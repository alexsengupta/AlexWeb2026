"""
Core Python logic for generating synthetic SST and diagnostics in Pyodide.

This module mirrors the behaviour of the original Python workflow while
reading SST from a CSV file (columns: time, lat, lon, sst). The main entry
point `generate_synthetic_sst` returns dictionaries that the JavaScript
front-end can consume to render diagnostics and offer CSV downloads.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Dict, Any

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import acf as sm_acf

# Constants tuned for seasonal fitting
P_ANNUAL = 365.2425
H_MEAN = 3
H_LOGVAR = 2
DAYS_PER_YEAR = 365


def design_harmonics(t: np.ndarray, period: float, harmonics: int) -> np.ndarray:
    """Return columns [1, cos, sin] up to the selected harmonic order."""
    t = np.asarray(t, dtype=float)
    omega = 2 * np.pi / period
    columns = [np.ones_like(t)]
    for k in range(1, harmonics + 1):
        columns.append(np.cos(k * omega * t))
        columns.append(np.sin(k * omega * t))
    return np.column_stack(columns)


def simulate_arma11(phi: float, theta: float, n: int, noise_std: float, rng: np.random.Generator) -> np.ndarray:
    """Simulate ARMA(1,1) with innovation variance noise_std^2."""
    e = rng.normal(0.0, noise_std, size=n)
    y = np.empty(n, dtype=float)
    y[0] = e[0]
    for t in range(1, n):
        y[t] = phi * y[t - 1] + e[t] + theta * e[t - 1]
    return y


def simulate_ar1(rho: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Simulate an AR(1) process with stationary initial variance."""
    eta = rng.normal(0.0, 1.0, size=n)
    s = np.empty(n, dtype=float)
    s[0] = eta[0] / np.sqrt(max(1e-12, 1 - rho**2))
    for t in range(1, n):
        s[t] = rho * s[t - 1] + eta[t]
    return s


def _clean_csv(csv_text: str) -> pd.DataFrame:
    """Load and clean the SST CSV."""
    df = pd.read_csv(StringIO(csv_text))
    if "time" not in df or "sst" not in df:
        raise ValueError("CSV must contain at least 'time' and 'sst' columns.")

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time", "sst"]).sort_values("time").reset_index(drop=True)
    # Drop Feb 29 to enforce 365-day climatology.
    mask = ~((df["time"].dt.month == 2) & (df["time"].dt.day == 29))
    df = df.loc[mask].reset_index(drop=True)
    if df.empty:
        raise ValueError("No valid rows after cleaning CSV input.")
    return df


def generate_synthetic_sst(csv_text: str, years_syn: int = 1000, seed: int = 20251029, decimals: int = 2) -> Dict[str, Any]:
    """Compute synthetic SST series and diagnostic metrics from CSV text."""
    years_syn = int(years_syn)
    if years_syn < 1 or years_syn > 10000:
        raise ValueError("years_syn must be between 1 and 10000.")

    df = _clean_csv(csv_text)
    sst = df["sst"].to_numpy(dtype=float)
    dates = df["time"]
    t = np.arange(sst.size, dtype=float)

    doy = np.array(
        [pd.Timestamp(2001, month, day).dayofyear for month, day in zip(dates.dt.month, dates.dt.day)],
        dtype=int,
    )

    Xs = design_harmonics(t, P_ANNUAL, H_MEAN)
    beta, *_ = np.linalg.lstsq(Xs, sst, rcond=None)
    seasonal_mean = Xs @ beta

    anomalies_raw = sst - seasonal_mean
    t_centered = t - t.mean()
    Xt = np.column_stack([np.ones_like(t_centered), t_centered])
    trend_coeffs, *_ = np.linalg.lstsq(Xt, anomalies_raw, rcond=None)
    anomalies = anomalies_raw - Xt @ trend_coeffs

    raw_var = np.full(DAYS_PER_YEAR, np.nan, dtype=float)
    for day in range(1, DAYS_PER_YEAR + 1):
        sample = anomalies[doy == day]
        raw_var[day - 1] = sample.var(ddof=1) if sample.size >= 2 else np.nan
    global_var = np.nanvar(anomalies, ddof=1)
    raw_var = np.where(np.isfinite(raw_var), raw_var, global_var)

    day_grid = np.arange(1, DAYS_PER_YEAR + 1, dtype=float)
    Xv = design_harmonics(day_grid, P_ANNUAL, H_LOGVAR)
    gamma, *_ = np.linalg.lstsq(Xv, np.log(raw_var), rcond=None)
    sigma_day = np.exp(0.5 * (Xv @ gamma))
    sigma_t = sigma_day[doy - 1]

    z = anomalies / sigma_t
    arma_fit = ARIMA(z, order=(1, 0, 1), trend="n").fit(method_kwargs={"warn_convergence": False})
    phi = float(arma_fit.arparams[0])
    theta = float(arma_fit.maparams[0])
    innovation_variance = float(arma_fit.scale)
    std_z = float(z.std(ddof=0))

    rng = np.random.default_rng(seed)

    n_acf = 60
    acf_obs = sm_acf(anomalies, nlags=n_acf, fft=True)
    lags = np.arange(n_acf + 1)
    lag_mask = (lags >= 10) & (lags <= 60)

    y_fast = simulate_arma11(phi, theta, z.size, noise_std=np.sqrt(innovation_variance), rng=rng)
    y_fast_std = y_fast.std(ddof=0)
    if y_fast_std > 0:
        y_fast /= y_fast_std

    def objective(rho: float, frac: float) -> float:
        s_short = simulate_ar1(rho, z.size, rng=rng)
        s_std = s_short.std(ddof=0)
        if s_std > 0:
            s_short /= s_std
        mix = np.sqrt(1 - frac) * y_fast + np.sqrt(frac) * s_short
        mix = mix * std_z * sigma_t
        acf_est = sm_acf(mix, nlags=n_acf, fft=True)
        return float(np.sum((acf_est[lag_mask] - acf_obs[lag_mask]) ** 2))

    best_score = np.inf
    rho_opt, frac_opt = 0.98, 0.3
    for rho in np.arange(0.97, 0.999, 0.003):
        for frac in np.arange(0.05, 0.85, 0.05):
            score = objective(rho, frac)
            if score < best_score:
                best_score, rho_opt, frac_opt = score, rho, frac

    for rho in np.clip(np.arange(rho_opt - 0.003, rho_opt + 0.0031, 0.001), 0.9, 0.9999):
        for frac in np.clip(np.arange(frac_opt - 0.08, frac_opt + 0.081, 0.02), 0.01, 0.99):
            score = objective(rho, frac)
            if score < best_score:
                best_score, rho_opt, frac_opt = score, rho, frac

    n_syn = years_syn * DAYS_PER_YEAR
    yA = simulate_arma11(phi, theta, n_syn, noise_std=np.sqrt(innovation_variance), rng=rng)
    std_yA = yA.std(ddof=0)
    if std_yA > 0:
        yA /= std_yA

    yS = simulate_ar1(rho_opt, n_syn, rng=rng)
    std_yS = yS.std(ddof=0)
    if std_yS > 0:
        yS /= std_yS

    y_mix = np.sqrt(1 - frac_opt) * yA + np.sqrt(frac_opt) * yS
    y_mix *= std_z

    sigma_long = np.tile(sigma_day, years_syn)
    x_syn = y_mix * sigma_long

    harm_1yr = design_harmonics(np.arange(DAYS_PER_YEAR, dtype=float), P_ANNUAL, H_MEAN) @ beta
    sst_syn = np.tile(harm_1yr, years_syn) + x_syn

    # Diagnostics: full observed record of anomalies
    n_obs = sst.size
    dates_obs = dates.dt.strftime("%Y-%m-%d").tolist()
    obs_anom_full = anomalies.tolist()
    syn_anom_full = x_syn[:n_obs].tolist()

    sst_syn_matrix = sst_syn.reshape(years_syn, DAYS_PER_YEAR)
    syn_mean = sst_syn_matrix.mean(axis=0)
    syn_anom = sst_syn_matrix - syn_mean
    var_syn_doy = syn_anom.var(axis=0, ddof=1)
    var_obs_doy = raw_var

    acf_syn_full = sm_acf(syn_anom.ravel(order="C"), nlags=n_acf, fft=True)

    doy_axis = list(range(1, DAYS_PER_YEAR + 1))
    acf_lags = lags.tolist()

    sst_syn_rounded = np.round(sst_syn, decimals=decimals)
    years = np.repeat(np.arange(1, years_syn + 1), DAYS_PER_YEAR)
    doy_long = np.tile(np.arange(1, DAYS_PER_YEAR + 1), years_syn)
    csv_lines = ["year,day_of_year,sst"]
    fmt = f"{{:d}},{{:d}},{{:.{decimals}f}}"
    csv_lines.extend(fmt.format(int(y), int(d), float(val)) for y, d, val in zip(years, doy_long, sst_syn_rounded))
    synthetic_csv = "\n".join(csv_lines)

    result: Dict[str, Any] = {
        "metadata": {
            "phi": round(phi, 6),
            "theta": round(theta, 6),
            "rho": round(float(rho_opt), 6),
            "fraction": round(float(frac_opt), 6),
            "years_syn": years_syn,
            "seed": seed,
        },
        "diagnostics": {
            "timeseries": {
                "dates": dates_obs,
                "observed": obs_anom_full,
                "synthetic": syn_anom_full,
            },
            "variance": {
                "doy": doy_axis,
                "observed": var_obs_doy.tolist(),
                "synthetic": var_syn_doy.tolist(),
            },
            "acf": {
                "lags": acf_lags,
                "observed": acf_obs.tolist(),
                "synthetic": acf_syn_full.tolist(),
            },
        },
        "synthetic_csv": synthetic_csv,
    }
    return result


def generate_synthetic_sst_json(csv_text: str, years_syn: int = 1000, seed: int = 20251029, decimals: int = 2) -> str:
    """Helper to return a JSON string for Pyodide consumption."""
    result = generate_synthetic_sst(csv_text, years_syn=years_syn, seed=seed, decimals=decimals)
    return json.dumps(result)
