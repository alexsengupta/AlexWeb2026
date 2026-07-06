#!/usr/bin/env python3
"""
MHW Live - daily updater.

Downloads the newest NOAA Coral Reef Watch Daily Global 5 km Satellite
Marine Heatwave *category* file, renders a polished Robinson-projection map
(title, date, legend, and a 60 S-60 N area inset all baked into the PNG),
and writes latest.png + meta.js next to this script. index.html shows them.

Run once a day via cron (see README.md).

Requires: python3, numpy, netCDF4, matplotlib, cartopy, scipy
    pip3 install numpy netCDF4 matplotlib cartopy scipy

Data source (public, date-stamped filenames - no session links):
  https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/marine_heatwave/
      v1.0.1/category/nc/<YYYY>/noaa-crw_mhw_v1.0.1_category_<YYYYMMDD>.nc
"""
import os
import sys
import json
import datetime as dt
import urllib.request
import urllib.error

import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches
import cartopy.crs as ccrs

# ---------------------------------------------------------------- config -----
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")          # downloaded .nc files
KEEP_NC_DAYS = 7
MAX_LOOKBACK = 16                           # days to walk back for newest file
CENTRAL_LON = 0                             # map centre longitude (try 180 for Pacific-centred)
BASE = ("https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/"
        "marine_heatwave/v1.0.1/category/nc")

# palette
OCEAN = "#dbe6ee"
CAT   = ["#ffd24c", "#ff9a2e", "#e02b2b", "#8f0f2e", "#5a1a8a"]   # cat 1..5
LAND  = "#c9ccd1"
ICE   = "#eef4fb"
INK   = "#0c356a"
CAT_LABELS = ["Moderate", "Strong", "Severe", "Extreme", "Beyond extreme"]


# --------------------------------------------------------------- download ----
def url_for(day):
    return f"{BASE}/{day:%Y}/noaa-crw_mhw_v1.0.1_category_{day:%Y%m%d}.nc"


def download_newest():
    os.makedirs(DATA, exist_ok=True)
    today = dt.date.today()
    last_err = None
    for back in range(MAX_LOOKBACK):
        day = today - dt.timedelta(days=back)
        dest = os.path.join(DATA, os.path.basename(url_for(day)))
        if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
            return dest, day
        try:
            req = urllib.request.Request(url_for(day),
                                         headers={"User-Agent": "mhw-live/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                f.write(r.read())
            if os.path.getsize(dest) > 100_000:
                print("downloaded", url_for(day))
                return dest, day
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 404:
                continue
            raise
        except Exception as e:            # noqa: BLE001
            last_err = e
            continue
    raise RuntimeError(f"No CRW file found in last {MAX_LOOKBACK} days ({last_err})")


# ------------------------------------------------------------- computation ---
def _classify(ds, max_width=2400):
    cat  = np.asarray(ds["heatwave_category"][0]).astype(np.int16)
    mask = np.asarray(ds["mask"][0]).astype(np.int16)     # 0 water 1 land 2 miss 4 ice
    lat  = ds["lat"][:]

    out = np.zeros(cat.shape, dtype=np.uint8)
    water = (mask == 0)
    out[water] = np.clip(cat[water], 0, 5)
    out[mask == 1] = 6
    out[mask == 4] = 7
    out[mask == 2] = 6
    if lat[0] < lat[-1]:
        out = out[::-1, :]
        lat = lat[::-1]
    step = max(1, out.shape[1] // max_width)
    if step > 1:
        out = out[::step, ::step]
    return out, cat, mask, lat


def _area_stats(cat, mask, lat, lat_limit=60.0):
    water = (mask == 0)
    band = (np.abs(lat) <= lat_limit)[:, None]
    w = np.cos(np.deg2rad(lat))[:, None] * water * band
    total = w.sum()
    fr = {c: float((w * (cat == c)).sum() / total) if total else 0.0
          for c in range(1, 6)}
    fr["mhw"] = sum(fr[c] for c in range(1, 6))
    return fr


# ----------------------------------------------------------------- render ----
def render(nc_path, png_path, day, max_width=2400):
    ds = nc.Dataset(nc_path)
    out, cat, mask, lat = _classify(ds, max_width)
    stats = _area_stats(cat, mask, lat)

    cmap = ListedColormap([OCEAN] + CAT + [LAND, ICE])
    norm = BoundaryNorm(np.arange(-0.5, 8.5, 1), cmap.N)
    proj = ccrs.Robinson(central_longitude=CENTRAL_LON)

    fig = plt.figure(figsize=(13, 7.9), dpi=200)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.02, 0.155, 0.96, 0.70], projection=proj)
    ax.set_global()
    ax.imshow(out, origin="upper", extent=[-180, 180, -90, 90],
              transform=ccrs.PlateCarree(), cmap=cmap, norm=norm,
              interpolation="nearest", regrid_shape=1600)
    ax.gridlines(color="white", linewidth=0.5, alpha=0.5)
    try:
        ax.spines["geo"].set_edgecolor("#9fb0ba")
    except Exception:                     # noqa: BLE001
        pass

    nice = day.strftime("%-d %B %Y")
    fig.text(0.5, 0.967, "Global Marine Heatwaves", ha="center",
             fontsize=23, fontweight="bold", color=INK)
    fig.text(0.5, 0.928, nice, ha="center", fontsize=13, color="#41586e")
    fig.text(0.5, 0.895,
             f"{stats['mhw']*100:.1f}% of ocean area (60°S–60°N) in a marine heatwave",
             ha="center", fontsize=11.5, color="#41586e")

    # ---- bottom legend: enlarged swatches + per-category % (area 60S-60N) ----
    def fmt(v):                       # v is a fraction 0..1
        p = v * 100
        if p == 0:
            return "0%"
        if p < 0.1:
            return "<0.1%"
        return f"{p:.1f}%"

    lax = fig.add_axes([0.04, 0.03, 0.92, 0.12])
    lax.set_xlim(0, 1)
    lax.set_ylim(0, 1)
    lax.axis("off")
    labels = ["No MHW"] + CAT_LABELS
    colours = [OCEAN] + CAT
    pcts = [None] + [fmt(stats[c]) for c in range(1, 6)]   # No MHW has no %
    n = len(labels)
    for i in range(n):
        xc = (i + 0.5) / n
        lax.scatter([xc], [0.72], marker="s", s=1400, c=[colours[i]],
                    edgecolors=("#b9c6d1" if i == 0 else "none"),
                    linewidths=1.0, zorder=3)
        lax.text(xc, 0.34, labels[i], ha="center", va="center",
                 fontsize=11.5, color="#26333d")
        if pcts[i] is not None:
            lax.text(xc, 0.06, pcts[i], ha="center", va="center",
                     fontsize=13, fontweight="bold", color="#26333d")

    fig.text(0.985, 0.008,
             "Data: NOAA Coral Reef Watch Daily 5 km MHW v1.0.1  ·  categories per Hobday et al.",
             ha="right", va="bottom", fontsize=7.5, color="#9aa7b2")
    fig.savefig(png_path, dpi=200, facecolor="white")
    plt.close(fig)
    return stats


# ---------------------------------------------------------------- cleanup ----
def prune_old_nc():
    if not os.path.isdir(DATA):
        return
    cutoff = dt.date.today() - dt.timedelta(days=KEEP_NC_DAYS)
    for f in os.listdir(DATA):
        if f.endswith(".nc"):
            try:
                d = dt.datetime.strptime(f[-11:-3], "%Y%m%d").date()
            except ValueError:
                continue
            if d < cutoff:
                os.remove(os.path.join(DATA, f))


# ------------------------------------------------------------------- main ----
def main():
    nc_path, day = download_newest()
    stats = render(nc_path, os.path.join(HERE, "latest.png"), day)
    meta = {
        "data_date": day.isoformat(),
        "generated_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "source": url_for(day),
        "mhw_fraction_60": stats["mhw"],
        "by_category_60": {str(c): stats[c] for c in range(1, 6)},
    }
    with open(os.path.join(HERE, "meta.js"), "w") as f:
        f.write("window.MHW_META = " + json.dumps(meta) + ";\n")
    with open(os.path.join(HERE, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    prune_old_nc()
    print(f"OK  data_date={meta['data_date']}  mhw60={stats['mhw']*100:.1f}%")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                # noqa: BLE001
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
