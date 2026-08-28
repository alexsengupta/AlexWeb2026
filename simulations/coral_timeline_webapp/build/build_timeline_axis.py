#!/usr/bin/env python3
"""
Coral Reef Timeline — nonlinear corridor axis solver.

Turns 154 dated events spanning 3.48 Ga to 2026 CE into positions along a
first-person 3D corridor, such that:

  1. Order is strictly preserved (so a scrubber can map position -> time and back).
  2. No two cards are closer than a readable minimum separation.
  3. Deep time still *feels* deep, rather than collapsing to equal spacing.

The naive approach (position = log10(years before present), which is what the
`suggested_nonlinear_coordinate` column already contains) fails: 84% of
consecutive events land within 1% of the corridor of each other, and the log
singularity near the present wastes ~5% of the corridor on the final year.

Method
------
Position is a LAYOUT OUTPUT, not a formula on time.

  Stage 1  local time transform, per chapter
           geological chapters use log10(years BP); historical chapters use
           calendar year. This follows the project brief's own convention.

  Stage 2  initial warp, a blend controlled by ALPHA
             x0 = L * [ alpha * F_log + (1 - alpha) * F_rank ]
           alpha = 1 -> faithful to log time (crowded)
           alpha = 0 -> equal spacing by event ordinal (deep time feels flat)

  Stage 3  lane alternation, left / right of the track, so simultaneous events
           sit shoulder to shoulder instead of stacked in depth.

  Stage 4  isotonic minimum-separation solve. We need
               x[i+1] - x[i] >= d[i]
           with minimal least-squares displacement from x0. Substituting
           y[i] = x[i] - cumsum(d) turns this into "y must be non-decreasing",
           which is exactly isotonic regression, solved exactly by
           pool-adjacent-violators. Because the constraint is a LOWER bound,
           regions that were already generous in x0 are left untouched: the
           solver only opens up the crowded parts.

Outputs positions CSV, a webapp JSON, and a diagnostic figure.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Geometry constants. Units are "corridor units" (cu), roughly metres in the
# 3D scene. These are readability parameters, not scientific ones: change them
# when the card size or camera field of view changes.
# --------------------------------------------------------------------------
D_CROSS = 7.0    # minimum depth gap between cards on OPPOSITE sides of track
D_SAME = 12.0    # minimum depth gap between cards on the SAME side
GATE = 34.0      # extra gap inserted at a chapter boundary (the "gate")
NOW_CE = 2026.5  # present-day reference for years-before-present

# log10(years BP) diverges as an event approaches the present, which hands an
# absurd share of the corridor to the most recent months. Positioning therefore
# uses log10(years BP + LOG_OFFSET). The offset is a display decision only; the
# exact years_bp is preserved for the scale readout and all reporting.
LOG_OFFSET = 3.0

# Chapters in true chronological order (oldest first).
# `weight` is the editorial knob: >1 stretches a chapter, <1 compresses it.
# All 1.0 here means the layout is driven purely by data and readability.
CHAPTER_ORDER = [
    "Deep time: >100 Ma",
    "Deep time: 100–2.6 Ma",
    "Quaternary: 2.6 Ma–10 ka",
    "Holocene / pre-1500",
    "1500–1799",
    "1800–1949",
    "1950–1979",
    "1980–1997",
    "1998–2013",
    "2014–2026",
    # Beyond the present. Everything from here on is projected, not observed.
    "Projected: 2027–2100",
    "Scenario, no date given",
]

# Chapters that lie in the future. Their events are model projections, and the
# app is required to label them as such rather than letting them read as record.
FUTURE_CHAPTERS = {
    "Projected: 2027–2100",
    "Scenario, no date given",
}

# Chapters whose internal span is long enough that linear calendar time is
# meaningless. These use log10(years BP) internally; the rest use calendar year.
GEOLOGICAL_CHAPTERS = {
    "Deep time: >100 Ma",
    "Deep time: 100–2.6 Ma",
    "Quaternary: 2.6 Ma–10 ka",
    "Holocene / pre-1500",
}


@dataclass
class Event:
    event_id: str
    display_date: str
    chapter: str
    years_bp: float
    headline: str
    category: str
    region: str
    confidence: str
    priority: str
    log_bp: float = 0.0      # log10(years_bp + LOG_OFFSET), used for positioning
    local_t: float = 0.0     # normalised 0..1 within its chapter
    lane: int = 0            # -1 left, +1 right
    x0: float = 0.0          # pre-solve position
    x: float = 0.0           # post-solve position
    extras: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def signed_log_bp(ybp: float) -> float:
    """log10(years BP + LOG_OFFSET), continued smoothly into the future.

    Past events have ybp >= 0 and use the plain log. Projections have ybp < 0,
    where the log is undefined, so the curve is reflected through the point at
    the present. Value and gradient both match at ybp = 0, so the corridor does
    not acquire an artificial kink at the boundary between record and forecast.
    """
    if ybp >= 0:
        return math.log10(ybp + LOG_OFFSET)
    return 2 * math.log10(LOG_OFFSET) - math.log10(LOG_OFFSET - ybp)


def years_before_present(row: dict) -> float | None:
    """Resolve an event to years before present, preferring the most precise field."""
    age_ma = row.get("age_ma", "").strip()
    if age_ma:
        try:
            return float(age_ma) * 1e6
        except ValueError:
            pass
    for key in ("year_ce", "sort_year"):
        val = row.get(key, "").strip()
        if val:
            try:
                yr = float(val)
            except ValueError:
                continue
            if yr < -1e6:          # sort_year holds huge negatives for deep time
                return abs(yr)
            ybp = NOW_CE - yr
            # 0.4 floor keeps log10 finite for the most recent past event, but
            # must not apply to projections, whose ybp is legitimately negative
            return ybp if ybp < 0 else max(0.4, ybp)
    return None


def load_events(path: Path) -> list[Event]:
    events: list[Event] = []
    skipped = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            ybp = years_before_present(row)
            if ybp is None:
                skipped.append(row.get("event_id", "?"))
                continue
            events.append(
                Event(
                    event_id=row["event_id"].strip(),
                    display_date=row.get("display_date", "").strip(),
                    chapter=row.get("nonlinear_time_bin", "").strip(),
                    years_bp=ybp,
                    headline=row.get("headline", "").strip(),
                    # prefer the controlled vocabulary when present, but keep the
                    # original alongside it so nothing is lost
                    category=(row.get("category") or row.get("event_category", "")).strip(),
                    region=row.get("regional_track", "").strip(),
                    confidence=row.get("confidence", "").strip(),
                    priority=row.get("animation_priority", "").strip(),
                    log_bp=signed_log_bp(ybp),
                    extras={
                        "significance": row.get("significance", "").strip(),
                        "why": row.get("why_it_matters", "").strip(),
                        "location": row.get("location", "").strip(),
                        "end_range": row.get("end_range", "").strip(),
                        "reef_system": row.get("reef_system", "").strip(),
                        "category_group": row.get("category_group", "").strip(),
                        "category_source": row.get("event_category", "").strip(),
                        "knowledge_frame": row.get("knowledge_frame", "").strip(),
                        "evidence_type": row.get("evidence_type", "").strip(),
                        # both citations, with their types, rather than only the first
                        "source_title": row.get("source_1_title", "").strip(),
                        "source_url": row.get("source_1_url", "").strip(),
                        "source_type": row.get("source_1_type", "").strip(),
                        "source2_title": row.get("source_2_title", "").strip(),
                        "source2_url": row.get("source_2_url", "").strip(),
                        "source2_type": row.get("source_2_type", "").strip(),
                        # Projection fields. Publication year and projection year
                        # are kept apart on purpose: a 2016 paper about 2070 is
                        # not a 2070 event, and the card shows both.
                        "is_projection": row.get("is_projection", "").strip() == "yes",
                        "proj_year": row.get("proj_year", "").strip(),
                        "proj_pub_year": row.get("proj_pub_year", "").strip(),
                        "proj_scenario": row.get("proj_scenario", "").strip(),
                        "proj_quote": row.get("proj_quote", "").strip(),
                        "proj_quote_note": row.get("proj_quote_note", "").strip(),
                        "proj_undated": row.get("proj_undated", "").strip() == "yes",
                        # Plain-language mode. Same claims, simpler words; see
                        # basic/merge_basic.py for how it was made and checked.
                        "b_head": row.get("basic_headline", "").strip(),
                        "b_sig": row.get("basic_significance", "").strip(),
                        "b_why": row.get("basic_why", "").strip(),
                        "b_links": row.get("basic_links", "").strip(),
                    },
                )
            )
    if skipped:
        print(f"  WARNING: {len(skipped)} events could not be dated: {skipped}")
    # Oldest first. Stable tiebreak on event_id keeps the editorial order the
    # curator chose for same-year events.
    events.sort(key=lambda e: (-e.years_bp, e.event_id))
    return events


def check_chapter_consistency(events: list[Event]) -> list[str]:
    """Chapters should partition time. Flag any event that sits outside its
    chapter's chronological block, which would mean the bin labels disagree
    with the dates."""
    problems = []
    rank = {c: i for i, c in enumerate(CHAPTER_ORDER)}
    unknown = sorted({e.chapter for e in events if e.chapter not in rank})
    for u in unknown:
        problems.append(f"unknown chapter label: {u!r}")
    seq = [rank.get(e.chapter, -1) for e in events]
    for i in range(1, len(seq)):
        if seq[i] < seq[i - 1] and seq[i] >= 0 and seq[i - 1] >= 0:
            problems.append(
                f"{events[i].event_id} ({events[i].display_date}, {events[i].chapter}) "
                f"follows {events[i-1].event_id} ({events[i-1].chapter}) out of chapter order"
            )
    return problems


# --------------------------------------------------------------------------
# Stage 1-2: local transform and initial warp
# --------------------------------------------------------------------------
def assign_local_time(events: list[Event]) -> None:
    """Normalise each event to 0..1 within its chapter, using log10(years BP)
    for geological chapters and calendar year for historical ones."""
    by_chapter: dict[str, list[Event]] = {}
    for e in events:
        by_chapter.setdefault(e.chapter, []).append(e)

    for chapter, group in by_chapter.items():
        if chapter in GEOLOGICAL_CHAPTERS:
            vals = [-e.log_bp for e in group]        # negate so it increases with time
        else:
            vals = [-e.years_bp for e in group]      # linear calendar time
        lo, hi = min(vals), max(vals)
        span = hi - lo
        for e, v in zip(group, vals):
            e.local_t = 0.5 if span <= 0 else (v - lo) / span


def minimum_feasible_length(events: list[Event]) -> float:
    """The shortest corridor that can hold every card at the readability floor.
    Nothing below this is achievable, whatever the warp asks for."""
    return float(separation_chain(events).sum())


def initial_warp(events: list[Event], alpha: float, nominal_length: float) -> None:
    """Blend a global log-time position with a rank (equal-spacing) position.

    The chapter budget is set by `weight * (event count)`, so a chapter with
    more events gets proportionally more corridor. Within a chapter, events are
    distributed by their local time transform. alpha controls how much the true
    log-time distribution is respected versus flat rank ordering.

    `nominal_length` must comfortably exceed the minimum feasible length,
    otherwise the separation solver binds everywhere and the warp has no room
    to express itself (the layout collapses to equal spacing regardless of alpha).
    """
    counts = {c: sum(1 for e in events if e.chapter == c) for c in CHAPTER_ORDER}
    present = [c for c in CHAPTER_ORDER if counts.get(c, 0) > 0]

    # Provisional budget per chapter, in arbitrary units, normalised later.
    budgets = {c: counts[c] for c in present}
    total_budget = sum(budgets.values()) or 1.0

    # Cumulative chapter start offsets, 0..1
    starts, acc = {}, 0.0
    for c in present:
        starts[c] = acc / total_budget
        acc += budgets[c]

    # Global log-time position, 0..1, oldest = 0
    logs = np.array([e.log_bp for e in events])
    lo, hi = logs.min(), logs.max()
    f_log = (hi - logs) / (hi - lo)

    for i, e in enumerate(events):
        width = budgets[e.chapter] / total_budget
        f_rank = starts[e.chapter] + width * e.local_t
        e.x0 = (alpha * f_log[i] + (1.0 - alpha) * f_rank) * nominal_length


# --------------------------------------------------------------------------
# Stage 3: lane assignment
# --------------------------------------------------------------------------
def assign_lanes(events: list[Event]) -> None:
    """Strict left/right alternation.

    Strict alternation means every ADJACENT pair is cross-lane, so the binding
    constraint is D_CROSS. Same-lane neighbours are two apart, and are therefore
    separated by at least 2 * D_CROSS. Provided 2 * D_CROSS >= D_SAME, the
    same-lane readability constraint is satisfied automatically.
    """
    assert 2 * D_CROSS >= D_SAME, (
        f"lane geometry unsafe: 2*D_CROSS ({2*D_CROSS}) < D_SAME ({D_SAME}); "
        "same-lane cards could overlap"
    )
    for i, e in enumerate(events):
        e.lane = -1 if i % 2 == 0 else 1


def separation_chain(events: list[Event]) -> np.ndarray:
    """Required gap d[i] between event i and i+1."""
    d = np.empty(len(events) - 1)
    for i in range(len(events) - 1):
        base = D_CROSS if events[i].lane != events[i + 1].lane else D_SAME
        if events[i].chapter != events[i + 1].chapter:
            base += GATE
        d[i] = base
    return d


# --------------------------------------------------------------------------
# Stage 4: isotonic minimum-separation solve
# --------------------------------------------------------------------------
def pava(z: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators: nearest non-decreasing sequence in L2.

    Returns argmin_y ||y - z||^2 subject to y[0] <= y[1] <= ... <= y[n-1].
    """
    vals: list[float] = []
    wts: list[float] = []
    for value in z:
        vals.append(float(value))
        wts.append(1.0)
        # Merge backwards while the last block violates monotonicity
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2 = vals.pop(), wts.pop()
            v1, w1 = vals.pop(), wts.pop()
            w = w1 + w2
            vals.append((v1 * w1 + v2 * w2) / w)
            wts.append(w)
    out = np.empty(len(z))
    idx = 0
    for v, w in zip(vals, wts):
        out[idx: idx + int(w)] = v
        idx += int(w)
    return out


def solve_positions(events: list[Event]) -> None:
    """Enforce x[i+1] - x[i] >= d[i] with minimal least-squares displacement."""
    x0 = np.array([e.x0 for e in events])
    d = separation_chain(events)
    cum = np.concatenate([[0.0], np.cumsum(d)])   # offsets c[i]
    y = pava(x0 - cum)
    x = y + cum
    x -= x.min()                                   # corridor starts at 0
    for e, xi in zip(events, x):
        e.x = float(xi)


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------
def scale_profile(events: list[Event]) -> np.ndarray:
    """Years of real time represented per corridor unit, between each pair."""
    out = np.empty(len(events) - 1)
    for i in range(len(events) - 1):
        dt = events[i].years_bp - events[i + 1].years_bp
        dx = events[i + 1].x - events[i].x
        out[i] = dt / dx if dx > 0 else np.nan
    return out


def summarise(events: list[Event], alpha: float) -> dict:
    x = np.array([e.x for e in events])
    x0 = np.array([e.x0 for e in events])
    L = float(x.max())
    gaps = np.diff(x)
    d = separation_chain(events)
    scales = scale_profile(events)
    finite = scales[np.isfinite(scales) & (scales > 0)]

    shares = {}
    for c in CHAPTER_ORDER:
        xs = [e.x for e in events if e.chapter == c]
        if xs:
            shares[c] = (max(xs) - min(xs)) / L * 100 if L else 0.0

    # How far the solver had to override the requested warp
    x0n = (x0 - x0.min()) / (x0.max() - x0.min()) if x0.max() > x0.min() else x0 * 0
    xn = x / L if L else x
    displacement = float(np.abs(xn - x0n).mean() * 100)

    deep = sum(v for k, v in shares.items() if k.startswith("Deep time"))
    # "Pinned" pairs are those sitting exactly on the readability floor, i.e.
    # where the requested time warp was overruled by the need to stay legible.
    pinned = float((gaps <= d + 1e-6).mean() * 100)
    return {
        "alpha": alpha,
        "pinned_pct": pinned,
        "corridor_units": L,
        "min_gap": float(gaps.min()),
        "median_gap": float(np.median(gaps)),
        "max_gap": float(gaps.max()),
        "constraints_ok": bool((gaps >= d - 1e-6).all()),
        "scale_min_yr_per_cu": float(finite.min()),
        "scale_max_yr_per_cu": float(finite.max()),
        "scale_dynamic_range": float(finite.max() / finite.min()),
        "deep_time_share_pct": deep,
        "mean_displacement_pct": displacement,
        "chapter_shares": shares,
    }


def make_figure(events: list[Event], stats: dict, sweep: list[dict], out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    x = np.array([e.x for e in events])
    L = x.max()
    palette = plt.get_cmap("turbo")(np.linspace(0.06, 0.94, len(CHAPTER_ORDER)))
    colour = {c: palette[i] for i, c in enumerate(CHAPTER_ORDER)}

    fig = plt.figure(figsize=(16, 13))
    gs = fig.add_gridspec(4, 2, height_ratios=[1.5, 1.2, 1.0, 1.0], hspace=0.42, wspace=0.22)

    # -- Panel 1: corridor map -------------------------------------------
    ax = fig.add_subplot(gs[0, :])
    for e in events:
        ax.plot([e.x, e.x], [0, e.lane], color=colour.get(e.chapter, "grey"),
                lw=0.7, alpha=0.55, zorder=1)
        ax.scatter(e.x, e.lane, s=26, color=colour.get(e.chapter, "grey"),
                   edgecolor="white", linewidth=0.4, zorder=3)
    ax.axhline(0, color="0.25", lw=1.2, zorder=2)
    seen = set()
    for i in range(1, len(events)):
        if events[i].chapter != events[i - 1].chapter:
            xb = (events[i].x + events[i - 1].x) / 2
            ax.axvline(xb, color="0.4", ls=":", lw=1.0, zorder=0)
            if events[i].chapter not in seen:
                ax.text(xb, 1.62, events[i].chapter, rotation=32, fontsize=7.5,
                        ha="left", va="bottom", color="0.25")
                seen.add(events[i].chapter)
    ax.text(0, 1.62, CHAPTER_ORDER[0], rotation=32, fontsize=7.5,
            ha="left", va="bottom", color="0.25")
    ax.set_ylim(-2.6, 3.4)
    ax.set_xlim(-L * 0.01, L * 1.01)
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(["left lane", "track", "right lane"], fontsize=8)
    ax.set_xlabel("position along corridor (corridor units ≈ metres)")
    ax.set_title(f"Corridor layout — {len(events)} events, "
                 f"{L:,.0f} cu total, minimum gap {stats['min_gap']:.1f} cu "
                 f"(floor {D_CROSS:.0f} cu)", fontsize=11, weight="bold")

    # -- Panel 2: honesty curve ------------------------------------------
    ax2 = fig.add_subplot(gs[1, :])
    mid = (x[:-1] + x[1:]) / 2
    sc = scale_profile(events)
    ax2.step(mid, sc, where="mid", color="0.2", lw=1.2)
    for i in range(1, len(events)):
        if events[i].chapter != events[i - 1].chapter:
            ax2.axvline((events[i].x + events[i - 1].x) / 2, color="0.4", ls=":", lw=1.0)
    ax2.set_yscale("log")
    ax2.set_xlim(-L * 0.01, L * 1.01)
    ax2.set_ylabel("years of real time\nper corridor unit", fontsize=9)
    ax2.set_xlabel("position along corridor")
    ax2.set_title(f"Scale distortion — the corridor compresses time by a factor of "
                  f"{stats['scale_dynamic_range']:,.0f} between its slowest and fastest stretch. "
                  f"This is what the on-screen ruler must disclose.", fontsize=10)
    ax2.grid(alpha=0.25, which="both")

    # -- Panel 3: gap distribution ---------------------------------------
    ax3 = fig.add_subplot(gs[2, 0])
    gaps = np.diff(x)
    ax3.hist(gaps, bins=45, color="#2a7fb8", edgecolor="white", linewidth=0.4)
    ax3.axvline(D_CROSS, color="crimson", ls="--", lw=1.4,
                label=f"readability floor ({D_CROSS:.0f} cu)")
    ax3.set_xlabel("gap between consecutive cards (cu)")
    ax3.set_ylabel("count")
    ax3.set_title("Card spacing after solve", fontsize=10)
    ax3.legend(fontsize=8)

    # -- Panel 4: chapter shares -----------------------------------------
    ax4 = fig.add_subplot(gs[2, 1])
    chs = [c for c in CHAPTER_ORDER if c in stats["chapter_shares"]]
    counts = [sum(1 for e in events if e.chapter == c) for c in chs]
    vals = [stats["chapter_shares"][c] for c in chs]
    ypos = np.arange(len(chs))
    ax4.barh(ypos, vals, color=[colour[c] for c in chs], edgecolor="white")
    for i, (v, n) in enumerate(zip(vals, counts)):
        ax4.text(v + 0.4, i, f"{v:.1f}%  ({n} ev)", va="center", fontsize=7.5)
    ax4.set_yticks(ypos)
    ax4.set_yticklabels(chs, fontsize=7.5)
    ax4.invert_yaxis()
    ax4.set_xlabel("share of corridor length (%)")
    ax4.set_xlim(0, max(vals) * 1.32)
    ax4.set_title("Corridor budget by chapter", fontsize=10)

    # -- Panel 5: alpha sweep --------------------------------------------
    ax5 = fig.add_subplot(gs[3, 0])
    a = [s["alpha"] for s in sweep]
    pinned = [s["pinned_pct"] for s in sweep]
    ax5.plot(a, pinned, "o-", color="#2a7fb8")
    best = int(np.argmin(pinned))
    ax5.scatter([a[best]], [pinned[best]], s=150, facecolor="none",
                edgecolor="crimson", lw=2, zorder=5)
    ax5.annotate(f"best: alpha={a[best]:.2f}\n{pinned[best]:.0f}% pinned",
                 (a[best], pinned[best]), textcoords="offset points",
                 xytext=(10, 22), fontsize=8, color="crimson")
    ax5.set_xlabel("alpha (0 = equal spacing, 1 = faithful log time)")
    ax5.set_ylabel("% of gaps pinned to\nthe readability floor")
    ax5.grid(alpha=0.25)
    ax5.set_title("Where the warp survives the floor", fontsize=10)

    ax6 = fig.add_subplot(gs[3, 1])
    ax6.plot(a, [s["deep_time_share_pct"] for s in sweep], "o-",
             color="#c0392b", label="deep time (>2.6 Ma) share")
    ax6.plot(a, [s["chapter_shares"].get("2014–2026", 0) for s in sweep], "s-",
             color="#27ae60", label="2014–2026 share")
    ax6.set_xlabel("alpha")
    ax6.set_ylabel("share of corridor (%)")
    ax6.legend(fontsize=8)
    ax6.grid(alpha=0.25)
    ax6.set_title("What alpha trades away", fontsize=10)

    fig.suptitle("Coral Reef Timeline — nonlinear corridor axis diagnostics",
                 fontsize=14, weight="bold", y=0.965)
    fig.savefig(out_png, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def verify(events: list[Event]) -> list[str]:
    failures = []
    x = np.array([e.x for e in events])
    d = separation_chain(events)
    gaps = np.diff(x)

    if not np.all(np.diff(x) > 0):
        failures.append("positions are not strictly increasing (scrubber would not be invertible)")
    bad = np.where(gaps < d - 1e-6)[0]
    if len(bad):
        failures.append(f"{len(bad)} pairs violate their minimum separation")

    # Same-lane pairs (two apart under strict alternation)
    for i in range(len(events) - 2):
        if events[i].lane == events[i + 2].lane:
            if x[i + 2] - x[i] < D_SAME - 1e-6:
                failures.append(
                    f"same-lane pair {events[i].event_id}/{events[i+2].event_id} "
                    f"only {x[i+2]-x[i]:.2f} cu apart (need {D_SAME})"
                )
    # Order must still match true chronology
    ybp = [e.years_bp for e in events]
    if any(ybp[i] < ybp[i + 1] for i in range(len(ybp) - 1)):
        failures.append("event order does not match true chronology")
    return failures


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def run(events: list[Event], alpha: float, length_factor: float) -> dict:
    assign_local_time(events)
    assign_lanes(events)                     # lanes first: they set the floor
    nominal = minimum_feasible_length(events) * length_factor
    initial_warp(events, alpha, nominal)
    solve_positions(events)
    s = summarise(events, alpha)
    s["length_factor"] = length_factor
    s["nominal_length"] = nominal
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="coral_reef_events_master_clean.csv")
    ap.add_argument("--alpha", type=float, default=0.40,
                    help="time fidelity: 0 = equal spacing, 1 = faithful log time")
    ap.add_argument("--length-factor", type=float, default=3.0,
                    help="corridor length as a multiple of the minimum feasible length")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    out = Path(args.outdir)
    (out / "data" / "derived").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    print("Loading events ...")
    events = load_events(Path(args.events))
    print(f"  {len(events)} events, {events[0].display_date} to {events[-1].display_date}")

    problems = check_chapter_consistency(events)
    if problems:
        print("  Chapter consistency issues:")
        for p in problems:
            print(f"    - {p}")
    else:
        print("  Chapter labels are consistent with dates.")

    assign_lanes(events)
    floor = minimum_feasible_length(events)
    print(f"\n  Minimum feasible corridor: {floor:,.0f} cu "
          f"(every card at the {D_CROSS:.0f} cu readability floor). "
          f"Requesting {args.length_factor:g}x that.")

    print("\nAlpha sweep (how much true log time to respect):")
    print(f"  {'alpha':>6} {'length(cu)':>11} {'min gap':>8} {'pinned%':>8} {'deep %':>7} "
          f"{'2014-26 %':>10} {'scale range':>13} {'ok':>4}")
    sweep = []
    for a in [0.0, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0]:
        s = run(events, a, args.length_factor)
        sweep.append(s)
        print(f"  {a:>6.2f} {s['corridor_units']:>11,.0f} {s['min_gap']:>8.1f} "
              f"{s['pinned_pct']:>8.1f} "
              f"{s['deep_time_share_pct']:>7.1f} "
              f"{s['chapter_shares'].get('2014–2026', 0):>10.1f} "
              f"{s['scale_dynamic_range']:>13,.0f} "
              f"{'yes' if s['constraints_ok'] else 'NO':>4}")

    print(f"\nFinal solve at alpha = {args.alpha}, length factor = {args.length_factor:g}")
    stats = run(events, args.alpha, args.length_factor)

    failures = verify(events)
    if failures:
        print("  VERIFICATION FAILED:")
        for f in failures:
            print(f"    - {f}")
    else:
        print("  Verification passed: strictly ordered, all separations satisfied.")

    L = stats["corridor_units"]
    print(f"  corridor length      {L:,.0f} cu")
    print(f"  gaps                 min {stats['min_gap']:.1f} / "
          f"median {stats['median_gap']:.1f} / max {stats['max_gap']:.1f} cu")
    print(f"  scale                {stats['scale_min_yr_per_cu']:,.2f} to "
          f"{stats['scale_max_yr_per_cu']:,.0f} years per cu "
          f"(range {stats['scale_dynamic_range']:,.0f}x)")
    print(f"  at 30 cu/s travel    {L/30:,.0f} s end to end")

    # -- write positions CSV ---------------------------------------------
    pos_csv = out / "data" / "derived" / "timeline_axis_positions.csv"
    with pos_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["event_id", "display_date", "years_bp", "chapter", "lane",
                    "x_cu", "x_norm", "years_per_cu_ahead", "category", "region",
                    "confidence", "animation_priority", "headline"])
        sc = scale_profile(events)
        for i, e in enumerate(events):
            w.writerow([
                e.event_id, e.display_date, f"{e.years_bp:.4f}", e.chapter, e.lane,
                f"{e.x:.3f}", f"{e.x / L:.6f}",
                f"{sc[i]:.6f}" if i < len(sc) and np.isfinite(sc[i]) else "",
                e.category, e.region, e.confidence, e.priority, e.headline,
            ])

    # -- write webapp JSON -----------------------------------------------
    payload = {
        "meta": {
            "generated_from": Path(args.events).name,
            "event_count": len(events),
            "alpha": args.alpha,
            "corridor_units": round(L, 2),
            "geometry": {"d_cross": D_CROSS, "d_same": D_SAME, "gate": GATE},
            "scale_dynamic_range": round(stats["scale_dynamic_range"], 1),
            "chapters": [c for c in CHAPTER_ORDER
                         if any(e.chapter == c for e in events)],
            "caveat": ("Distance along the corridor does not represent duration. "
                       "The on-screen ruler must display the local scale."),
        },
        "events": [
            {
                "id": e.event_id, "date": e.display_date, "yearsBP": round(e.years_bp, 3),
                "chapter": e.chapter, "lane": e.lane,
                "x": round(e.x, 3), "t": round(e.x / L, 6),
                "headline": e.headline, "category": e.category, "region": e.region,
                "confidence": e.confidence, "priority": e.priority,
                **e.extras,
            }
            for e in events
        ],
    }
    json_path = out / "data" / "derived" / "timeline_axis.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    fig_path = out / "figures" / "timeline_axis_diagnostics.png"
    make_figure(events, stats, sweep, fig_path)

    print(f"\nWrote {pos_csv}")
    print(f"Wrote {json_path}")
    print(f"Wrote {fig_path}")


if __name__ == "__main__":
    main()
