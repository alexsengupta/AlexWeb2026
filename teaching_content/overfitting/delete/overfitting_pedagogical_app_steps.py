"""overfitting_pedagogical_app_steps.py

A pedagogical Bokeh server app inspired by fig3_overfitting.py.

This version is intentionally *guided* and *stepwise* without using tabs:

  Step 1: Generate an "observed" time series y(t)
  Step 2: Generate predictors X(t) and inspect simple predictor–y correlations
  Step 3: Fit an OLS multiple linear regression and compare TRAIN vs TEST skill

Designed for honours+ students with a focus on three overarching concepts:
  1) Overfitting: training fit ≠ predictive skill
  2) Time-series validation: blocked vs random splits (leakage under persistence)
  3) Spurious skill: trends/autocorrelation can create misleading relationships

Run
---
  bokeh serve --show overfitting_pedagogical_app_steps.py

Dependencies
------------
  numpy, bokeh

Notes
-----
- Uses numpy.linalg.lstsq for OLS (works even when p >= n_train).
- "Scenarios" only populate Step 1–2 (y and X). If you change any y/X
  generation setting, the app switches to "Custom".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import (
    BoxAnnotation,
    Button,
    ColumnDataSource,
    Div,
    HoverTool,
    Select,
    Slider,
    Span,
    Toggle,
)
from bokeh.plotting import figure


# -----------------------------
# Styling helpers
# -----------------------------

GREY = "#333333"
MID_GREY = "#666666"
LIGHT_GREY = "#999999"
BLUE = "#1a73e8"
RED = "#d93025"

INFO_ICON_STYLE = "font-size:16px; color:#666; cursor:help; user-select:none;"


# -----------------------------
# Parameters and scenarios
# -----------------------------


@dataclass(frozen=True)
class YXParams:
    """Only the parameters that define the synthetic data (Steps 1–2)."""

    start_year: int
    n_years: int
    phi_y: float
    sigma_y: float
    trend_y: float

    n_predictors: int
    phi_x: float
    sigma_x: float
    trend_x: float


SCENARIOS: Dict[str, Tuple[str, YXParams]] = {
    "Null overfitting": (
        "Fills in Step 1–2 with a persistent y(t), many predictors, and *no true relationship* (null world). "
        "Try increasing p or reducing training years in Step 3 to see overfitting.",
        YXParams(
            start_year=1985,
            n_years=40,
            phi_y=0.50,
            sigma_y=0.8,
            trend_y=0.0,
            n_predictors=12,
            phi_x=0.00,
            sigma_x=1.0,
            trend_x=0.0,
        ),
    ),
    "Leakage": (
        "Fills in Step 1–2 with *high autocorrelation* in y(t). "
        "In Step 3, compare Blocked vs Random splits: Random splits can look too good because nearby years leak information.",
        YXParams(
            start_year=1985,
            n_years=40,
            phi_y=0.85,
            sigma_y=0.8,
            trend_y=0.0,
            n_predictors=12,
            phi_x=0.00,
            sigma_x=1.0,
            trend_x=0.0,
        ),
    ),
    "Shared trend trap": (
        "Fills in Step 1–2 with a shared trend in y and X. "
        "In Step 3, you may see apparently strong relationships driven by the common trend. "
        "Toggle 'Detrend' to see how much of the relationship was just trend.",
        YXParams(
            start_year=1985,
            n_years=50,
            phi_y=0.50,
            sigma_y=0.8,
            trend_y=0.08,
            n_predictors=12,
            phi_x=0.10,
            sigma_x=1.0,
            trend_x=0.08,
        ),
    ),
}


# -----------------------------
# Core maths
# -----------------------------


def _clip(phi: float) -> float:
    return float(np.clip(phi, -0.999, 0.999))


def ar1(phi: float, n: int, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Stationary AR(1) with approx marginal std ~ sigma."""
    phi = _clip(phi)
    innov_sd = sigma * np.sqrt(max(1e-12, 1.0 - phi**2))

    e = rng.normal(0.0, innov_sd, n)
    x = np.empty(n, dtype=float)
    x[0] = rng.normal(0.0, sigma)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((a - b) ** 2)))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 3:
        return float("nan")
    if np.allclose(np.std(a), 0.0) or np.allclose(np.std(b), 0.0):
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def r2(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 2:
        return float("nan")
    sse = float(np.sum((a - b) ** 2))
    sst = float(np.sum((a - float(np.mean(a))) ** 2))
    if sst <= 0:
        return float("nan")
    return 1.0 - sse / sst


def fit_trend(t: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Fit y ~ a + b t. Returns (a, b)."""
    if len(t) < 2:
        return float(np.mean(y)) if len(y) else 0.0, 0.0
    b, a = np.polyfit(t, y, 1)
    return float(a), float(b)


def detrend_by_training(t: np.ndarray, y: np.ndarray, train_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Remove a linear trend fit on training portion only.

    Returns (y_anom, trend_fit_all).
    """
    a, b = fit_trend(t[train_mask], y[train_mask])
    trend_fit = a + b * t
    return y - trend_fit, trend_fit


def split_mask_blocked(n: int, n_train: int) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    mask[:n_train] = True
    return mask


def split_mask_random(n: int, n_train: int, rng: np.random.Generator) -> np.ndarray:
    idx = np.arange(n)
    tr = rng.choice(idx, size=n_train, replace=False)
    mask = np.zeros(n, dtype=bool)
    mask[tr] = True
    return mask


def predictor_names(p: int) -> List[str]:
    return [f"X{j+1}" for j in range(int(p))]


def ols_fit_predict(X: np.ndarray, y: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
    """Fit y ~ b0 + X b using least squares. Returns (b0, b, yhat_all)."""
    n = X.shape[0]
    A = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    b0 = float(beta[0])
    b = beta[1:].astype(float)
    yhat = A @ beta
    return b0, b, yhat


# -----------------------------
# Simulation + model wrapper
# -----------------------------


@dataclass
class Params:
    """Full parameter set (including Step 3 modelling choices)."""

    # Step 1–2
    yx: YXParams

    # Step 3
    n_train: int
    split_method: str  # "Blocked" or "Random"
    detrend: bool


def simulate(seed: int, yx: YXParams) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(int(seed))

    years = np.arange(yx.start_year, yx.start_year + yx.n_years)
    t = np.arange(yx.n_years, dtype=float)

    y = ar1(yx.phi_y, yx.n_years, yx.sigma_y, rng)
    y = y + yx.trend_y * (t - t[0])

    X = np.empty((yx.n_years, yx.n_predictors), dtype=float)
    for j in range(yx.n_predictors):
        X[:, j] = ar1(yx.phi_x, yx.n_years, yx.sigma_x, rng)
    if abs(yx.trend_x) > 0:
        X = X + yx.trend_x * (t - t[0])[:, None]

    return {"years": years, "t": t, "y": y, "X": X}


def fit_and_score(seed: int, params: Params) -> Dict[str, object]:
    """Fit OLS MLR and compute metrics for train and test."""

    data = simulate(seed, params.yx)
    years = data["years"]
    t = data["t"]
    y = data["y"]
    X = data["X"]

    # Split RNG should be independent of data RNG
    rng_split = np.random.default_rng(int(seed) + 10_000_019)

    n_years = int(params.yx.n_years)
    n_train = int(params.n_train)
    n_train = int(np.clip(n_train, 5, max(5, n_years - 5)))  # keep at least 5 test yrs

    if params.split_method == "Random":
        train_mask = split_mask_random(n_years, n_train, rng_split)
    else:
        train_mask = split_mask_blocked(n_years, n_train)
    test_mask = ~train_mask

    # Optional detrending (fit on training only)
    if params.detrend:
        y_anom, y_trend_fit = detrend_by_training(t, y, train_mask)
        X_anom = np.empty_like(X)
        for j in range(X.shape[1]):
            X_anom[:, j], _ = detrend_by_training(t, X[:, j], train_mask)
    else:
        y_anom = y.copy()
        y_trend_fit = np.zeros_like(y)
        X_anom = X

    # Fit OLS on anomalies (or raw)
    X_train = X_anom[train_mask]
    y_train = y_anom[train_mask]

    b0, b, yhat_anom_all = ols_fit_predict(X_train, y_train)  # fit on train only

    # Predict for all years using same coefficients
    A_all = np.column_stack([np.ones(n_years), X_anom])
    beta = np.concatenate([[b0], b])
    yhat_anom = A_all @ beta

    # Re-add trend if we detrended
    yhat = y_trend_fit + yhat_anom

    y_train_orig = y[train_mask]
    y_test_orig = y[test_mask]
    yhat_train = yhat[train_mask]
    yhat_test = yhat[test_mask]

    r_train = corr(y_train_orig, yhat_train)
    r_test = corr(y_test_orig, yhat_test)
    r2_train = r2(y_train_orig, yhat_train)
    r2_test = r2(y_test_orig, yhat_test)
    rmse_train = rmse(y_train_orig, yhat_train)
    rmse_test = rmse(y_test_orig, yhat_test)

    # Baselines (test)
    mean_baseline = np.full_like(y_test_orig, float(np.mean(y_train_orig)))
    rmse_test_mean = rmse(y_test_orig, mean_baseline)

    a_tr, b_tr = fit_trend(t[train_mask], y_train_orig)
    y_trend_only_all = a_tr + b_tr * t
    rmse_test_trend = rmse(y_test_orig, y_trend_only_all[test_mask])

    # Complexity/dependence heuristics
    p = int(params.yx.n_predictors)
    ratio = p / max(1, n_train)
    phi_y = float(params.yx.phi_y)
    n_eff = n_train * (1.0 - phi_y) / (1.0 + phi_y) if abs(1.0 + phi_y) > 1e-12 else 1.0
    n_eff = float(np.clip(n_eff, 1.0, float(n_train)))

    return {
        "years": years,
        "t": t,
        "y": y,
        "X": X,
        "yhat": yhat,
        "train_mask": train_mask,
        "test_mask": test_mask,
        "y_train": y_train_orig,
        "y_test": y_test_orig,
        "yhat_train": yhat_train,
        "yhat_test": yhat_test,
        "r_train": r_train,
        "r_test": r_test,
        "r2_train": r2_train,
        "r2_test": r2_test,
        "rmse_train": rmse_train,
        "rmse_test": rmse_test,
        "rmse_test_mean": rmse_test_mean,
        "rmse_test_trend": rmse_test_trend,
        "coef_intercept": b0,
        "coef": b,
        "p": p,
        "n_train": n_train,
        "ratio": ratio,
        "phi_y": phi_y,
        "n_eff": n_eff,
        "detrend": params.detrend,
    }


# -----------------------------
# Widgets
# -----------------------------


# Top bar controls
seed_base = Slider(title="Base seed (changes the random realisation)", start=0, end=9999, step=1, value=96)
btn_resample = Button(label="Resample (new realisation)", button_type="primary")
btn_reset_history = Button(label="Reset history", button_type="default")

# Scenario buttons
btn_scn_null = Button(label="Null overfitting", button_type="success")
btn_scn_leak = Button(label="Leakage", button_type="default")
btn_scn_trend = Button(label="Shared trend trap", button_type="default")

# Step 1: y
start_year = Slider(title="Start year", start=1900, end=2025, step=1, value=1985)
n_years = Slider(title="Total duration (years)", start=20, end=120, step=1, value=40)
phi_y = Slider(title="y autocorrelation (AR1 ϕᵧ)", start=-0.2, end=0.95, step=0.05, value=0.50)
sigma_y = Slider(title="y noise level (σᵧ)", start=0.2, end=2.0, step=0.1, value=0.8)
trend_y = Slider(title="y trend (units/year)", start=-0.2, end=0.2, step=0.01, value=0.0)

# Step 2: X
n_predictors = Slider(title="# predictors (p)", start=1, end=60, step=1, value=12)
phi_x = Slider(title="Predictor autocorrelation (AR1 ϕₓ)", start=-0.2, end=0.95, step=0.05, value=0.00)
sigma_x = Slider(title="Predictor noise level (σₓ)", start=0.2, end=2.0, step=0.1, value=1.0)
trend_x = Slider(title="Predictor shared trend (units/year)", start=-0.2, end=0.2, step=0.01, value=0.0)
highlight_pred = Slider(title="Highlight predictor #", start=1, end=12, step=1, value=1)

# Step 3: modelling
n_train = Slider(title="Training years", start=5, end=95, step=1, value=25)
split_method = Select(title="Validation split", value="Blocked", options=["Blocked", "Random"])
detrend_toggle = Toggle(label="Detrend y and X before fitting (fit anomalies, then add trend back)", active=False)
show_history_toggle = Toggle(label="Show resampling history", active=False)


# -----------------------------
# Data sources
# -----------------------------


src_y = ColumnDataSource(data=dict(year=[], y=[]))

# Predictor time series (multi_line)
src_X = ColumnDataSource(data=dict(xs=[], ys=[], name=[], alpha=[], width=[], color=[]))

# Step 2 scatter: y vs highlighted predictor
src_sc_yx = ColumnDataSource(data=dict(x=[], y=[]))

# Step 3 time series (observed + predictions)
src_obs_train = ColumnDataSource(data=dict(year=[], y=[]))
src_obs_test = ColumnDataSource(data=dict(year=[], y=[]))
src_pred_train = ColumnDataSource(data=dict(year=[], yhat=[]))
src_pred_test = ColumnDataSource(data=dict(year=[], yhat=[]))

# Step 3 scatters
src_sc_train = ColumnDataSource(data=dict(obs=[], pred=[]))
src_sc_test = ColumnDataSource(data=dict(obs=[], pred=[]))
src_line_train = ColumnDataSource(data=dict(x=[], y=[]))
src_line_test = ColumnDataSource(data=dict(x=[], y=[]))

# History cloud (optional)
src_hist = ColumnDataSource(data=dict(r_train=[], r_test=[]))


# -----------------------------
# Figures
# -----------------------------


# Step 1
fig_y = figure(
    height=300,
    sizing_mode="stretch_width",
    title="Step 1 — Generate an observed time series y(t)",
    x_axis_label="Year",
    y_axis_label="y",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
fig_y.line("year", "y", source=src_y, line_color=GREY, line_width=2)
fig_y.scatter("year", "y", source=src_y, marker="circle", size=6, color=GREY, alpha=0.8)


# Step 2: predictors time series
fig_X = figure(
    height=300,
    sizing_mode="stretch_width",
    title="Step 2 — Generate predictors X(t) (one highlighted)",
    x_axis_label="Year",
    y_axis_label="X",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)

r_multiline = fig_X.multi_line(
    xs="xs",
    ys="ys",
    source=src_X,
    line_color="color",
    line_alpha="alpha",
    line_width="width",
)
fig_X.add_tools(HoverTool(renderers=[r_multiline], tooltips=[("Predictor", "@name")], line_policy="nearest"))


# Step 2: scatter of y vs highlighted predictor
fig_yx = figure(
    height=260,
    width=360,
    title="Step 2 — Scatter: y vs highlighted predictor",
    x_axis_label="Highlighted predictor",
    y_axis_label="Observed y",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
fig_yx.scatter("x", "y", source=src_sc_yx, marker="circle", size=7, alpha=0.65, color=MID_GREY)
fig_yx.add_tools(
    HoverTool(
        tooltips=[
            ("x", "@x{0.00}"),
            ("y", "@y{0.00}"),
            ("What is this?", "Raw correlation view (not a model yet)"),
        ]
    )
)


# Step 3: time-series view (train/test)
fig_ts = figure(
    height=280,
    sizing_mode="stretch_width",
    title="Step 3 — Fit on training years, evaluate on test years",
    x_axis_label="Year",
    y_axis_label="y",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)

train_box = BoxAnnotation(fill_color="#E8F0FE", fill_alpha=0.8)
test_box = BoxAnnotation(fill_color="#FDE8E8", fill_alpha=0.8)
fig_ts.add_layout(train_box)
fig_ts.add_layout(test_box)

split_span = Span(location=0, dimension="height", line_color=MID_GREY, line_dash="dashed", line_width=1.5)
fig_ts.add_layout(split_span)

# Observed y
fig_ts.line("year", "y", source=src_y, line_color=GREY, line_width=2)
fig_ts.scatter("year", "y", source=src_obs_train, marker="circle", size=6, color=BLUE, alpha=0.9, legend_label="Observed (train)")
fig_ts.scatter("year", "y", source=src_obs_test, marker="circle", size=6, color=RED, alpha=0.9, legend_label="Observed (test)")

# Predicted yhat
pred_train_line = fig_ts.line("year", "yhat", source=src_pred_train, line_color=BLUE, line_width=2, alpha=0.85, legend_label="Model (train)")
pred_test_line = fig_ts.line("year", "yhat", source=src_pred_test, line_color=RED, line_width=2, alpha=0.85, legend_label="Model (test)")

fig_ts.scatter("year", "yhat", source=src_pred_train, marker="square", size=7, color=BLUE, alpha=0.85, line_color="white")
fig_ts.scatter("year", "yhat", source=src_pred_test, marker="square", size=7, color=RED, alpha=0.85, line_color="white")

fig_ts.legend.location = "top_left"
fig_ts.legend.click_policy = "hide"


# Step 3: scatters
sc_tr = figure(
    height=260,
    width=340,
    title="Training scatter",
    x_axis_label="Observed y",
    y_axis_label="Predicted ŷ",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
sc_tr.scatter("obs", "pred", source=src_sc_train, marker="circle", size=7, alpha=0.7, color=BLUE)
sc_tr.line("x", "y", source=src_line_train, line_dash="dashed", line_color=LIGHT_GREY)
sc_tr.match_aspect = True
sc_tr.add_tools(
    HoverTool(
        tooltips=[
            ("Observed", "@obs{0.00}"),
            ("Predicted", "@pred{0.00}"),
            ("What is this?", "Training years only (in-sample)"),
        ]
    )
)

sc_te = figure(
    height=260,
    width=340,
    title="Test scatter",
    x_axis_label="Observed y",
    y_axis_label="Predicted ŷ",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
sc_te.scatter("obs", "pred", source=src_sc_test, marker="circle", size=7, alpha=0.7, color=RED)
sc_te.line("x", "y", source=src_line_test, line_dash="dashed", line_color=LIGHT_GREY)
sc_te.match_aspect = True
sc_te.add_tools(
    HoverTool(
        tooltips=[
            ("Observed", "@obs{0.00}"),
            ("Predicted", "@pred{0.00}"),
            ("What is this?", "Test years (out-of-sample)"),
        ]
    )
)


# Optional history plot
hist = figure(
    height=240,
    sizing_mode="stretch_width",
    title="Resampling history (correlation skill): each click adds one point",
    x_axis_label="Training correlation r",
    y_axis_label="Test correlation r",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
hist.scatter("r_train", "r_test", source=src_hist, marker="circle", size=7, alpha=0.6)
hist.line([-1, 1], [-1, 1], line_dash="dotted", line_color=LIGHT_GREY)


# -----------------------------
# Text blocks
# -----------------------------


scenario_status = Div(text="", sizing_mode="stretch_width")

step1_text = Div(
    text=(
        "<div style='font-size:13px; line-height:1.35'>"
        "<b>What you control here:</b> persistence (ϕᵧ), noise level (σᵧ), and an optional trend. "
        "<br/>Try large ϕᵧ to create a strongly autocorrelated series."  # concise
        "</div>"
    ),
    sizing_mode="stretch_width",
)

step2_text = Div(
    text=(
        "<div style='font-size:13px; line-height:1.35'>"
        "<b>What you control here:</b> how many predictors you have (p) and how 'time-series-like' they are (ϕₓ, trend). "
        "<br/>With larger p, it becomes easier to find a predictor that correlates with y by chance."  # concise
        "</div>"
    ),
    sizing_mode="stretch_width",
)

pred_corr_div = Div(text="", sizing_mode="stretch_width")

step3_text = Div(
    text=(
        "<div style='font-size:13px; line-height:1.35'>"
        "<b>Step 3 guidance</b>"
        "<ul style='margin-top:6px; margin-bottom:6px'>"
        "<li><b>Train vs test balance:</b> choose how many years to reserve for testing. Watch how test skill changes.</li>"
        "<li><b>Blocked vs random:</b> random splits can create <i>leakage</i> when y(t) is autocorrelated (nearby years are not independent).</li>"
        "<li><b>Trends:</b> shared trends can create spurious skill. Try toggling <b>Detrend</b>.</li>"
        "</ul>"
        "</div>"
    ),
    sizing_mode="stretch_width",
)

interpretation_div = Div(text="", sizing_mode="stretch_width")

equation_div = Div(text="", sizing_mode="stretch_width")


# -----------------------------
# State
# -----------------------------


state: Dict[str, object] = {
    "run_index": 0,
    "active_scenario": "Null overfitting",
    "applying_scenario": False,
}


# -----------------------------
# Helpers: scenario logic
# -----------------------------


def current_yx_params() -> YXParams:
    return YXParams(
        start_year=int(start_year.value),
        n_years=int(n_years.value),
        phi_y=float(phi_y.value),
        sigma_y=float(sigma_y.value),
        trend_y=float(trend_y.value),
        n_predictors=int(n_predictors.value),
        phi_x=float(phi_x.value),
        sigma_x=float(sigma_x.value),
        trend_x=float(trend_x.value),
    )


def yx_matches(a: YXParams, b: YXParams) -> bool:
    # Sliders have discrete steps; isclose is safe and tolerant.
    return (
        a.start_year == b.start_year
        and a.n_years == b.n_years
        and a.n_predictors == b.n_predictors
        and np.isclose(a.phi_y, b.phi_y)
        and np.isclose(a.sigma_y, b.sigma_y)
        and np.isclose(a.trend_y, b.trend_y)
        and np.isclose(a.phi_x, b.phi_x)
        and np.isclose(a.sigma_x, b.sigma_x)
        and np.isclose(a.trend_x, b.trend_x)
    )


def set_active_scenario(name: str | None) -> None:
    state["active_scenario"] = name

    btn_scn_null.button_type = "success" if name == "Null overfitting" else "default"
    btn_scn_leak.button_type = "success" if name == "Leakage" else "default"
    btn_scn_trend.button_type = "success" if name == "Shared trend trap" else "default"

    if name is None:
        scenario_status.text = (
            "<div style='font-size:12.5px; color:#555'>"
            "Scenario: <b>Custom</b> (you changed a y/X setting)."
            "</div>"
        )
    else:
        desc, _ = SCENARIOS[name]
        scenario_status.text = (
            "<div style='font-size:12.5px; color:#555'>"
            f"Scenario: <b>{name}</b>. "
            "<span style='color:#777'>(Scenarios only fill in Steps 1–2.)</span>"
            "</div>"
            f"<div style='font-size:12.5px; color:#666; margin-top:2px'>{desc}</div>"
        )


def apply_scenario(name: str) -> None:
    """Set Step 1–2 sliders from a scenario and mark it active."""
    state["applying_scenario"] = True

    _, yx = SCENARIOS[name]

    start_year.value = yx.start_year
    n_years.value = yx.n_years
    phi_y.value = yx.phi_y
    sigma_y.value = yx.sigma_y
    trend_y.value = yx.trend_y

    n_predictors.value = yx.n_predictors
    phi_x.value = yx.phi_x
    sigma_x.value = yx.sigma_x
    trend_x.value = yx.trend_x

    highlight_pred.value = 1

    # Reset resampling history because the data-generating process changed
    state["run_index"] = 0
    src_hist.data = {"r_train": [], "r_test": []}

    state["applying_scenario"] = False
    set_active_scenario(name)


# -----------------------------
# Update functions
# -----------------------------


def update_slider_bounds() -> None:
    # Keep at least 5 test years
    n_train.start = 5
    n_train.end = max(6, int(n_years.value) - 5)
    if n_train.value > n_train.end:
        n_train.value = n_train.end

    # Highlight predictor slider bounds
    highlight_pred.start = 1
    highlight_pred.end = max(1, int(n_predictors.value))
    if highlight_pred.value > highlight_pred.end:
        highlight_pred.value = 1

    # Update training slider title to show both counts
    n_te = int(n_years.value) - int(n_train.value)
    n_train.title = f"Training years (Train: {int(n_train.value)}, Test: {n_te})"


def format_interpretation(run: Dict[str, object]) -> str:
    p = int(run["p"])
    ntr = int(run["n_train"])
    ratio = float(run["ratio"])
    phi = float(run["phi_y"])
    n_eff = float(run["n_eff"])

    rmse_model = float(run["rmse_test"])
    rmse_mean = float(run["rmse_test_mean"])
    rmse_trend = float(run["rmse_test_trend"])

    warn = ""
    if p >= ntr - 1:
        warn = (
            "<div style='color:#d93025; font-weight:600; margin-top:6px'>"
            "Warning: p ≥ n<sub>train</sub>−1. The model can (nearly) interpolate training data. "
            "This often destroys out-of-sample performance."  # concise
            "</div>"
        )
    elif ratio > 0.4:
        warn = (
            "<div style='color:#d93025; font-weight:600; margin-top:6px'>"
            "Caution: high p/n<sub>train</sub> (higher overfitting risk)."
            "</div>"
        )

    html = f"""
    <div style='font-size:13px; line-height:1.35'>
      <b>How to interpret the diagnostics</b>
      <ul style='margin-top:6px; margin-bottom:6px'>
        <li><b>Complexity:</b> p={p} predictors with n<sub>train</sub>={ntr} years → p/n<sub>train</sub>={ratio:.2f}.</li>
        <li><b>Dependence:</b> ϕ<sub>y</sub>={phi:.2f} → rough effective sample size n<sub>eff</sub>≈{n_eff:.1f} (heuristic).</li>
        <li><b>Baselines (test RMSE):</b> mean-only={rmse_mean:.2f}, trend-only={rmse_trend:.2f}. Your model RMSE={rmse_model:.2f}.</li>
      </ul>
      {warn}
    </div>
    """
    return html


def format_equation(run: Dict[str, object]) -> str:
    b0 = float(run["coef_intercept"])
    b = np.asarray(run["coef"], dtype=float)
    p = len(b)

    # Use generic names X1..Xp
    terms = []
    for j in range(p):
        coef = b[j]
        name = f"X{j+1}"
        terms.append(f"{coef:+.3f}·{name}")

    # Break into lines for readability
    chunk = 6
    lines = [" ".join(terms[i : i + chunk]) for i in range(0, p, chunk)]
    rhs = "<br/>".join(lines)

    if bool(run["detrend"]):
        header = "<b>Fitted OLS equation (applied to <i>anomalies</i>)</b>"
        note = "<span style='color:#777'>(Trends are removed using the training period, then added back to ŷ.)</span>"
    else:
        header = "<b>Fitted OLS equation</b>"
        note = ""

    html = f"""
    <div style='font-size:13px; line-height:1.35'>
      {header} {note}<br/>
      <div style='font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
                  font-size:12.5px; margin-top:6px; max-height:110px; overflow:auto; border:1px solid #eee; padding:8px'>
        ŷ = {b0:+.3f} <br/>
        {rhs}
      </div>
    </div>
    """
    return html


def update_all(add_to_history: bool) -> None:
    update_slider_bounds()

    # If user changed y/X settings after pressing a scenario button, switch to Custom
    if not bool(state.get("applying_scenario", False)):
        active = state.get("active_scenario")
        if isinstance(active, str) and active in SCENARIOS:
            _, yx_ref = SCENARIOS[active]
            if not yx_matches(current_yx_params(), yx_ref):
                set_active_scenario(None)

    # Run model
    yx = current_yx_params()
    params = Params(
        yx=yx,
        n_train=int(n_train.value),
        split_method=str(split_method.value),
        detrend=bool(detrend_toggle.active),
    )

    seed = int(seed_base.value) + int(state["run_index"])
    run = fit_and_score(seed, params)

    years = run["years"]
    y = run["y"]
    X = run["X"]
    yhat = run["yhat"]
    train_mask = run["train_mask"]
    test_mask = run["test_mask"]

    # Step 1: y plot
    src_y.data = {"year": years, "y": y}

    # Step 2: predictor multi-line
    p = X.shape[1]
    names = predictor_names(p)
    hi = int(highlight_pred.value) - 1
    hi = int(np.clip(hi, 0, p - 1))

    xs = [years.tolist() for _ in range(p)]
    ys = [X[:, j].tolist() for j in range(p)]
    alpha = [1.0 if j == hi else 0.15 for j in range(p)]
    width = [3.0 if j == hi else 1.0 for j in range(p)]
    color = [BLUE if j == hi else LIGHT_GREY for j in range(p)]
    src_X.data = {"xs": xs, "ys": ys, "name": names, "alpha": alpha, "width": width, "color": color}

    # Step 2: scatter y vs highlighted predictor
    src_sc_yx.data = {"x": X[:, hi], "y": y}
    r_yx = corr(X[:, hi], y)

    # Simple multiple-comparisons indicator: max |r| across predictors
    r_all = np.array([corr(X[:, j], y) for j in range(p)], dtype=float)
    if np.any(np.isfinite(r_all)):
        j_best = int(np.nanargmax(np.abs(r_all)))
        best_txt = f"Best of p predictors (max |r|): X{j_best+1} with r={r_all[j_best]:+.2f}"
    else:
        best_txt = "Best of p predictors: n/a"

    pred_corr_div.text = (
        "<div style='font-size:13px; line-height:1.35'>"
        f"<b>Highlighted predictor:</b> X{hi+1}<br/>"
        f"Correlation with y over the full record: <b>r={r_yx:+.2f}</b><br/>"
        f"<span style='color:#666'>{best_txt}</span>"
        "</div>"
    )

    fig_yx.title.text = f"Step 2 — Scatter: y vs X{hi+1} (r={r_yx:+.2f})"

    # Step 3: time series points + predictions
    src_obs_train.data = {"year": years[train_mask], "y": y[train_mask]}
    src_obs_test.data = {"year": years[test_mask], "y": y[test_mask]}
    src_pred_train.data = {"year": years[train_mask], "yhat": yhat[train_mask]}
    src_pred_test.data = {"year": years[test_mask], "yhat": yhat[test_mask]}

    # Split shading
    if params.split_method == "Blocked":
        # Training is the first block
        train_box.left = years[0] - 0.5
        train_box.right = years[int(run["n_train"]) - 1] + 0.5
        test_box.left = years[int(run["n_train"]) ] - 0.5
        test_box.right = years[-1] + 0.5
        train_box.visible = True
        test_box.visible = True
        split_span.location = years[int(run["n_train"]) ] - 0.5
        split_span.visible = True

        pred_train_line.visible = True
        pred_test_line.visible = True
    else:
        # Random split: no contiguous blocks to shade
        train_box.visible = False
        test_box.visible = False
        split_span.visible = False

        # Don't connect non-consecutive years
        pred_train_line.visible = False
        pred_test_line.visible = False

    # Step 3: scatters
    src_sc_train.data = {"obs": run["y_train"], "pred": run["yhat_train"]}
    src_sc_test.data = {"obs": run["y_test"], "pred": run["yhat_test"]}

    # 1:1 lines and ranges
    def _lims(a: np.ndarray, b: np.ndarray, pad: float = 0.2) -> Tuple[float, float]:
        mn = float(np.min([np.min(a), np.min(b)]))
        mx = float(np.max([np.max(a), np.max(b)]))
        span = max(1e-9, mx - mn)
        return mn - pad * span, mx + pad * span

    tr_lo, tr_hi = _lims(run["y_train"], run["yhat_train"])
    te_lo, te_hi = _lims(run["y_test"], run["yhat_test"])

    src_line_train.data = {"x": [tr_lo, tr_hi], "y": [tr_lo, tr_hi]}
    src_line_test.data = {"x": [te_lo, te_hi], "y": [te_lo, te_hi]}

    sc_tr.x_range.start, sc_tr.x_range.end = tr_lo, tr_hi
    sc_tr.y_range.start, sc_tr.y_range.end = tr_lo, tr_hi
    sc_te.x_range.start, sc_te.x_range.end = te_lo, te_hi
    sc_te.y_range.start, sc_te.y_range.end = te_lo, te_hi

    sc_tr.title.text = f"Training scatter (r={run['r_train']:+.2f}, RMSE={run['rmse_train']:.2f})"
    sc_te.title.text = f"Test scatter (r={run['r_test']:+.2f}, RMSE={run['rmse_test']:.2f})"

    # Interpretation and equation blocks
    interpretation_div.text = format_interpretation(run)
    equation_div.text = format_equation(run)

    # Optional resampling history
    hist.visible = bool(show_history_toggle.active)
    if add_to_history:
        src_hist.stream({"r_train": [float(run["r_train"])], "r_test": [float(run["r_test"])]}, rollover=1000)


# -----------------------------
# Callbacks
# -----------------------------


def on_any_change(attr: str, old: object, new: object) -> None:
    # Avoid multiple intermediate updates while applying a scenario
    if bool(state.get("applying_scenario", False)):
        return
    update_all(add_to_history=False)


def on_resample() -> None:
    state["run_index"] = int(state["run_index"]) + 1
    update_all(add_to_history=True)


def on_reset_history() -> None:
    src_hist.data = {"r_train": [], "r_test": []}


def on_scenario_button(name: str) -> None:
    apply_scenario(name)
    update_all(add_to_history=False)


btn_resample.on_click(on_resample)
btn_reset_history.on_click(on_reset_history)

btn_scn_null.on_click(lambda: on_scenario_button("Null overfitting"))
btn_scn_leak.on_click(lambda: on_scenario_button("Leakage"))
btn_scn_trend.on_click(lambda: on_scenario_button("Shared trend trap"))

# Widget change callbacks
for w in [
    seed_base,
    start_year,
    n_years,
    phi_y,
    sigma_y,
    trend_y,
    n_predictors,
    phi_x,
    sigma_x,
    trend_x,
    highlight_pred,
    n_train,
    split_method,
    detrend_toggle,
    show_history_toggle,
]:
    prop = "value" if hasattr(w, "value") else "active"
    w.on_change(prop, on_any_change)


# -----------------------------
# Layout
# -----------------------------


title = Div(text="<h2 style='margin:0'>Overfitting & spurious skill — build data, then model</h2>")

scenario_help = Div(
    text=(
        "<div style='font-size:12.5px; color:#666'>"
        "Scenarios populate <b>Step 1</b> (y) and <b>Step 2</b> (X). "
        "If you edit a y/X setting, the scenario switches to <b>Custom</b>."
        "</div>"
    ),
    sizing_mode="stretch_width",
)

# Info icons next to scenario buttons
info_null = Div(
    text=f"<span title='{SCENARIOS['Null overfitting'][0]}' style='{INFO_ICON_STYLE}'>ⓘ</span>",
    width=18,
)
info_leak = Div(
    text=f"<span title='{SCENARIOS['Leakage'][0]}' style='{INFO_ICON_STYLE}'>ⓘ</span>",
    width=18,
)
info_trend = Div(
    text=f"<span title='{SCENARIOS['Shared trend trap'][0]}' style='{INFO_ICON_STYLE}'>ⓘ</span>",
    width=18,
)

scenario_row = row(
    Div(text="<b>Scenarios:</b>", width=80),
    btn_scn_null,
    info_null,
    btn_scn_leak,
    info_leak,
    btn_scn_trend,
    info_trend,
    Spacer(width=10),
    seed_base,
    btn_resample,
    btn_reset_history,
    sizing_mode="stretch_width",
)

# Step 1 controls
step1_controls = column(
    Div(text="<h3 style='margin:0'>Step 1: Generate observed y(t)</h3>"),
    step1_text,
    start_year,
    n_years,
    phi_y,
    sigma_y,
    trend_y,
    width=360,
)

# Step 2 controls
step2_controls = column(
    Div(text="<h3 style='margin:0'>Step 2: Generate predictors X(t)</h3>"),
    step2_text,
    n_predictors,
    phi_x,
    sigma_x,
    trend_x,
    highlight_pred,
    width=360,
)

# Step 3 controls
step3_controls = column(
    Div(text="<h3 style='margin:0'>Step 3: Fit + evaluate (OLS MLR)</h3>"),
    step3_text,
    n_train,
    split_method,
    detrend_toggle,
    show_history_toggle,
    width=360,
)

# Assemble steps vertically
layout = column(
    title,
    scenario_help,
    scenario_row,
    scenario_status,
    Div(text="<hr style='margin:10px 0'>"),
    row(step1_controls, fig_y, sizing_mode="stretch_width"),
    Div(text="<hr style='margin:10px 0'>"),
    row(
        step2_controls,
        column(
            fig_X,
            row(fig_yx, column(pred_corr_div, sizing_mode="stretch_width"), sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
    ),
    Div(text="<hr style='margin:10px 0'>"),
    row(
        step3_controls,
        column(
            fig_ts,
            row(sc_tr, sc_te, sizing_mode="stretch_width"),
            interpretation_div,
            equation_div,
            hist,
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
    ),
    sizing_mode="stretch_width",
)

curdoc().add_root(layout)
curdoc().title = "Overfitting pedagogical app"


# -----------------------------
# Initial state
# -----------------------------


apply_scenario("Null overfitting")
update_all(add_to_history=False)
