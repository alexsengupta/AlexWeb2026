# Overfitting pedagogical app (Bokeh)

This is a small interactive teaching app based on the logic of `fig3_overfitting.py`.

It is designed to keep the focus on three concepts:

1. **Overfitting:** high training R² can coexist with poor/negative test R².
2. **Time-series validation:** blocked (hindcast) splits are safer than random splits when autocorrelation is present.
3. **Spurious skill from trends:** shared trends can create misleading relationships; detrending reduces this.

## Files

- `overfitting_pedagogical_app.py` — the Bokeh server app.

## How to run locally

From the directory containing `overfitting_pedagogical_app.py`:

```bash
pip install bokeh numpy scikit-learn
bokeh serve --show overfitting_pedagogical_app.py
```

## Teaching suggestions

- Start with the **“Overfitting under the null”** scenario.
- Increase the number of predictors **p** while keeping **n_train** fixed.
- Click **Resample** a few times and watch the history cloud build up.
- Switch **Split** to **Random** for high ϕᵧ to illustrate leakage.
- Use the **Shared trend trap** scenario, then turn on **Detrend**.
