# Overfitting & spurious skill — step-by-step app (Bokeh)

This is a small pedagogical **Bokeh server** app (honours+) that demonstrates:

1) **Overfitting**: training fit is not predictive skill  
2) **Time-series validation**: blocked vs random splits (leakage under persistence)  
3) **Spurious relationships** driven by persistence and shared trends

## Files
- `overfitting_pedagogical_app_steps.py` — stepwise app laid out **top-to-bottom** (Step 1 → Step 2 → Step 3)

## Run locally
```bash
pip install bokeh numpy
bokeh serve --show overfitting_pedagogical_app_steps.py
```

## How to use (quick demo)
### Scenarios (top)
The three scenario buttons populate **Step 1 (y)** and **Step 2 (X)**. If you change any y/X generation setting, the app switches to **Custom**.

### Step 1 — Generate y(t)
- Increase **ϕᵧ** to add persistence.
- Add **trend** to introduce non-stationarity.

### Step 2 — Generate X(t)
- Increase **p** to increase the chance of “good looking” predictors.
- The highlighted predictor is bold; others are faint.
- The scatter plot shows **y vs the highlighted predictor** (with correlation r).

### Step 3 — Model + evaluate
- Choose the **train/test balance** (training years slider shows both Train and Test counts).
- Compare **Blocked** vs **Random** splits when ϕᵧ is high (leakage effect).
- Toggle **Detrend** in the shared-trend scenario.
- Click **Resample** repeatedly; optionally turn on **Show resampling history**.
