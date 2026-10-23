# Web app inventory and facelift tracker

Each app is reviewed for: **(1) correctness** (does the code do what it claims), **(2) efficiency**, **(3) help and explanation**, then **(4) visuals and tablet/phone layout**.
A rebuilt app goes into `apps/<name>/index.html`. It becomes the "master" version once checked, and the old page is only re-linked to it after you sign off. At that point the old folder moves to `old_apps/`.

Status key: ⬜ not started · 🔍 reviewed · 🛠️ rebuilt, awaiting your check · ✅ signed off and linked from the site

_Last updated: 23 Oct 2026 (4 of ~40 apps done)_

## Progress

| # | App | Current location | Status | New location | Notes |
|---|-----|------------------|--------|--------------|-------|
| 1 | Fish flocking (boids) | was `simulations/flocking/` (now `old_apps/flocking/`) | ✅ | `apps/flocking/` | Live 18 Oct. Linked from Academic Apps and Vibing; the AI Rabbit Hole page links the old chat transcript in `old_apps/`. |
| 2 | Phantom traffic jams (was Motorway traffic) | was `simulations/traffic_model/` (now `old_apps/traffic_model/`) | ✅ | `apps/traffic/` | Live 18 Oct. Linked from Academic Apps ("Traffic Jam" card) and Vibing (button). |
| 3 | Schelling's town (was Schelling Segregation Model) | was `simulations/schelling_model/` (now `old_apps/schelling_model/`) | ✅ | `apps/schelling/` | Live 20 Oct. Linked from Academic Apps (card). |
| 4 | Why marine heatwaves accelerate (was MHW acceleration explainer) | was `simulations/MHW_acceleration/` (now `old_apps/MHW_acceleration/`, including the unused .nc files) | ✅ | `apps/mhw/` | Live 23 Oct. Linked from Academic Apps (card) and the MHW hub page (`MarineHeatwaves/mhw.html`). |

## Notes for later

- **AI Rabbit Hole page (`AIrabbithole/conceptual_models.html`):** this page features the old flocking app and its AI/user dialogue. The dialogue now lives at `old_apps/flocking/flocking_chat.html`. Both need replacing to match the new `apps/flocking/` app. Alex suggests using the worked example from his MEE paper "Every scientist a modeller" instead. *(noted 20 Oct 2026)*

## Still to do

### Academic Apps page (simulations and explainers)
| App | Current location | Status |
|-----|------------------|--------|
| Coral bleaching simulator | `simulations/coral_lagoon/coral_bleaching_multiyear.html` | ⬜ |
| Reef bathtub model (+ explainer) | `simulations/coral_reef_pH/` | ⬜ |
| Coral reef timeline | `simulations/coral_timeline_webapp/index.html` | ⬜ |
| Ocean SST explorer (seasonality) | `simulations/seasonality/index.html` | ⬜ |
| Synthetic SST generator | `simulations/syntheticSST/web_app/index.html` | ⬜ |
| Stommel basin simulator | `simulations/stommel_model/index.html` | ⬜ |
| Estuary models (2- and 3-layer) | `simulations/estuary/` | ⬜ |
| Wave superposition | `simulations/waves/w7.html` | ⬜ |
| Deriving the Coriolis force | `teaching_content/Deriving_Coriolis_Force.html` | ⬜ |
| Overfitting and spurious skill | `teaching_content/overfitting/overfitting_app.html` | ⬜ |
| Correlation paradox (winds and sea ice) | `simulations/counterintuitive_correlations/correlation_madness.html` | ⬜ |
| Monte Carlo time series (plain / AR1 / block bootstrap) | `simulations/monte_carlo_simulation/` | ⬜ |
| Predator–prey model | `simulations/predator_prey/pred_prey_model.html` | ⬜ |
| Conceptual models (AI Rabbit Hole) | `AIrabbithole/conceptual_models.html` | ⬜ |

### Marine heatwaves
| App | Current location | Status |
|-----|------------------|--------|
| MHW hub page | `MarineHeatwaves/mhw.html` | ⬜ |
| MHW Live global map | `MarineHeatwaves/MHWlive/index.html` | ⬜ |
| MHW paper browser (all) | `MarineHeatwaves/all_mhw.html` | ⬜ |
| Polar MHW paper browser | `MarineHeatwaves/polar.html` | ⬜ |
| Subsurface MHW paper browser | `MarineHeatwaves/subsurface.html` | ⬜ |

### Homepage tools and other pages
| App | Current location | Status |
|-----|------------------|--------|
| Climate indices dashboard | `climate indices/index.html` | ⬜ |
| AI Brief (homepage pop-up + archive) | `index.html` + `ai_brief/` | ⬜ |
| AI scaling / model growth | `AI_model_growth/index.html` | ⬜ |
| Carbonator (original) | `Carbonator.html` | ⬜ |
| Publications paper browser | `publications/publications.html` | ⬜ |
| Teaching portfolio | `teaching/teaching_portfolio.html` | ⬜ |
| BEES course map | `teaching/bees_course_maps/course_map.html` | ⬜ |
| Research group honeycomb | `students/research_group_honeycomb.html` | ⬜ |
| Scientific schematics gallery | `schematics/index.html` | ⬜ |
| Seminars | `seminars/index.html` | ⬜ |
| AI Slop | `AI_SLOP/index.html` | ⬜ |
| AI Rabbit Hole hub | `AIrabbithole/index.html` | ⬜ |
| Fractal explorer | `vibe/fractal/mandelbrot.html` | ⬜ |
| Family tree builder | `vibe/family_tree/FamilyTreeBuilder.html` | ⬜ |

### Not linked from anywhere (decide: keep, link or retire)
| App | Location | Note |
|-----|----------|------|
| Barotropic instability explorer | `simulations/instability/index.html` | Looks finished; may just need a link |
| Predator–prey with delay (3 versions) | `simulations/predator_prey2/` | Possibly a better successor to the linked predator–prey app |
| SSP Carbonator local builds (v2–v13) | `simulations/carbonator2_0/` | Probably superseded by the hosted Carbonator 2 |
| Old subsurface MHW browser | `MarineHeatwaves/index.html` | Replaced by `subsurface.html` |
| Draft wave versions and chat transcript | `simulations/waves/` | Development history |

---

## Review notes

### 1. Fish flocking: `apps/flocking/index.html`

**Correctness: problems in the old version, all fixed in the new one**
- **Edge wrap-around was only half done.** Fish wrapped at the edges, but their neighbour search did not look across the edge, so schools split apart at the boundary. Neighbour distances now wrap around too.
- **Separation didn't match its write-up.** The help text said the push grows as 1/d², but the code used 1/d, and the push also braked the fish's forward motion. Revision 2 replaces this with a force form (see below).
- **Fish moved one at a time in the demo.** Later fish reacted to positions that had already been updated, and the "move" step applied twice the force displayed. All fish now compute their steering from the same snapshot, then move together. A test confirms the result no longer depends on fish order.
- **Fear was weaker than claimed.** The help said fear overrides flocking, but in practice the maximum reduction in flocking forces was about 12%. Fear now scales flocking down by (1 − 0.8u), adds an escape force (now up to 3× the normal maximum after revision 2), and allows a short speed burst. Here u is an alarm level that rises from 0 to 1 as the threat gets closer.
- **Predators switched targets every frame.** They now keep a target for 45 steps and pause briefly after a catch.
- **Sliders that did nothing.** Changing the fish or predator count used to have no effect until reset. It now applies live.
- **Other fixes:**
  - Fast-forward no longer keeps running after you exit the demo.
  - The back link now goes to Academic Apps (it pointed at the old Playground redirect).
  - The reference is corrected to Reynolds (1987); the old page said 1986.

**Efficiency**
- **Neighbour search:** was an all-pairs check, which grows with the square of the fish count. It is now a uniform grid, which is close to linear.
- **Trails:** were drawn as about 15,000 separate line segments per frame. They are now a single fade over the canvas.
- **Screen sharpness:** the canvas now uses the full resolution of high-DPI (Retina) screens.
- **Measured speed:** 400 fish plus 3 predators at 6× speed holds 60 fps in headless Chromium. One model step takes 0.06 ms at 120 fish and 0.37 ms at 400 fish.

**Help and explanation**
- **New 9-step guided tour.** It uses a hand-placed group of fish and the same `steer()` function as the simulation, so the arrows show exactly what the model computes. You can drag any fish and the arrows update live. The weight sliders also update the tour arrows. The steps show:
  - neighbours inside the perception radius
  - each of the three rules in turn
  - the weighted forces added tip to tail
  - the capped turn
  - why every fish must update together
- **"About the model" panel** covers:
  - the full equations
  - the time-step order
  - how predators and startles work
  - polarisation, with the random-headings baseline of about 0.08 for 120 fish
  - what the model leaves out (blind spot, 3D, walls, noise, identical individuals; zone models of Couzin 2002)
  - four references
- **Five "Experiments to try".** Their claims were checked by running the model headless (mean polarisation over the last 1,000 of 3,000 steps):

  | Setting | Polarisation |
  |---|---|
  | Default | 0.95 |
  | No alignment | 0.10 |
  | Loners (no alignment or cohesion) | 0.12 |
  | Perception 2 BL | 0.76, in about 50 small groups |
  | No separation | Fish pile on top of each other (nearest neighbour at 0) |

  Predators catch roughly one fish every 250 steps. Cohesion made little difference to the catch rate. The predator experiment says so plainly and points to the confusion effect, which this model leaves out.

**Visuals and devices**
- **Layout:** the tank fills the screen and the control panel can be hidden on desktop. On tablets and phones the controls stack below the tank and the tour card sits under the tank.
- **Colours:** dark (deep water) and light (lagoon) themes, with fish-shaped markers. The force arrows use a colour-blind-checked palette (vermillion / blue / green) and carry text labels, so colour isn't the only cue.
- **New features:**
  - live polarisation plot
  - optional colour-by-heading
  - spotlight one fish to see its forces live
  - click or tap the water to startle the fish
  - presets
  - keyboard shortcuts: space to play/pause, arrow keys to step and to move through the tour
- **Accessibility:** respects reduced-motion settings (starts paused).
- **Checked at:** 1440×900, 820×1180 (iPad) and 390×844 (phone), with no horizontal scrolling.

**Revision 2 (18 Oct): changes from your feedback**
- **Start / Pause / Reset.** The page opens paused, with an arrow on every fish showing its starting heading. Pausing later shows the same arrows, fainter. The button reads Start, then Pause, then Resume. Reset gives new random positions and waits for Start. A step button sits beside it.
- **Dragging in the tour was broken.** A transparent drawing layer sat on top of the fish and swallowed every click. That layer now ignores clicks, which also fixes "tap the water to startle". The cursor changes to a hand over draggable fish.
- **Tour order.** It now starts with both circles (perception radius and personal space) together.
- **Force formulation changed (the model change you asked about).** Previously each rule used Reynolds' "desired velocity minus current velocity, capped" form. That made the separation arrow point partly backwards, and most arrows the same length (the cap). Now:
  - **Separation** points directly away from each intruder, scaled from 0 at the edge of personal space to 1 at contact.
  - **Alignment** = (neighbours' average velocity − own velocity) / cruise speed.
  - **Cohesion** = offset to the neighbours' centre / R.
  - The weighted sum is multiplied by a gain (0.06), then capped at 0.1 per step (inertia), plus a gentle return to cruising speed.
  - Re-tested over 3 seeds × 3,000 steps (mean polarisation / number of groups): default 0.99 / 2; no alignment 0.11 / 18; tight school 1.00 / 1; loners 0.09 / 50.
  - The About text and slider hints describe this form.
- **Weights kept, but explained.** Force sizes come from the geometry at each step; the weights are fixed traits (how much each fish cares about each rule). The tour shows the raw forces first, then applies the weights at the "overall push" step.
- **Presets** now reset the fish and wait for Start. Each has a description: it appears on hover, and below the buttons after you click one.
- **Predator experiment re-measured.** In this model, schooling fish are caught about twice as often as loners (20 vs 8.5 catches per 6,000 steps, over 6 runs). The experiment text now says so, and explains what the model leaves out.

**Before linking it from the site**
- Have a play with the tour and experiments and send me any changes.
- Done 18 Oct: Academic Apps and Vibing now point to `apps/flocking/`, and the old folder has moved to `old_apps/flocking/`.

### 2. Traffic: review of the old `simulations/traffic_model/motorway_traffic.html`

**Correctness**
- **"Detailed rules" pop-up opens on load.** Its CSS sets `display: none` and then `display: flex` in the same rule, so the pop-up covers the page as soon as it loads.
- **Help text doesn't match the code:**
  - The braking term is described as "exponentially stronger", but it actually goes as (desired gap / actual gap)².
  - The "Deceleration" slider is described as maximum braking, but it actually scales that braking term.
- **The car-following rule is a cut-down version of the Intelligent Driver Model (IDM).** It leaves out the closing-speed term, so cars can't anticipate a fast approach to a slower car.
- **Lane changes are unsafe:**
  - The gap check compares centre-to-centre distance against a gap that can be smaller than a car length, so cars can overlap.
  - During the 20-frame lane change, cars in the target lane can't see the merging car.
  - Two cars can merge into the same space from either side.
- **Start-up:** cars start at random positions with no minimum spacing, at zero speed.
- **Number of cars** can't be changed while the simulation is running.
- **Back link** goes to the old Playground redirect.

**Efficiency**
- Every car searches all other cars to find the car ahead (and several more times for lane changes), with physics running at 120 Hz. Sorting each lane once per step would be much cheaper.
- The canvas ignores high-resolution screens.

**Explanation**
- The rules are described, but nothing explains *why* jams appear without a cause, which is the whole point of the app.
- There are no measurements: average speed, traffic flow or stopped cars.
- There is no way to deliberately create a disturbance.

**Visuals and devices**
- Cars get random colours, so jams are hard to spot. Colouring by speed, plus brake lights, would make the backward-moving wave obvious.
- The control panel and the rules box sit on top of the road, and there is no tablet or phone layout.

### 2b. Rebuild: `apps/traffic/index.html`

**Model**
- **Car-following:** the Intelligent Driver Model (Treiber et al. 2000). Cars reach 2 m/s², lorries 1 m/s², with comfortable braking of 1.5 m/s² and a 2 m minimum gap. Vehicles are 4.5 m (cars) or 12 m (lorries).
- **Reaction time:** drivers use the gap and speeds as they were one reaction time ago.
- **Wobble:** an Ornstein–Uhlenbeck random acceleration with a 2 s memory.
- **Emergency braking:** applied based on the current situation, so cars never collide.
- **Lane changes:** MOBIL (Kesting et al. 2007), with a politeness setting.
- **Smooth driver:** a simplified version of the Stern et al. (2018) controller. It aims for its own average speed over the last 38 s, creeps faster only when the gap ahead is large, and blends towards the leader's speed when the gap gets small.
- **Update order:** all drivers decide from one snapshot, then all move together.
- **Speed:** each lane is kept sorted, so neighbour lookups are cheap; 150 vehicles at 6× speed holds 60 fps.

**Tested in Node** (ring of 230 m, 22 cars, reaction time 0.5 s unless stated):

| Test | Result |
|---|---|
| Perfect start, no wobble | Stays steady until a car brakes, then a jam forms |
| Reaction time 0–0.3 s | The disturbance fades |
| Reaction time 0.4 s or more | Jams form |
| Wobble 0.2 | First stopped car after 12–17 s (8 runs) |
| 14 cars | No jams |
| 12 / 14 / 16 / 18 / 22 / 26 cars | Flow 1,690 / 1,770 / 1,760 / 1,040 / 940 / 620 per hour |
| Time gap 2 s | No jams, but slower: flow 680 vs 1,057 per hour |
| Smooth driver, no wobble | Dissolves the jam within about 3 minutes |
| Smooth driver, wobble 0.15–0.3 | Share of cars stopped roughly halves (about 30% to 15%) |
| Motorway, 600 m × 3 lanes, 10% lorries | Flow peaks at about 2,070 per hour per lane at 30 vehicles per km per lane; falls to about 1,400 at 60 |

**Interface**
- **Two road modes:** the ring experiment and the motorway.
- **Car colours:** cars are coloured by speed, from red (stopped) through orange and yellow to light blue (free flow). The colours change in lightness as well as hue, so they work for colour-blind viewers.
- **Brake lights** show when a driver is braking hard.
- **Braking a car:** click any car, or use the button, to make it brake. That car is then highlighted in white, including in the space–time diagram.
- **Space–time diagram:** shows the last 3 minutes. On the motorway it plots the middle lane only, to stay readable.
- **Live numbers:** average speed, cars stopped, flow and time.
- **Presets:** each one resets the road.
- **Controls:** Start, Pause, a 1-second step, and Reset back to even spacing.
- **"Things to try":** the experiments quote the test numbers above.
- **8-step guided story:** it runs the real simulation.
- **About panel:** the equations, the smooth-driver controller, a flow table, limitations and 5 references.
- **Themes and layouts:** dark and light themes; checked at desktop, iPad and phone sizes.

**Revision 2 (18 Oct): changes from your feedback**
- **Motorway drawn as a long loop.** It's now a "stadium" shape (two straights joined by half-circles) that fills the screen, and stands upright on phones. Lanes are drawn about 1.4× real width.
  - On desktop, vehicles are about 1.7× larger than before (cars about 20 px long), and about 1.6× larger on phones.
  - The ring experiment stays circular, and is also larger, because the diagram no longer takes up its own space.
  - The model itself is unchanged (still 600 m), so all the test numbers still hold.
- **Space–time diagram is collapsible.** It's now a bar along the bottom of the road. Clicking the bar (or the switch in Display) slides it up over the bottom of the road. It records even while collapsed, so its history is there when you open it. It starts collapsed, and the guided story opens it at step 2.
- **New "Rules and parameters" window, for advanced users.** It lists all 10 rules: what each does, the equation, the fixed values, and the live value of the slider that controls it. Each control name jumps to its slider and highlights it. You can open it from the last story step, the About panel, and the Things to try section.

**Revision 3 (18 Oct): standout cars and brake lights**
- **The car you braked** is now white, with a dark outline, a pulsing ring and a "braking car" label for the first 8 seconds. Its line in the space–time diagram is also white.
- **The smooth driver** is now a purple car (a colour not used in the speed scale), with a purple halo. Its line in the diagram is purple, and all text that mentioned "amber" now says "purple".
- **Brake lights** now show as a bright red bar across the back of the car plus a red glow on the road behind it. They now appear from 0.8 m/s² of braking, and get stronger the harder the braking. The legend has a key for all three.

**Revision 4 (18 Oct): live.** The braked car's behaviour is now explained: it brakes at 4 m/s² for 2 s, then drives normally and stays white only so you can follow it. This appears in the label on the car, the legend, the story, the About panel and the Rules table. Academic Apps and Vibing now link to `apps/traffic/`, and the old folder has moved to `old_apps/traffic_model/`.

### 3. Schelling: review of the old app, and the rebuild in `apps/schelling/index.html`

**Old app: what was wrong**
- **Radius 1 used only 4 neighbours, not 8.** The cut-off was circular, so the diagonals (at distance 1.41) were excluded, even though the help text said radius 1 meant the 8 surrounding cells.
- **"Tolerance" worked backwards.** The slider was the minimum share of similar neighbours, so a higher value meant *less* tolerant.
- **Any slider change re-randomised the town.**
- **Random moves ignored the destination**, and agents were not re-checked before moving.
- **Slow:** every mover rescanned the whole grid for empty cells.
- **Group counts never changed**, so that display was useless, and the "1 group" option was meaningless.

**Rebuild**
- **The town:** a 40 × 40 grid of homes in blocks of 5 separated by streets. Each household is a little house in its group's colour. Moves are animated: the house fades in at its new home, and a ghost fades out at the old one. Unhappy households carry a white badge, and there's a key.
- **Headline:** "wanted 30% → got 74%", updated live.
- **Live numbers:** the share who want to move, the share with no other-colour neighbours, moves last round, and households that are unhappy but stuck.
- **Two charts:**
  - a histogram of how similar each household's neighbourhood is, now versus at the start, with a marker at the threshold;
  - average similarity and the share wanting to move, over time.
- **Inspect:** click any house to see its neighbourhood outlined and why it is happy or not.
- **Fixes and live changes:** 8 neighbours at radius 1 (square neighbourhood); the threshold now changes live; the town wraps at the edges. Unhappy households are re-checked before they move.
- **Presets:** 20%, 30%, 50% and 70%.
- **Guided story (7 steps):** a mixed town; a mild preference, highlighting an unhappy house; moving; the surprise; small changes giving big jumps; what the model does and doesn't show; going further.
- **Advanced options** (folded away and off by default; changing one builds a new town):
  - mixed preferences (an intolerant minority);
  - unequal groups (majority share), or 2–4 colours;
  - diversity seekers (Pancs & Vriend style, with an asymmetry setting);
  - choosy movers (best of N homes);
  - restlessness;
  - moving only nearby;
  - neighbourhood size.
- **About panel:** results tables with the tested numbers, the caveats, and 4 references.
- **Themes and layouts:** dark and light themes; checked at desktop, iPad and phone sizes.

**Tested in Node** (40 × 40, 10% empty, 2 equal groups; several runs averaged)

*Threshold sweep*

| Threshold | Final similarity | No other-colour neighbours |
|---|---|---|
| 20% | 57% | 6% |
| 25% | 57% | 6% |
| 30% | 74% | 26% |
| 50% | 85% | 51% |
| 60% | 97% | 86% |
| 70% | 99% | 96% |

A random town starts at about 50%. The jump between 25% and 30% is the step from needing 2 of 8 neighbours to 3 of 8.

*Advanced options*

| Option | Result |
|---|---|
| Intolerant minority (base threshold 20%; minority needs 75%) | 57% similar with none; 65% with 10% intolerant; 71% with 20% |
| Unequal groups, 80/20, threshold 30% | 79% of the minority unhappy at the start, 54% after 400 rounds of random moves; with choosy movers, 43% of the minority and none of the majority |
| Diversity seekers, ideal 50/50 | No segregation (49%) if being outnumbered feels no worse; 61% if a bit worse; 69% if twice as bad; 77% if much worse |
| Rule: leave if under 30% or over 70% similar | No segregation, with random or choosy moves, so the asymmetry is what matters |
| Restlessness | 2% → 86% (more segregated than 74%); 10% → 74% |
| Local moves | 70%, and slower; with 3% empty homes some households get stuck |

**Schelling revision 2 (20 Oct)**
- **Streets removed.** They had no role in the model and were purely decorative, so the houses are now bigger.
- **Clearer houses.** Each house has a dark outline, and empty plots are clearly lighter than occupied ones.
- **Stronger colours.** Blue #3f9cff, orange #ff9d00, teal #60e0d0 and pink #e8508a on dark (darker versions on light). All four pass the colour-blind separation check; the old green and pink were hard to tell apart.
- **Dark theme is now the default**, regardless of the system setting.
- **Key fixes:** the key no longer overlaps the town when there are 3–4 colours.

## 4. Why marine heatwaves accelerate (`apps/mhw/`)

**Review of the old page**
- **Correctness:** the basic idea (fixed threshold, uniform warming μ) was right. Two issues:
  - Intensity was measured above the threshold, not above climatology. The Hobday et al. (2016) standard is above climatology, so the new page uses that (Alex's choice).
  - MHW days and mean duration were counted differently (days excluded merged gaps; duration included them). Both now use event durations including joined gaps, so days = events × mean duration.
- **Efficiency:** the page carried 335 KB of data, including stored year and day-of-year arrays that can be computed from the index. SST is now stored to 0.01 °C as integers; the whole page is about 135 KB. All metrics are precomputed once per example, so playback only redraws.
- **Guidance:** the old page ran through examples, but nothing told the reader where to look, and the panels all competed for attention.

**What the new page does**
- Four examples (one peak, three peaks, many peaks, real ocean) plus an Explore tab.
- Each example is a short sequence of steps: set-up → warm it → compare with a straight line → other measures → key message.
- "Look at" chips name the panels that matter; the other panels fade. On tablet and phone the focused panels move up to sit directly under the text.
- Playback pauses automatically at key moments with a callout in the text and labels on the charts (e.g. each new peak crossing in example 2, 150 and 300 days a year in the real example).
- "Early rate, continued" dashed line on the MHW-days chart shows the acceleration; "if peaks just rose by μ" line on the intensity chart shows the lag.
- Light theme by default, dark available. Colours: warmed series blue, MHW days red, just-crossed amber, threshold black dashed, climatology grey.
- About panel: method (Hobday rules), data note (OISST v2.1, ~30°N 180°E, 1982 to Sep 2025, own trend of 0.34 °C/decade removed) and references.

**Tested numbers (real series)**

| Warming μ | MHW days/yr | Events/decade | Mean duration (d) | Mean peak intensity (°C) |
|---|---|---|---|---|
| 0 | 23.5 | 16.3 | 14.4 | 1.90 |
| 0.5 | 72.4 | 45.6 | 15.9 | 1.91 |
| 1.0 | 150.4 | 61.1 | 24.6 | 2.09 |
| 1.1 | 166 | 62.3 (max) | 26.7 | 2.16 |
| 1.5 | 234 | 57.7 | 40.6 | 2.40 |
| 2.0 | 300.6 | 36.6 | 82.1 | 2.86 |
| 3.0 | 355.3 | 10.1 | 352.8 | 4.02 |

Toy checks: one peak gives a straight line (about 14 days per 0.1 °C) and intensity = 1.75 + μ; three peaks cross at μ = 0.25 and 0.55, with average duration and intensity dropping at each crossing; many peaks give a smooth acceleration, events rising to about 10 then falling to 1 as everything merges by μ ≈ 1.7.

Tested at 1440×900, 820×1180 and 390×844 in both themes: no script errors, no horizontal scrolling.
