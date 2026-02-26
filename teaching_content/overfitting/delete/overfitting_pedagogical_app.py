"""overfitting_pedagogical_app.py

A lightweight Bokeh server app inspired by fig3_overfitting.py.

Purpose
-------
Pedagogical demonstration of:
  1) Overfitting (training fit != predictive skill)
  2) Why time-series validation should be blocked (random splits leak)
  3) How autocorrelation and shared trends can create spurious relationships

Run
---
  bokeh serve --show overfitting_pedagogical_app.py

Dependencies
------------
  numpy, bokeh, scikit-learn
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (
    BoxAnnotation,
    Button,
    ColumnDataSource,
    Div,
    Select,
    Slider,
    Span,
    Toggle,
)
from bokeh.plotting import figure

from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, root_mean_squared_error


# -----------------------------
# Defaults + labels
# -----------------------------

DEFAULT_PRED_NAMES = [
    "MHW freq",
    "MHW dur",
    "MHW int",
    "MHW cum",
    "SST anom",
    "Chl-a",
    "MLD",
    "Wind spd",
    "Precip",
    "ENSO idx",
    "SAM idx",
    "IOD idx",
]

BLUE = "#1a73e8"
RED = "#d93025"
GREY = "#333333"
MID_GREY = "#666666"


@dataclass
class Params:
    start_year: int
    n_years: int
    n_train: int
    n_predictors: int
    phi_y: float
    sigma_y: float
    trend_y: float
    phi_x: float
    sigma_x: float
    trend_x: float
    split_method: str  # "Blocked" or "Random"
    detrend: bool
    model_type: str  # "OLS" or "Ridge"
    ridge_log10_alpha: float


def _safe_float(x: float, lo: float, hi: float) -> float:
    return float(np.clip(x, lo, hi))


def ar1_series(phi: float, n: int, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Generate stationary AR(1) with approximate marginal std ~= sigma."""
    phi = _safe_float(phi, -0.999, 0.999)
    # innovation variance so that Var(x) ~ sigma^2 for stationary AR(1)
    innov_sd = sigma * np.sqrt(max(1e-12, 1.0 - phi**2))
    e = rng.normal(0.0, innov_sd, n)
    x = np.empty(n, dtype=float)
    x[0] = rng.normal(0.0, sigma)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def fit_linear_trend(t: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Return (intercept, slope) of y ~ a + b t."""
    if len(t) < 2:
        return float(y.mean()) if len(y) else 0.0, 0.0
    b, a = np.polyfit(t, y, 1)  # returns slope, intercept
    return float(a), float(b)


def detrend_using_training(t: np.ndarray, y: np.ndarray, train_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Detrend y using linear fit on training portion only.

    Returns
    -------
    y_anom : y - trend_fit
    trend_fit : fitted trend evaluated for all t
    """
    t_tr = t[train_mask]
    y_tr = y[train_mask]
    a, b = fit_linear_trend(t_tr, y_tr)
    trend_fit = a + b * t
    return y - trend_fit, trend_fit


def predictor_names(p: int) -> List[str]:
    names = list(DEFAULT_PRED_NAMES)
    if p <= len(names):
        return names[:p]
    # Extend with generic names
    extra = [f"X{idx}" for idx in range(len(names) + 1, p + 1)]
    return names + extra


def split_indices(
    n_years: int,
    n_train: int,
    split_method: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return boolean mask of length n_years marking training indices."""
    n_train = int(n_train)
    if split_method == "Blocked":
        mask = np.zeros(n_years, dtype=bool)
        mask[:n_train] = True
        return mask
    # Random split (same train size)
    idx = np.arange(n_years)
    train_idx = rng.choice(idx, size=n_train, replace=False)
    mask = np.zeros(n_years, dtype=bool)
    mask[train_idx] = True
    return mask


def simulate_and_fit(seed: int, params: Params) -> Dict[str, object]:
    rng = np.random.default_rng(int(seed))

    years = np.arange(params.start_year, params.start_year + params.n_years)
    t = np.arange(params.n_years, dtype=float)

    train_mask = split_indices(params.n_years, params.n_train, params.split_method, rng)
    test_mask = ~train_mask

    # Response
    y = ar1_series(params.phi_y, params.n_years, params.sigma_y, rng)
    y = y + params.trend_y * (t - t[0])

    # Predictors
    X = np.empty((params.n_years, params.n_predictors), dtype=float)
    for j in range(params.n_predictors):
        X[:, j] = ar1_series(params.phi_x, params.n_years, params.sigma_x, rng)
    if abs(params.trend_x) > 0:
        X = X + params.trend_x * (t - t[0])[:, None]

    # Optional detrending (fit trends on training only; apply to all)
    if params.detrend:
        y_anom, y_trend_fit = detrend_using_training(t, y, train_mask)
        X_anom = np.empty_like(X)
        X_trends = np.empty_like(X)
        for j in range(params.n_predictors):
            X_anom[:, j], X_trends[:, j] = detrend_using_training(t, X[:, j], train_mask)
    else:
        y_anom, y_trend_fit = y.copy(), np.zeros_like(y)
        X_anom = X

    # Model
    if params.model_type == "Ridge":
        alpha = 10 ** float(params.ridge_log10_alpha)
        reg = Ridge(alpha=alpha, fit_intercept=True)
    else:
        reg = LinearRegression(fit_intercept=True)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("reg", reg),
        ]
    )

    X_train = X_anom[train_mask]
    y_train = y_anom[train_mask]
    X_test = X_anom[test_mask]
    y_test = y_anom[test_mask]

    model.fit(X_train, y_train)
    yhat_anom = model.predict(X_anom)

    # Add trend back to get predictions for y
    yhat = y_trend_fit + yhat_anom

    # Metrics on ORIGINAL y (not anomalies)
    y_train_orig = y[train_mask]
    y_test_orig = y[test_mask]
    yhat_train = yhat[train_mask]
    yhat_test = yhat[test_mask]

    r2_train = float(r2_score(y_train_orig, yhat_train)) if len(y_train_orig) >= 2 else float("nan")
    r2_test = float(r2_score(y_test_orig, yhat_test)) if len(y_test_orig) >= 2 else float("nan")
    rmse_train = float(root_mean_squared_error(y_train_orig, yhat_train))
    rmse_test = float(root_mean_squared_error(y_test_orig, yhat_test))

    # Baselines
    mean_baseline_test = np.full_like(y_test_orig, float(y_train_orig.mean()))
    rmse_test_mean = float(root_mean_squared_error(y_test_orig, mean_baseline_test))

    # Trend-only baseline (fit on training, predict on all)
    a0, b0 = fit_linear_trend(t[train_mask], y_train_orig)
    y_trend_only_all = a0 + b0 * t
    rmse_test_trend = float(root_mean_squared_error(y_test_orig, y_trend_only_all[test_mask]))

    # Coefficients (standardised predictors)
    coefs = model.named_steps["reg"].coef_.ravel().astype(float)
    intercept = float(model.named_steps["reg"].intercept_)
    names = predictor_names(params.n_predictors)
    coef_pairs = list(zip(names, coefs))
    coef_pairs_sorted = sorted(coef_pairs, key=lambda x: abs(x[1]), reverse=True)

    return {
        "years": years,
        "t": t,
        "y": y,
        "yhat": yhat,
        "train_mask": train_mask,
        "test_mask": test_mask,
        "y_train": y_train_orig,
        "y_test": y_test_orig,
        "yhat_train": yhat_train,
        "yhat_test": yhat_test,
        "r2_train": r2_train,
        "r2_test": r2_test,
        "rmse_train": rmse_train,
        "rmse_test": rmse_test,
        "rmse_test_mean": rmse_test_mean,
        "rmse_test_trend": rmse_test_trend,
        "intercept": intercept,
        "coef_pairs_sorted": coef_pairs_sorted,
    }


def format_metrics(run: Dict[str, object], params: Params) -> str:
    n_train = int(params.n_train)
    p = int(params.n_predictors)
    ratio = p / max(1, n_train)

    phi_y = float(params.phi_y)
    n_eff = n_train * (1 - phi_y) / (1 + phi_y) if abs(1 + phi_y) > 1e-12 else 0.0
    n_eff = float(np.clip(n_eff, 1.0, float(n_train)))

    r2_tr = run["r2_train"]
    r2_te = run["r2_test"]
    rmse_tr = run["rmse_train"]
    rmse_te = run["rmse_test"]
    rmse_mean = run["rmse_test_mean"]
    rmse_trend = run["rmse_test_trend"]

    warn = ""
    if p >= n_train - 1:
        warn = (
            "<div style='color:#d93025; font-weight:600; margin-top:6px'>"
            "Warning: p ≥ n<sub>train</sub>−1 → OLS can (nearly) interpolate training data." 
            "Generalisation is usually poor."
            "</div>"
        )
    elif ratio > 0.4:
        warn = (
            "<div style='color:#d93025; font-weight:600; margin-top:6px'>"
            "Caution: high p/n<sub>train</sub> (likely overfitting)."
            "</div>"
        )

    detrend_note = "on" if params.detrend else "off"
    model_note = params.model_type
    if params.model_type == "Ridge":
        model_note += f" (α=10^{params.ridge_log10_alpha:.1f})"

    html = f"""
    <div style='font-size:13px; line-height:1.35'>
      <div><b>Model:</b> {model_note} &nbsp; | &nbsp; <b>Detrend:</b> {detrend_note} &nbsp; | &nbsp; <b>Split:</b> {params.split_method}</div>

      <div style='margin-top:8px'><b>Fit quality</b></div>
      <ul style='margin-top:4px; margin-bottom:6px'>
        <li><b>Training</b>: R²={r2_tr:+.2f}, RMSE={rmse_tr:.2f}</li>
        <li><b>Test</b>: R²={r2_te:+.2f}, RMSE={rmse_te:.2f}</li>
      </ul>

      <div style='margin-top:6px'><b>Baselines (test RMSE)</b></div>
      <ul style='margin-top:4px; margin-bottom:6px'>
        <li>Mean of training: {rmse_mean:.2f}</li>
        <li>Linear trend (fit on training): {rmse_trend:.2f}</li>
      </ul>

      <div style='margin-top:6px'><b>Complexity & dependence</b></div>
      <ul style='margin-top:4px; margin-bottom:0px'>
        <li>n<sub>train</sub>={n_train}, p={p}, p/n<sub>train</sub>={ratio:.2f}</li>
        <li>ϕ<sub>y</sub>={phi_y:.2f} → rough n<sub>eff</sub>≈{n_eff:.1f} (heuristic)</li>
      </ul>
      {warn}
    </div>
    """
    return html


def format_coeffs(run: Dict[str, object], top_k: int = 6) -> str:
    pairs = run["coef_pairs_sorted"]
    intercept = float(run["intercept"])
    top = pairs[:top_k]

    rows = "".join(
        f"<tr><td style='padding:2px 8px 2px 0'>{name}</td><td style='padding:2px 0; text-align:right'>{coef:+.3f}</td></tr>"
        for name, coef in top
    )

    html = f"""
    <div style='font-size:13px; line-height:1.35'>
      <div style='margin-top:6px'><b>Largest coefficients (standardised X)</b></div>
      <div style='font-size:12px; color:#555'>Intercept: {intercept:+.3f}</div>
      <table style='border-collapse:collapse; margin-top:4px'>
        {rows}
      </table>
      <div style='font-size:12px; color:#555; margin-top:4px'>
        (In the <i>null</i> world these are just chance.)
      </div>
    </div>
    """
    return html


# -----------------------------
# Widgets
# -----------------------------

scenario = Select(
    title="Scenario",
    value="Overfitting under the null",
    options=[
        "Overfitting under the null",
        "Autocorrelation + random split (leakage)",
        "Shared trend trap",
    ],
)

start_year = Slider(title="Start year", start=1900, end=2025, step=1, value=1985)
n_years = Slider(title="Total years", start=20, end=100, step=1, value=40)
n_train = Slider(title="Training years", start=5, end=95, step=1, value=25)

n_predictors = Slider(title="# predictors (p)", start=1, end=40, step=1, value=12)

phi_y = Slider(title="Response AR(1) ϕᵧ", start=-0.2, end=0.95, step=0.05, value=0.50)
sigma_y = Slider(title="Response std (σᵧ)", start=0.2, end=2.0, step=0.1, value=0.8)
trend_y = Slider(title="Response trend (units/yr)", start=-0.2, end=0.2, step=0.01, value=0.0)

phi_x = Slider(title="Predictor AR(1) ϕₓ", start=-0.2, end=0.95, step=0.05, value=0.0)
sigma_x = Slider(title="Predictor std (σₓ)", start=0.2, end=2.0, step=0.1, value=1.0)
trend_x = Slider(title="Predictor shared trend (units/yr)", start=-0.2, end=0.2, step=0.01, value=0.0)

split_method = Select(title="Split", value="Blocked", options=["Blocked", "Random"])

detrend_toggle = Toggle(label="Detrend (fit anomalies + re-add trend)", button_type="default", active=False)

model_type = Select(title="Model", value="OLS", options=["OLS", "Ridge"])
ridge_log10_alpha = Slider(title="Ridge strength log10(α)", start=-3.0, end=3.0, step=0.1, value=0.0)

seed_base = Slider(title="Base seed", start=0, end=9999, step=1, value=96)

btn_resample = Button(label="Resample (new realisation)", button_type="primary")
btn_reset_history = Button(label="Reset history", button_type="default")


# -----------------------------
# Data sources
# -----------------------------

src_obs = ColumnDataSource(data=dict(year=[], y=[]))
src_obs_train = ColumnDataSource(data=dict(year=[], y=[]))
src_obs_test = ColumnDataSource(data=dict(year=[], y=[]))

src_pred_train = ColumnDataSource(data=dict(year=[], yhat=[]))
src_pred_test = ColumnDataSource(data=dict(year=[], yhat=[]))

src_sc_train = ColumnDataSource(data=dict(obs=[], pred=[]))
src_sc_test = ColumnDataSource(data=dict(obs=[], pred=[]))
src_line_train = ColumnDataSource(data=dict(x=[], y=[]))
src_line_test = ColumnDataSource(data=dict(x=[], y=[]))

src_hist = ColumnDataSource(data=dict(run=[], r2_train=[], r2_test=[]))


# -----------------------------
# Figures
# -----------------------------

ts = figure(
    height=320,
    sizing_mode="stretch_width",
    title="(a) Time series: training fit vs test prediction",
    x_axis_label="Year",
    y_axis_label="Synthetic response (units)",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)

# Background annotations for blocked split
train_box = BoxAnnotation(fill_color="#E8F0FE", fill_alpha=0.8)
test_box = BoxAnnotation(fill_color="#FDE8E8", fill_alpha=0.8)
ts.add_layout(train_box)
ts.add_layout(test_box)

split_span = Span(location=0, dimension="height", line_color=MID_GREY, line_dash="dashed", line_width=1.5)
ts.add_layout(split_span)

ts.line("year", "y", source=src_obs, line_color=GREY, line_width=2)
ts.circle("year", "y", source=src_obs_train, size=6, color=BLUE, alpha=0.9, legend_label="Observed (train)")
ts.circle("year", "y", source=src_obs_test, size=6, color=RED, alpha=0.9, legend_label="Observed (test)")

# Predictions: line + square markers (we'll hide the line for random splits)
r_pred_train_line = ts.line(
    "year", "yhat", source=src_pred_train, line_color=BLUE, line_width=2, alpha=0.85, legend_label="Model (train)"
)
r_pred_train_pts = ts.square(
    "year", "yhat", source=src_pred_train, size=7, color=BLUE, alpha=0.85, line_color="white"
)

r_pred_test_line = ts.line(
    "year", "yhat", source=src_pred_test, line_color=RED, line_width=2, alpha=0.85, legend_label="Model (test)"
)
r_pred_test_pts = ts.square(
    "year", "yhat", source=src_pred_test, size=7, color=RED, alpha=0.85, line_color="white"
)

ts.legend.location = "top_left"
ts.legend.click_policy = "hide"


sc_tr = figure(
    height=260,
    width=300,
    title="(b) Training scatter",
    x_axis_label="Observed",
    y_axis_label="Predicted",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
sc_tr.scatter("obs", "pred", source=src_sc_train, size=7, alpha=0.7, color=BLUE)
sc_tr.line("x", "y", source=src_line_train, line_dash="dashed", line_color="#999999")
sc_tr.match_aspect = True


sc_te = figure(
    height=260,
    width=300,
    title="(c) Test scatter",
    x_axis_label="Observed",
    y_axis_label="Predicted",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
sc_te.scatter("obs", "pred", source=src_sc_test, size=7, alpha=0.7, color=RED)
sc_te.line("x", "y", source=src_line_test, line_dash="dashed", line_color="#999999")
sc_te.match_aspect = True


hist = figure(
    height=260,
    width=340,
    title="History (each Resample adds one point)",
    x_axis_label="Training R²",
    y_axis_label="Test R²",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
hist.scatter("r2_train", "r2_test", source=src_hist, size=7, alpha=0.6)
hist.line([-1, 1], [-1, 1], line_dash="dotted", line_color="#999999")


metrics_div = Div(text="", sizing_mode="stretch_width")
coefs_div = Div(text="", sizing_mode="stretch_width")


howto_div = Div(
    text=(
        "<div style='font-size:13px; line-height:1.35'>"
        "<b>What to try</b>"
        "<ul style='margin-top:6px'>"
        "<li>Increase <b>p</b> (predictors) at fixed <b>n<sub>train</sub></b> → training R² rises, test R² often collapses.</li>"
        "<li>Switch <b>Split</b> to <b>Random</b> when ϕᵧ is high → apparent skill can be inflated (information leakage).</li>"
        "<li>Add <b>trend</b> to y and X → spurious skill; turn on <b>Detrend</b> to reduce it.</li>"
        "</ul>"
        "</div>"
    ),
    sizing_mode="stretch_width",
)


# -----------------------------
# App state
# -----------------------------

state: Dict[str, object] = {
    "run_index": 0,
    "last_run": None,
}


def get_params() -> Params:
    return Params(
        start_year=int(start_year.value),
        n_years=int(n_years.value),
        n_train=int(n_train.value),
        n_predictors=int(n_predictors.value),
        phi_y=float(phi_y.value),
        sigma_y=float(sigma_y.value),
        trend_y=float(trend_y.value),
        phi_x=float(phi_x.value),
        sigma_x=float(sigma_x.value),
        trend_x=float(trend_x.value),
        split_method=str(split_method.value),
        detrend=bool(detrend_toggle.active),
        model_type=str(model_type.value),
        ridge_log10_alpha=float(ridge_log10_alpha.value),
    )


def apply_scenario(name: str) -> None:
    """Set widget values for canned scenarios."""
    if name == "Overfitting under the null":
        start_year.value = 1985
        n_years.value = 40
        n_train.value = 25
        n_predictors.value = 12
        phi_y.value = 0.50
        sigma_y.value = 0.8
        trend_y.value = 0.0
        phi_x.value = 0.0
        sigma_x.value = 1.0
        trend_x.value = 0.0
        split_method.value = "Blocked"
        detrend_toggle.active = False
        model_type.value = "OLS"
        ridge_log10_alpha.value = 0.0
        return

    if name == "Autocorrelation + random split (leakage)":
        start_year.value = 1985
        n_years.value = 40
        n_train.value = 25
        n_predictors.value = 12
        phi_y.value = 0.85
        sigma_y.value = 0.8
        trend_y.value = 0.0
        phi_x.value = 0.0
        sigma_x.value = 1.0
        trend_x.value = 0.0
        split_method.value = "Random"
        detrend_toggle.active = False
        model_type.value = "OLS"
        ridge_log10_alpha.value = 0.0
        return

    if name == "Shared trend trap":
        start_year.value = 1985
        n_years.value = 50
        n_train.value = 30
        n_predictors.value = 12
        phi_y.value = 0.50
        sigma_y.value = 0.8
        trend_y.value = 0.08
        phi_x.value = 0.10
        sigma_x.value = 1.0
        trend_x.value = 0.08
        split_method.value = "Blocked"
        detrend_toggle.active = False
        model_type.value = "OLS"
        ridge_log10_alpha.value = 0.0
        return


def update_train_slider_bounds() -> None:
    # keep at least 5 years for test
    n_train.end = max(6, int(n_years.value) - 5)
    n_train.start = 5
    if n_train.value > n_train.end:
        n_train.value = n_train.end


def update_plots(add_to_history: bool) -> None:
    params = get_params()
    update_train_slider_bounds()

    # UI: only show ridge strength slider when Ridge is selected
    ridge_log10_alpha.visible = params.model_type == "Ridge"

    seed = int(seed_base.value) + int(state["run_index"])
    run = simulate_and_fit(seed, params)
    state["last_run"] = run

    years = run["years"]
    y = run["y"]
    yhat = run["yhat"]
    train_mask = run["train_mask"]
    test_mask = run["test_mask"]

    # Sources
    src_obs.data = {"year": years, "y": y}
    src_obs_train.data = {"year": years[train_mask], "y": y[train_mask]}
    src_obs_test.data = {"year": years[test_mask], "y": y[test_mask]}

    src_pred_train.data = {"year": years[train_mask], "yhat": yhat[train_mask]}
    src_pred_test.data = {"year": years[test_mask], "yhat": yhat[test_mask]}

    src_sc_train.data = {"obs": run["y_train"], "pred": run["yhat_train"]}
    src_sc_test.data = {"obs": run["y_test"], "pred": run["yhat_test"]}

    # 1:1 lines for scatters
    def _lims(a: np.ndarray, b: np.ndarray, pad: float = 0.2) -> Tuple[float, float]:
        mn = float(np.min([a.min(), b.min()]))
        mx = float(np.max([a.max(), b.max()]))
        span = mx - mn
        return mn - pad * span - 1e-6, mx + pad * span + 1e-6

    tr_lo, tr_hi = _lims(run["y_train"], run["yhat_train"])
    te_lo, te_hi = _lims(run["y_test"], run["yhat_test"])
    src_line_train.data = {"x": [tr_lo, tr_hi], "y": [tr_lo, tr_hi]}
    src_line_test.data = {"x": [te_lo, te_hi], "y": [te_lo, te_hi]}
    sc_tr.x_range.start, sc_tr.x_range.end = tr_lo, tr_hi
    sc_tr.y_range.start, sc_tr.y_range.end = tr_lo, tr_hi
    sc_te.x_range.start, sc_te.x_range.end = te_lo, te_hi
    sc_te.y_range.start, sc_te.y_range.end = te_lo, te_hi

    # Titles with metrics
    sc_tr.title.text = f"(b) Training scatter (R²={run['r2_train']:+.2f}, RMSE={run['rmse_train']:.2f})"
    sc_te.title.text = f"(c) Test scatter (R²={run['r2_test']:+.2f}, RMSE={run['rmse_test']:.2f})"

    # Time-series background shading for blocked split only
    if params.split_method == "Blocked":
        split_year = years[params.n_train] if params.n_train < len(years) else years[-1]
        train_box.left = years[0] - 0.5
        train_box.right = years[params.n_train - 1] + 0.5
        test_box.left = years[params.n_train] - 0.5
        test_box.right = years[-1] + 0.5
        train_box.visible = True
        test_box.visible = True
        split_span.location = split_year - 0.5
        split_span.visible = True

        # In blocked split, line connections are meaningful
        r_pred_train_line.visible = True
        r_pred_test_line.visible = True
    else:
        train_box.visible = False
        test_box.visible = False
        split_span.visible = False

        # In random split, don't connect non-consecutive years
        r_pred_train_line.visible = False
        r_pred_test_line.visible = False

    # Update metrics + coef panels
    metrics_div.text = format_metrics(run, params)
    coefs_div.text = format_coeffs(run)

    # History
    if add_to_history:
        new = {
            "run": [int(state["run_index"])],
            "r2_train": [float(run["r2_train"])],
            "r2_test": [float(run["r2_test"])],
        }
        src_hist.stream(new, rollover=1000)


def on_any_change(attr: str, old: object, new: object) -> None:
    # Any parameter change recomputes current run (does not add to history)
    update_plots(add_to_history=False)


def on_scenario_change(attr: str, old: object, new: object) -> None:
    apply_scenario(str(new))
    update_plots(add_to_history=False)


def on_resample() -> None:
    state["run_index"] = int(state["run_index"]) + 1
    update_plots(add_to_history=True)


def on_reset_history() -> None:
    src_hist.data = dict(run=[], r2_train=[], r2_test=[])


# Wire callbacks
scenario.on_change("value", on_scenario_change)

for w in [
    start_year,
    n_years,
    n_train,
    n_predictors,
    phi_y,
    sigma_y,
    trend_y,
    phi_x,
    sigma_x,
    trend_x,
    split_method,
    detrend_toggle,
    model_type,
    ridge_log10_alpha,
    seed_base,
]:
    w.on_change("value" if hasattr(w, "value") else "active", on_any_change)

btn_resample.on_click(on_resample)
btn_reset_history.on_click(on_reset_history)


# -----------------------------
# Layout
# -----------------------------

controls = column(
    Div(text="<h2 style='margin:0'>Overfitting & spurious skill (interactive)</h2>"),
    scenario,
    Div(text="<b>Time & split</b>"),
    start_year,
    n_years,
    n_train,
    split_method,
    Div(text="<b>Response (y)</b>"),
    phi_y,
    sigma_y,
    trend_y,
    Div(text="<b>Predictors (X)</b>"),
    n_predictors,
    phi_x,
    sigma_x,
    trend_x,
    Div(text="<b>Safeguards</b>"),
    detrend_toggle,
    model_type,
    ridge_log10_alpha,
    Div(text="<b>Resampling</b>"),
    seed_base,
    row(btn_resample, btn_reset_history),
    howto_div,
    metrics_div,
    coefs_div,
    sizing_mode="fixed",
    width=360,
)

plots = column(
    ts,
    row(sc_tr, sc_te, hist),
    sizing_mode="stretch_both",
)

curdoc().add_root(row(controls, plots, sizing_mode="stretch_both"))
curdoc().title = "Overfitting pedagogical app"


# Initial draw
apply_scenario(scenario.value)
update_plots(add_to_history=False)
