# Reef Flat "Bathtub" Model

Two files, both self-contained single-page HTML. No server-side code, no build step, no external libraries.

| File | What it is |
|---|---|
| `reef_bathtub.html` | The interactive model. Sliders for every parameter, live plots. |
| `reef_explainer.html` | A scrollable walk-through that builds the model up one process at a time. |

**Deployment.** The two pages link to each other by bare relative filename (`href="reef_explainer.html"` and `href="reef_bathtub.html"`). Put both in the same folder on the server and the links work with no edits. Upload only one and its cross-link will 404. Filenames are case-sensitive on most servers. If you link in from PowerPoint, use the full `https://` address, not a relative path.

Both pages embed the same physics core (`core.js`) verbatim, so they cannot drift apart. The build asserts this, and the test suite re-checks it by comparing the copy in each file byte for byte.

---

## 1. The idea

A reef flat is a shallow lagoon sitting behind a raised crest. At high tide the ocean pours over the crest and the lagoon is well connected to it. At low tide the crest stands proud of the sea surface, the lagoon is impounded, and whatever lives there is working on a fixed, shallow parcel of water.

The model treats that lagoon as a single well-mixed box: one temperature, one alkalinity, one dissolved carbon concentration, all uniform. Everything interesting comes from the fact that the box is thin. A shallow box has little heat capacity and little water to dilute into, so the same fluxes of heat and carbon that are negligible offshore become large signals here.

That is the whole conceit. It is a bathtub with a sun lamp, a set of chemical reactions on the floor, and a plug that is pulled twice a day.

## 2. State variables

Three prognostic variables, all for the lagoon box:

| Symbol | Meaning | Units |
|---|---|---|
| `T` | temperature | °C |
| `TA` | total alkalinity | µmol kg⁻¹ |
| `DIC` | dissolved inorganic carbon | µmol kg⁻¹ |

Depth `h(t)` is diagnostic, set by the tide and the crest. pH, pCO₂, aragonite saturation Ω, and the individual carbon species are all diagnosed from `TA`, `DIC`, `T` and salinity. They are outputs, never inputs.

## 3. Geometry and exchange

The lagoon floor is the datum. The crest sits `hCrest` above it. Offshore sea level is

```
η(t) = msl + tideAmp · cos( 2π (t − tidePhaseH) / tidePeriodH )
```

The lagoon depth is

```
h(t) = max( hCrest, η(t) )
```

so when the ocean drops below the crest the lagoon does not drain to nothing, it retains a ponded depth `hCrest`. The head above the crest is `head = max(0, η − hCrest)`, and the lagoon is *connected* whenever `head > 0`.

Exchange with the ocean is split into two physically distinct processes:

**(a) Filling.** When the depth is rising, the added volume is ocean water. Over a step,

```
f = Δh⁺ / h_next      X ← X + f (X_ocean − X)      for X = T, TA, DIC
```

Draining removes lagoon water and therefore changes no concentration.

**(b) Crest-driven exchange.** While connected, water is pumped across the crest by waves and the head difference. The rate is shaped like broad-crested weir discharge, proportional to head^3/2, normalised so it reaches `kMax` at a reference head of 0.5 m:

```
k(t) = kMax · min( 1, (head / 0.5)^1.5 )
```

and each tracer relaxes exponentially towards its ocean value at that rate. At the default `kMax = 1.5 h⁻¹` the residence time at full head is about **40 minutes**. That number matters: it is what makes the lagoon's chemistry a *local* problem for only part of the day.

At the default settings the lagoon is impounded (disconnected) about **26% of the time**.

## 4. Light

Insolation is a half sine over the daylight window, centred on local noon, exactly zero at night:

```
I(t) = Ipeak · sin( π (t − sunrise) / dayLenH ),   sunrise = 12 − dayLenH/2
```

Light reaching the benthos is attenuated through the water column:

```
I_bed = I · exp( −Kd · h )
```

and the photosynthetic response saturates:

```
L = tanh( I_bed / Ik )
```

The `exp(−Kd·h)` term is the coupling that makes the tide matter for chemistry as well as for flushing: deep water at midday means a dimmer, cooler benthos.

## 5. Metabolism

Gross primary production, respiration and net community production:

```
GPP  = Pmax · L
Resp = Rbase · Q10^((T − 25)/10)
NCP  = GPP − Resp                    (positive = net autotrophy)
```

Respiration runs day and night and speeds up as the water warms, which is why the model can warm itself into a more heterotrophic state.

Calcification is deliberately split into gross precipitation and gross dissolution so the two can be reasoned about separately:

```
Ω-dependence:  ω = clamp( (Ω − 1) / 2 , 0 , 1.25 )
precipitation: G_gross = Gmax · (0.30 + 0.70·L) · ω
dissolution:   D_gross = Diss                       (constant, day and night)
net:           G       = G_gross − D_gross
```

Three assumptions are packed in here, all standard and all adjustable:

- **Light enhancement.** Dark calcification is 30% of the light value, consistent with the classic ~3× light enhancement factor.
- **Saturation dependence.** Precipitation is linear in Ω, zero at Ω = 1, and equal to `Gmax` at Ω = 3. The cap at 1.25 stops the curve running away at high Ω.
- **Dissolution is constant.** It represents sediment and framework dissolution that continues regardless of light. This is the term that makes the reef lose carbonate at night.

At the default settings the reef **builds**: net calcification is about **98 mmol CaCO₃ m⁻² d⁻¹** (218 precipitated, 120 dissolved). Net community production is about **38 mmol C m⁻² d⁻¹**.

## 6. Effect on the water

Areal fluxes are converted to concentration tendencies by dividing through the mass of the water column, which is where the shallowness bites:

```
conv = 10³ / (ρ · h)                 ρ = 1025 kg m⁻³

d(DIC)/dt = ( −NCP − G ) · conv
d(TA)/dt  = ( −2G ) · conv
```

Two things to notice, and they are the crux of the model:

- Photosynthesis and respiration move **DIC only**. Carbon is taken up or released, but no charge changes.
- Calcification moves **DIC by one and TA by two**, because removing one CO₃²⁻ ion removes two units of charge.

That two-to-one difference is what lets the two processes be told apart from a water sample, and it is why the explainer's TA–DIC plane works as a diagnostic.

## 7. Heat

```
Q_net = absorb · ( I − Ī ) − λ ( T − T_ocean )
dT/dt = Q_net / ( ρ c_p h )                       c_p = 3990 J kg⁻¹ K⁻¹
```

The solar term is written as an anomaly about its own daily mean `Ī`, and the loss term is a linear restoring flux. Written this way, a well-flushed lagoon sits at the ocean temperature by construction, and the model produces a temperature *range* driven by the diurnal cycle rather than a spurious mean offset. The `1/h` puts the whole heating anomaly into a thin layer at low tide.

At the default settings the lagoon swings over about **3.9 °C** (25.4 to 29.3 °C) against a 27 °C ocean.

## 8. Air–sea CO₂ exchange

```
k_gas = gasVel / 24                              m h⁻¹
F     = − k_gas ( [CO₂] − [CO₂]_eq ) / h         positive = uptake into the water
[CO₂]_eq = K₀ · pCO₂_air
```

This is switchable. It is worth switching off once, because the result is instructive: at the default gas transfer velocity of 3 m d⁻¹ an excess of dissolved CO₂ in a one-metre pond decays with an e-folding time of about **4 days**, while tidal flushing replaces the whole lagoon in **40 minutes**. Turning gas exchange off in the default run changes the mean DIC by 0.13 µmol kg⁻¹, which is nothing. On a reef flat, the atmosphere is a bystander. It sets the ocean's carbon content over decades, but it does not referee the daily cycle.

## 9. Carbonate chemistry

Given `TA`, `DIC`, `T` and `S`, the model solves for [H⁺] and then diagnoses everything else. The alkalinity expression includes carbonate, borate and water:

```
TA = [HCO₃⁻] + 2[CO₃²⁻] + [B(OH)₄⁻] + [OH⁻] − [H⁺]
```

Phosphate, silicate, sulfate and fluoride contributions are neglected. For open reef water that is under 2 µmol kg⁻¹ on TA.

Aragonite saturation is

```
Ω_ar = [Ca²⁺][CO₃²⁻] / K*sp,ar
```

Calcium is essentially constant at fixed salinity, so at a given temperature and salinity Ω is simply proportional to carbonate. At 27 °C and S = 35 the constant is 62.4, meaning Ω = 1 needs 62 µmol kg⁻¹ of carbonate and Ω = 3.5 needs 219.

**Equilibrium constants**, all on the total pH scale:

| Constant | Source |
|---|---|
| K₁, K₂ | Lueker, Dickson & Keeling (2000), Mehrbach refit |
| K_B | Dickson (1990) |
| K_w | Millero (1995) / DOE handbook |
| K₀ | Weiss (1974) |
| K*sp,ar | Mucci (1983) |
| B_T | Lee et al. (2010) |
| Ca_T | Riley & Tongudai (1967) |

**Solver.** Bisection on pH over the range 2 to 12, 60 iterations, using the geometric mean of the bracket at each step so that bisection in [H⁺] is bisection in pH. Bisection is used rather than Newton–Raphson because it cannot diverge and needs no derivative. Sixty iterations is exact to about 1 part in 10¹⁶, which is to say exact.

## 10. Numerics

Operator splitting per step:

1. Explicit Euler on the source terms (metabolism, calcification, gas exchange, heat).
2. Filling with ocean water, applied as a mixing fraction.
3. Crest exchange and heat loss applied **exactly**, as `exp(−k Δt)`.

Applying the linear relaxation terms exactly rather than by forward Euler makes the scheme unconditionally stable in `k` and `λ`. This matters, because `k` can reach 5 h⁻¹ and forward Euler would blow up at any sensible time step. The default 5-minute step is close to converged: against a 1-minute step it misses the daily temperature maximum by 0.01 °C and the pH minimum by 0.002. A 60-minute step is still stable but clips the peaks, losing 0.2 °C and 0.03 pH units.

The run discards the first `days − showDays` of output as spin-up. The default is a 6-day run displaying the last 3.

## 11. Parameters and defaults

**Geometry and tide**

| Parameter | Default | Range | Units |
|---|---|---|---|
| Reef crest height `hCrest` | 0.5 | 0.1 – 2 | m |
| Hour of high tide `tidePhaseH` | 06:00 | 0 – 24 | h |
| Tidal period `tidePeriodH` | 12.42 | 12 – 24.84 | h |
| Mean sea level `msl` | 1.1 | 0.2 – 3 | m |
| Tidal amplitude `tideAmp` | 0.85 | 0 – 1.5 | m |
| Max exchange rate `kMax` | 1.5 | 0 – 5 | h⁻¹ |

**Ocean and atmosphere**

| Parameter | Default | Range | Units |
|---|---|---|---|
| Ocean temperature | 27 | 18 – 34 | °C |
| Ocean DIC | 1980 | 1850 – 2150 | µmol kg⁻¹ |
| Ocean alkalinity | 2300 | 2150 – 2450 | µmol kg⁻¹ |
| Atmospheric pCO₂ | 425 | 280 – 1100 | µatm |
| Salinity | 35 | 30 – 38 | |

**Sun**

| Parameter | Default | Range | Units |
|---|---|---|---|
| Peak insolation `Ipeak` | 900 | 0 – 1200 | W m⁻² |
| Day length `dayLenH` | 12 | 8 – 16 | h |

**Reef metabolism**

| Parameter | Default | Range | Units |
|---|---|---|---|
| Max gross photosynthesis `Pmax` | 34 | 0 – 80 | mmol m⁻² h⁻¹ |
| Respiration at 25 °C `Rbase` | 12 | 0 – 40 | mmol m⁻² h⁻¹ |
| Max gross calcification `Gmax` | 12 | 0 – 30 | mmol m⁻² h⁻¹ |
| Dissolution `Diss` | 5 | 0 – 15 | mmol m⁻² h⁻¹ |
| Saturating irradiance `Ik` | 150 | 20 – 800 | W m⁻² |
| Light attenuation `Kd` | 0.2 | 0 – 1.5 | m⁻¹ |
| Respiration `Q10` | 2 | 1 – 3 | |

**Heat and gas**

| Parameter | Default | Range | Units |
|---|---|---|---|
| Heat-loss sensitivity `λ` | 40 | 5 – 90 | W m⁻² K⁻¹ |
| Shortwave absorbed `absorb` | 0.9 | 0.3 – 1 | |
| Gas transfer velocity `gasVel` | 3 | 0 – 12 | m d⁻¹ |

**Switches**: calcification on/off, calcification responds to Ω on/off, alkalinity may change on/off, air–sea CO₂ exchange on/off. Each of these exists so a process can be removed and the difference watched.

## 12. What the default run does

Ocean end-member at 27 °C, TA 2300, DIC 1980: pH 8.04, Ω_ar 3.59, pCO₂ 396 µatm, and 224 µmol kg⁻¹ of carbonate.

Over the last three days of the default run the lagoon ranges:

| | min | max | range |
|---|---|---|---|
| Depth | 0.50 | 1.95 | 1.45 m |
| Temperature | 25.4 | 29.3 | 3.9 °C |
| pH | 7.91 | 8.15 | 0.24 |
| Ω_ar | 2.67 | 4.20 | 1.52 |
| pCO₂ | 271 | 588 | 317 µatm |
| DIC | 1762 | 2088 | 327 µmol kg⁻¹ |
| TA | 2146 | 2319 | 172 µmol kg⁻¹ |

Two of these deserve comment. The pH swing of 0.24 units in a single day is roughly twice the total change the open ocean has undergone since the industrial revolution: reef organisms already live in a highly variable chemical environment, which cuts both ways in arguments about their sensitivity to acidification. And Ω sits below the ~3.5 that Hoegh-Guldberg et al. (2007) associate with healthy reef growth for 25% of the time, bottoming out at 2.67, under a present-day atmosphere and an ocean that is not yet especially acidified.

## 13. What the model is not

Worth being explicit, because the model is simple enough to over-read:

- **One box, no space.** There is no along-flat gradient, no upstream depletion, no residence-time distribution. Real reef flats show all three, and the water at the back of a flat is chemically very different from the water at the crest.
- **Prescribed metabolism, no ecology.** `Pmax`, `Gmax` and `Diss` are fixed numbers. Nothing grows, dies, bleaches, or acclimates. The model can tell you what a *given* community does to the water, not how the community responds over seasons or years.
- **Calcification's Ω-dependence is a straight line.** It is a defensible caricature of a relationship that is noisy in mesocosms and contested in the field. Treat the Ω sensitivity as illustrative.
- **No nutrients, no organic alkalinity, no sediment porewater.** All three matter on real flats.
- **Heat loss is a single linear coefficient.** It stands in for longwave, latent and sensible fluxes lumped together, and it is the parameter that most needs tuning against a real site.

The model is built to make mechanisms visible, not to hindcast a particular reef. If you want the second thing, the honest route is to keep this structure and fit `λ`, `kMax`, `Pmax`, `Gmax` and `Diss` to a season of logger data from the site in question.

## 14. Testing

The model ships with two browser test suites, run under headless Chromium:

- The app suite checks health, control behaviour, plot rendering, URL state and layout.
- The explainer suite runs 105 checks. About 30 of them assert that **every number quoted in the prose matches the run displayed beside it**, so the text cannot drift away from the physics when either is edited. The rest cover core-verbatim equality with the app, every scene rendering, the interactive sliders, scroll behaviour and narrow-screen layout.

## 15. References

Dickson, A. G. (1990). Thermodynamics of the dissociation of boric acid in synthetic seawater. *Deep-Sea Research*, 37, 755–766.

Hoegh-Guldberg, O. et al. (2007). Coral reefs under rapid climate change and ocean acidification. *Science*, 318, 1737–1742.

Lee, K. et al. (2010). The universal ratio of boron to chlorinity for the North Pacific and North Atlantic oceans. *Geochimica et Cosmochimica Acta*, 74, 1801–1811.

Lueker, T. J., Dickson, A. G. & Keeling, C. D. (2000). Ocean pCO₂ calculated from DIC, TA, and equations for K₁ and K₂. *Marine Chemistry*, 70, 105–119.

Millero, F. J. (1995). Thermodynamics of the carbon dioxide system in the oceans. *Geochimica et Cosmochimica Acta*, 59, 661–677.

Mucci, A. (1983). The solubility of calcite and aragonite in seawater at various salinities, temperatures, and one atmosphere total pressure. *American Journal of Science*, 283, 780–799.

Riley, J. P. & Tongudai, M. (1967). The major cation/chlorinity ratios in sea water. *Chemical Geology*, 2, 263–269.

Weiss, R. F. (1974). Carbon dioxide in water and seawater: the solubility of a non-ideal gas. *Marine Chemistry*, 2, 203–215.
