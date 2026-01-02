/**
 * EstuaryModel_2layer.js
 * Core physics model for 2-layer 1D estuary with temperature transport
 * Box model with exchange flow driven by sea-level gradients
 */

class EstuaryModel_2layer {
    constructor(numBoxes = 20) {
        this.numBoxes = numBoxes;
        this.boxLength = 2500; // individual box length in meters (default 2.5 km)
        this.updateDomainLength();

        // Physical constants
        this.rho = 1025; // water density (kg/m³)
        this.cp = 4000; // specific heat (J/kg/K)
        this.g = 9.81; // gravity (m/s²)
        this.alpha = 2e-4; // thermal expansion coefficient (1/K)
        this.beta = 7.7e-4; // haline contraction coefficient (1/psu)

        // Layer thickness fractions (fixed for now)
        this.layerFraction = {
            upper: 0.4,  // 40% of total depth
            lower: 0.6   // 60% of total depth
        };

        // State variables (arrays for each box)
        // Two-layer structure: upper (surface) and lower (bottom)
        this.temperature = {
            upper: new Array(numBoxes).fill(15),
            lower: new Array(numBoxes).fill(15)
        };
        this.salinity = {
            upper: new Array(numBoxes).fill(30),
            lower: new Array(numBoxes).fill(30)
        };
        this.eta = new Array(numBoxes).fill(0); // sea level (m)
        this.depth = new Array(numBoxes).fill(10); // total depth (m)
        this.width = new Array(numBoxes).fill(1000); // width (m)

        // Barotropic (depth-averaged) velocity for shallow water
        this.u_barotropic = new Array(numBoxes).fill(0);

        // Layer-specific velocities
        this.velocity = {
            upper: new Array(numBoxes).fill(0),
            lower: new Array(numBoxes).fill(0)
        };

        // Exchange flow magnitude (m³/s)
        this.exchangeFlow = new Array(numBoxes).fill(0);

        // Parameters (set by UI controls)
        this.params = {
            tidalAmplitude: 1.0, // m
            tidalPeriod: 12.42 * 3600, // M2 tide in seconds
            riverDischarge: 30, // m³/s - REDUCED from 100 to balance exchange flow
            diffusivity: 50, // m²/s - Moderate (sharper than old 100, but not too sharp)
            heatFluxAmplitude: 200, // W/m² (diurnal cycle amplitude)
            oceanTemp: 18, // °C
            riverTemp: 12, // °C
            oceanSalinity: 35, // psu
            riverSalinity: 0, // psu
            exchangeCoefficient: 0.01, // C_ex for baroclinic exchange (dimensionless)
            verticalMixing: 1e-6, // w_e - Entrainment velocity (m/s) for vertical mixing
            oceanMixing: 0.5, // Coastal ocean mixing: 0 = pure estuarine, 1 = pure ocean
            frictionCoefficient: 0.0002, // r for linear bottom friction (s^-1)
            boxLength: 2500, // individual box length (m) - controls estuary length
            dt: 200, // time step (seconds) - range 50-300s for stability
            animationSpeed: 1.0, // animation playback speed multiplier (does not affect physics)
            advectionScheme: 'upwind', // 'upwind' or 'tvd'
            taperedGeometry: false
        };

        // Time tracking
        this.time = 0; // seconds
        this.elapsedDays = 0;

        // Exchange coefficient for box model flow
        this.exchangeCoeff = 500; // tuning parameter for Q = C * Δη * w

        // Time series data storage
        this.timeSeries = {
            time: [],                    // elapsed days
            meanTempUpper: [],           // domain-mean upper layer temperature
            meanTempLower: [],           // domain-mean lower layer temperature
            meanSalinityUpper: [],       // domain-mean upper layer salinity
            meanSalinityLower: [],       // domain-mean lower layer salinity
            stratificationTemp: [],      // mean ΔT (lower - upper)
            stratificationSalinity: [],  // mean ΔS (lower - upper)
            heatFlux: [],                // surface heat flux
            expectedWarming: []          // cumulative expected warming from heat flux
        };

        // Initial profiles (t=0 reference)
        this.initialTemperature = {
            upper: null,
            lower: null
        };
        this.initialSalinity = {
            upper: null,
            lower: null
        };

        // Sampling interval for time series (every N seconds)
        this.sampleInterval = 1800; // 30 minutes
        this.lastSampleTime = 0;

        // Initialize geometry
        this.updateGeometry();

        // Initialize temperature and salinity profiles
        this.setInitialProfiles();

        // Store initial profiles
        this.initialTemperature.upper = [...this.temperature.upper];
        this.initialTemperature.lower = [...this.temperature.lower];
        this.initialSalinity.upper = [...this.salinity.upper];
        this.initialSalinity.lower = [...this.salinity.lower];
    }

    /**
     * Update total domain length and dx based on boxLength parameter
     */
    updateDomainLength() {
        this.boxLength = this.params ? this.params.boxLength : 2500;
        this.dx = this.boxLength;
        this.totalLength = this.numBoxes * this.dx;
    }

    /**
     * Set initial temperature and salinity profiles
     * Both T and S use linear ramp between river and ocean values
     * Both layers start with same values (well-mixed vertically)
     */
    setInitialProfiles() {
        for (let i = 0; i < this.numBoxes; i++) {
            const x = i / (this.numBoxes - 1); // 0 at mouth, 1 at head

            // Temperature: linear ramp from ocean to river (both layers equal)
            const temp = this.params.oceanTemp + x * (this.params.riverTemp - this.params.oceanTemp);
            this.temperature.upper[i] = temp;
            this.temperature.lower[i] = temp;

            // Salinity: linear ramp from ocean to river (both layers equal)
            const salinity = this.params.oceanSalinity + x * (this.params.riverSalinity - this.params.oceanSalinity);
            this.salinity.upper[i] = salinity;
            this.salinity.lower[i] = salinity;
        }
    }

    updateGeometry() {
        // Set depth and width profiles based on geometry setting
        if (this.params.taperedGeometry) {
            // Tapered: wider and deeper at mouth, narrower at head
            for (let i = 0; i < this.numBoxes; i++) {
                const x = i / (this.numBoxes - 1); // 0 at mouth, 1 at head
                this.depth[i] = 15 * (1 - 0.6 * x); // 15m → 6m
                this.width[i] = 2000 * (1 - 0.7 * x); // 2000m → 600m
            }
        } else {
            // Uniform geometry
            this.depth.fill(10);
            this.width.fill(1000);
        }
    }

    /**
     * Main update step - advances simulation by dt
     */
    update() {
        const dt = this.params.dt;

        // 1. Update barotropic velocity from shallow water momentum equation
        this.updateBarotropicVelocity(dt);

        // 2. Update sea level from shallow water continuity equation
        this.updateSeaLevel(dt);

        // 3. Add baroclinic component to get layer velocities
        this.updateLayerVelocities();

        // 4. Update temperature (advection + diffusion + heat flux)
        this.updateTemperature(dt);

        // 5. Update salinity (advection + diffusion)
        this.updateSalinity(dt);

        // 6. Apply boundary conditions
        this.applyBoundaryConditions();

        // Update time
        this.time += dt;
        this.elapsedDays = this.time / 86400;

        // Record time series data at intervals
        if (this.time - this.lastSampleTime >= this.sampleInterval) {
            this.recordTimeSeries();
            this.lastSampleTime = this.time;
        }
    }

    /**
     * Record current state to time series
     */
    recordTimeSeries() {
        const diagnostics = this.getDiagnostics();

        this.timeSeries.time.push(this.elapsedDays);
        this.timeSeries.meanTempUpper.push(diagnostics.meanTempUpper);
        this.timeSeries.meanTempLower.push(diagnostics.meanTempLower);
        this.timeSeries.meanSalinityUpper.push(diagnostics.meanSalinityUpper);
        this.timeSeries.meanSalinityLower.push(diagnostics.meanSalinityLower);
        this.timeSeries.stratificationTemp.push(diagnostics.stratificationTemp);
        this.timeSeries.stratificationSalinity.push(diagnostics.stratificationSalinity);
        this.timeSeries.heatFlux.push(diagnostics.currentHeatFlux);

        // Calculate cumulative expected warming from heat flux
        const meanDepth = this.depth.reduce((a, b) => a + b) / this.depth.length;
        const h_upper = this.layerFraction.upper * meanDepth;
        const expectedWarmingRate = diagnostics.currentHeatFlux / (this.rho * this.cp * h_upper);
        const dt = this.sampleInterval;

        const prevExpectedWarming = this.timeSeries.expectedWarming.length > 0 ?
            this.timeSeries.expectedWarming[this.timeSeries.expectedWarming.length - 1] : 0;

        this.timeSeries.expectedWarming.push(prevExpectedWarming + expectedWarmingRate * dt);
    }

    /**
     * Update barotropic velocity using shallow water momentum equation
     * ∂u/∂t = -g·∂η/∂x - r·u
     * Uses BACKWARD difference for stability (avoids computational mode)
     */
    updateBarotropicVelocity(dt) {
        const newU = [...this.u_barotropic];

        // Box 0: Ocean boundary - use FORWARD difference
        // dEta/dx = (eta[1] - eta[0]) / dx where eta[0] is prescribed
        const dEta_dx_0 = (this.eta[1] - this.eta[0]) / this.dx;
        const pressure_gradient_0 = -this.g * dEta_dx_0;
        const friction_0 = -this.params.frictionCoefficient * this.u_barotropic[0];
        newU[0] = this.u_barotropic[0] + (pressure_gradient_0 + friction_0) * dt;

        // Interior points (box 1 to numBoxes-2): use BACKWARD difference for stability
        for (let i = 1; i < this.numBoxes - 1; i++) {
            // Pressure gradient: -g * ∂η/∂x (BACKWARD difference)
            const dEta_dx = (this.eta[i] - this.eta[i-1]) / this.dx;
            const pressure_gradient = -this.g * dEta_dx;

            // Bottom friction: -r * u (linear drag)
            const friction = -this.params.frictionCoefficient * this.u_barotropic[i];

            // Forward Euler time step
            const dudt = pressure_gradient + friction;
            newU[i] = this.u_barotropic[i] + dudt * dt;
        }

        // Boundary condition at river end: river discharge sets the velocity
        // u_river = -Q / (W × H) (negative = seaward flow)
        const river_idx = this.numBoxes - 1;
        const riverArea = this.width[river_idx] * this.depth[river_idx];
        newU[river_idx] = -this.params.riverDischarge / riverArea;

        this.u_barotropic = newU;
    }

    /**
     * Update sea level using shallow water continuity equation
     * ∂η/∂t = -∂(u·H)/∂x
     * Uses FORWARD difference for stability (pairs with backward diff in momentum)
     */
    updateSeaLevel(dt) {
        const newEta = [...this.eta];

        // Boundary condition at ocean: prescribed tidal forcing
        const omega = 2 * Math.PI / this.params.tidalPeriod;
        newEta[0] = this.params.tidalAmplitude * Math.sin(omega * this.time);

        // Interior points: continuity equation
        for (let i = 1; i < this.numBoxes - 1; i++) {
            // Flux divergence: ∂(u·H)/∂x (FORWARD difference for stability)
            // This pairs with backward diff in momentum to avoid computational mode
            const flux_here = this.u_barotropic[i] * this.depth[i];
            const flux_right = this.u_barotropic[i+1] * this.depth[i+1];
            const dFlux_dx = (flux_right - flux_here) / this.dx;

            // Forward Euler time step
            newEta[i] = this.eta[i] - dFlux_dx * dt;
        }

        // Boundary condition at river: zero gradient or slight elevation from river input
        const river_effect = this.params.riverDischarge / (this.width[this.numBoxes-1] * this.depth[this.numBoxes-1] * 100);
        newEta[this.numBoxes - 1] = newEta[this.numBoxes - 2] + river_effect;

        this.eta = newEta;
    }

    /**
     * Calculate layer velocities by adding baroclinic component to barotropic flow
     * Two-layer velocities = barotropic flow ± baroclinic exchange
     */
    updateLayerVelocities() {
        for (let i = 0; i < this.numBoxes; i++) {
            const H = this.depth[i];
            const W = this.width[i];

            // Layer thicknesses
            const h_upper = this.layerFraction.upper * H;
            const h_lower = this.layerFraction.lower * H;

            // BAROCLINIC EXCHANGE FLOW
            // Calculate reduced gravity from density difference between layers
            const deltaT = this.temperature.lower[i] - this.temperature.upper[i];
            const deltaS = this.salinity.lower[i] - this.salinity.upper[i];

            // g' = g[β·ΔS - α·ΔT]
            // Positive g' means lower layer is denser (stable stratification)
            const gPrime = this.g * (this.beta * deltaS - this.alpha * deltaT);

            // Exchange flow magnitude: Q_ex = C_ex · W · H · sqrt(g'·H)
            // Only if stratification is stable (g' > 0)
            let Q_ex = 0;
            if (gPrime > 0) {
                Q_ex = this.params.exchangeCoefficient * W * H * Math.sqrt(gPrime * H);
            }

            // Store exchange flow for diagnostics
            this.exchangeFlow[i] = Q_ex;

            // LAYER VELOCITIES
            // Barotropic flow ± baroclinic exchange
            // Upper layer: seaward (negative) when exchange is active
            // Lower layer: landward (positive) when exchange is active
            const A_upper = W * h_upper;
            const A_lower = W * h_lower;

            this.velocity.upper[i] = this.u_barotropic[i] - Q_ex / A_upper;
            this.velocity.lower[i] = this.u_barotropic[i] + Q_ex / A_lower;
        }
    }

    /**
     * Update temperature field for both layers
     * (advection + diffusion + surface forcing + vertical mixing)
     */
    updateTemperature(dt) {
        const newTempUpper = [...this.temperature.upper];
        const newTempLower = [...this.temperature.lower];

        for (let i = 1; i < this.numBoxes - 1; i++) {
            const H = this.depth[i];
            const h_upper = this.layerFraction.upper * H;
            const h_lower = this.layerFraction.lower * H;

            // === UPPER LAYER ===
            let dTdt_upper = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dTdt_upper += this.advectionUpwind(i, 'upper', 'temperature');
            } else {
                dTdt_upper += this.advectionTVD(i, 'upper', 'temperature');
            }

            // 2. Diffusion
            const diffUpper = this.params.diffusivity *
                (this.temperature.upper[i+1] - 2*this.temperature.upper[i] + this.temperature.upper[i-1]) / (this.dx * this.dx);
            dTdt_upper += diffUpper;

            // 3. Surface heat flux (only to upper layer)
            const heatFlux = this.getSurfaceHeatFlux();
            const heatFluxTerm = heatFlux / (this.rho * this.cp * h_upper);
            dTdt_upper += heatFluxTerm;

            // 4. Vertical mixing (exchange with lower layer)
            const verticalMixing_upper = this.params.verticalMixing *
                (this.temperature.lower[i] - this.temperature.upper[i]) / h_upper;
            dTdt_upper += verticalMixing_upper;

            newTempUpper[i] = this.temperature.upper[i] + dTdt_upper * dt;

            // === LOWER LAYER ===
            let dTdt_lower = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dTdt_lower += this.advectionUpwind(i, 'lower', 'temperature');
            } else {
                dTdt_lower += this.advectionTVD(i, 'lower', 'temperature');
            }

            // 2. Diffusion
            const diffLower = this.params.diffusivity *
                (this.temperature.lower[i+1] - 2*this.temperature.lower[i] + this.temperature.lower[i-1]) / (this.dx * this.dx);
            dTdt_lower += diffLower;

            // 3. Vertical mixing (exchange with upper layer)
            const verticalMixing_lower = this.params.verticalMixing *
                (this.temperature.upper[i] - this.temperature.lower[i]) / h_lower;
            dTdt_lower += verticalMixing_lower;

            newTempLower[i] = this.temperature.lower[i] + dTdt_lower * dt;
        }

        this.temperature.upper = newTempUpper;
        this.temperature.lower = newTempLower;
    }

    /**
     * Update salinity field for both layers
     * (advection + diffusion + vertical mixing)
     */
    updateSalinity(dt) {
        const newSalUpper = [...this.salinity.upper];
        const newSalLower = [...this.salinity.lower];

        for (let i = 1; i < this.numBoxes - 1; i++) {
            const H = this.depth[i];
            const h_upper = this.layerFraction.upper * H;
            const h_lower = this.layerFraction.lower * H;

            // === UPPER LAYER ===
            let dSdt_upper = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dSdt_upper += this.advectionUpwind(i, 'upper', 'salinity');
            } else {
                dSdt_upper += this.advectionTVD(i, 'upper', 'salinity');
            }

            // 2. Diffusion
            const diffUpper = this.params.diffusivity *
                (this.salinity.upper[i+1] - 2*this.salinity.upper[i] + this.salinity.upper[i-1]) / (this.dx * this.dx);
            dSdt_upper += diffUpper;

            // 3. Vertical mixing
            const verticalMixing_upper = this.params.verticalMixing *
                (this.salinity.lower[i] - this.salinity.upper[i]) / h_upper;
            dSdt_upper += verticalMixing_upper;

            newSalUpper[i] = this.salinity.upper[i] + dSdt_upper * dt;

            // === LOWER LAYER ===
            let dSdt_lower = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dSdt_lower += this.advectionUpwind(i, 'lower', 'salinity');
            } else {
                dSdt_lower += this.advectionTVD(i, 'lower', 'salinity');
            }

            // 2. Diffusion
            const diffLower = this.params.diffusivity *
                (this.salinity.lower[i+1] - 2*this.salinity.lower[i] + this.salinity.lower[i-1]) / (this.dx * this.dx);
            dSdt_lower += diffLower;

            // 3. Vertical mixing
            const verticalMixing_lower = this.params.verticalMixing *
                (this.salinity.upper[i] - this.salinity.lower[i]) / h_lower;
            dSdt_lower += verticalMixing_lower;

            newSalLower[i] = this.salinity.lower[i] + dSdt_lower * dt;
        }

        this.salinity.upper = newSalUpper;
        this.salinity.lower = newSalLower;
    }

    /**
     * Upwind advection scheme for specified layer and field
     */
    advectionUpwind(i, layer, field) {
        const u = this.velocity[layer][i];
        const values = this[field][layer];

        if (u > 0) {
            // Flow to the right, use left-side difference
            return -u * (values[i] - values[i-1]) / this.dx;
        } else {
            // Flow to the left, use right-side difference
            return -u * (values[i+1] - values[i]) / this.dx;
        }
    }

    /**
     * TVD scheme for specified layer and field
     */
    advectionTVD(i, layer, field) {
        const u = this.velocity[layer][i];
        const values = this[field][layer];

        // Compute slopes
        const slopeLeft = values[i] - values[i-1];
        const slopeRight = values[i+1] - values[i];

        // Minmod limiter
        let limitedSlope = 0;
        if (slopeLeft * slopeRight > 0) {
            limitedSlope = Math.sign(slopeLeft) * Math.min(Math.abs(slopeLeft), Math.abs(slopeRight));
        }

        // Second-order correction
        const value_face = values[i] + 0.5 * limitedSlope * (u > 0 ? -1 : 1);

        return -u * (u > 0 ?
            (value_face - values[i-1]) :
            (values[i+1] - value_face)
        ) / this.dx;
    }

    /**
     * Calculate surface heat flux (diurnal cycle)
     * Positive = heating, Negative = cooling
     */
    getSurfaceHeatFlux() {
        const omega = 2 * Math.PI / 86400; // diurnal cycle (24 hours)
        return this.params.heatFluxAmplitude * Math.cos(omega * this.time);
    }

    /**
     * Apply boundary conditions at mouth and head for two layers
     */
    applyBoundaryConditions() {
        // MOUTH (ocean end - box 0)
        // Coastal mixing parameter applies to ALL layers equally
        // oceanMixing parameter: 0 = pure estuarine recirculation, 1 = pure ocean, 0.5 = 50/50 mix
        const alpha = this.params.oceanMixing;

        // Lower layer: coastal mixing
        this.temperature.lower[0] = this.params.oceanTemp;
        this.salinity.lower[0] = alpha * this.params.oceanSalinity +
                                 (1 - alpha) * this.salinity.lower[1];

        // Upper layer: coastal mixing
        this.temperature.upper[0] = this.params.oceanTemp;
        this.salinity.upper[0] = alpha * this.params.oceanSalinity +
                                 (1 - alpha) * this.salinity.upper[1];

        // HEAD (river end - box numBoxes-1)
        // River water enters well-mixed - BOTH layers have same river properties
        // No stratification at river boundary (river water is fresh and well-mixed)
        this.temperature.upper[this.numBoxes - 1] = this.params.riverTemp;
        this.salinity.upper[this.numBoxes - 1] = this.params.riverSalinity;
        this.temperature.lower[this.numBoxes - 1] = this.params.riverTemp;
        this.salinity.lower[this.numBoxes - 1] = this.params.riverSalinity;
    }

    /**
     * Get diagnostic statistics for two layers
     */
    getDiagnostics() {
        // Upper layer stats
        const tempsUpper = this.temperature.upper.slice(1, -1);
        const salsUpper = this.salinity.upper.slice(1, -1);
        const meanTempUpper = tempsUpper.reduce((a, b) => a + b) / tempsUpper.length;
        const meanSalinityUpper = salsUpper.reduce((a, b) => a + b) / salsUpper.length;

        // Lower layer stats
        const tempsLower = this.temperature.lower.slice(1, -1);
        const salsLower = this.salinity.lower.slice(1, -1);
        const meanTempLower = tempsLower.reduce((a, b) => a + b) / tempsLower.length;
        const meanSalinityLower = salsLower.reduce((a, b) => a + b) / salsLower.length;

        // Stratification (lower - upper, positive means stable)
        const stratificationTemp = meanTempLower - meanTempUpper;
        const stratificationSalinity = meanSalinityLower - meanSalinityUpper;

        // Overall mean (depth-weighted would be better, but simple mean for now)
        const meanTemp = (meanTempUpper + meanTempLower) / 2;
        const meanSalinity = (meanSalinityUpper + meanSalinityLower) / 2;

        // Calculate observed warming
        const initialMeanTempUpper = this.initialTemperature.upper.slice(1, -1).reduce((a, b) => a + b) / tempsUpper.length;
        const initialMeanTempLower = this.initialTemperature.lower.slice(1, -1).reduce((a, b) => a + b) / tempsLower.length;
        const initialMeanTemp = (initialMeanTempUpper + initialMeanTempLower) / 2;
        const observedWarming = meanTemp - initialMeanTemp;

        // Expected warming from time series
        const expectedWarming = this.timeSeries.expectedWarming.length > 0 ?
            this.timeSeries.expectedWarming[this.timeSeries.expectedWarming.length - 1] : 0;

        // Warming rates
        const observedWarmingRate = this.elapsedDays > 0 ? observedWarming / this.elapsedDays : 0;
        const expectedWarmingRate = this.elapsedDays > 0 ? expectedWarming / this.elapsedDays : 0;

        // VELOCITY DIAGNOSTICS AT MOUTH (box 0)
        const u_barotropic_mouth = this.u_barotropic[0];
        const u_upper_mouth = this.velocity.upper[0];
        const u_lower_mouth = this.velocity.lower[0];
        const Q_exchange_mouth = this.exchangeFlow[0];

        // Volume fluxes at mouth (m³/s)
        const H_mouth = this.depth[0];
        const W_mouth = this.width[0];
        const h_upper_mouth = this.layerFraction.upper * H_mouth;
        const h_lower_mouth = this.layerFraction.lower * H_mouth;
        const Q_upper_mouth = u_upper_mouth * W_mouth * h_upper_mouth;
        const Q_lower_mouth = u_lower_mouth * W_mouth * h_lower_mouth;
        const Q_total_mouth = Q_upper_mouth + Q_lower_mouth;

        // Expected river velocity for comparison (at RIVER END, not mouth!)
        const river_idx = this.numBoxes - 1;
        const H_river = this.depth[river_idx];
        const W_river = this.width[river_idx];
        const riverVelocity_expected = this.params.riverDischarge / (W_river * H_river);

        // Tidal velocity magnitude (expected ~1.0 m/s)
        const omega = 2 * Math.PI / this.params.tidalPeriod;
        const eta_prescribed = this.params.tidalAmplitude * Math.sin(omega * this.time);
        const c_ocean = Math.sqrt(this.g * this.depth[0]);
        const tidalVelocity_expected = (c_ocean / this.depth[0]) * eta_prescribed;

        // VELOCITY PROFILE AT MULTIPLE LOCATIONS
        const idx_10km = Math.min(Math.floor(this.numBoxes * 0.2), this.numBoxes - 1);  // ~20% in
        const idx_25km = Math.min(Math.floor(this.numBoxes * 0.5), this.numBoxes - 1);  // ~50% in
        const idx_river = this.numBoxes - 1;  // River end

        const velocityProfile = {
            mouth: {
                distance: 0,
                u_baro: this.u_barotropic[0],
                u_upper: this.velocity.upper[0],
                u_lower: this.velocity.lower[0],
                eta: this.eta[0]
            },
            km10: {
                distance: (idx_10km * this.dx) / 1000,
                u_baro: this.u_barotropic[idx_10km],
                u_upper: this.velocity.upper[idx_10km],
                u_lower: this.velocity.lower[idx_10km],
                eta: this.eta[idx_10km]
            },
            km25: {
                distance: (idx_25km * this.dx) / 1000,
                u_baro: this.u_barotropic[idx_25km],
                u_upper: this.velocity.upper[idx_25km],
                u_lower: this.velocity.lower[idx_25km],
                eta: this.eta[idx_25km]
            },
            river: {
                distance: (idx_river * this.dx) / 1000,
                u_baro: this.u_barotropic[idx_river],
                u_upper: this.velocity.upper[idx_river],
                u_lower: this.velocity.lower[idx_river],
                eta: this.eta[idx_river]
            }
        };

        return {
            meanTemp,
            meanTempUpper,
            meanTempLower,
            minTemp: Math.min(...tempsUpper, ...tempsLower),
            maxTemp: Math.max(...tempsUpper, ...tempsLower),
            meanSalinity,
            meanSalinityUpper,
            meanSalinityLower,
            minSalinity: Math.min(...salsUpper, ...salsLower),
            maxSalinity: Math.max(...salsUpper, ...salsLower),
            stratificationTemp,
            stratificationSalinity,
            currentHeatFlux: this.getSurfaceHeatFlux(),
            cfl: this.calculateCFL(),
            observedWarming,
            expectedWarming,
            observedWarmingRate,
            expectedWarmingRate,
            // Velocity diagnostics
            u_barotropic_mouth,
            u_upper_mouth,
            u_lower_mouth,
            Q_exchange_mouth,
            Q_upper_mouth,
            Q_lower_mouth,
            Q_total_mouth,
            riverVelocity_expected,
            tidalVelocity_expected,
            velocityRatio: Math.abs(tidalVelocity_expected / riverVelocity_expected),
            velocityProfile
        };
    }

    /**
     * Calculate CFL number for stability check
     */
    calculateCFL() {
        const maxU_upper = Math.max(...this.velocity.upper.map(Math.abs));
        const maxU_lower = Math.max(...this.velocity.lower.map(Math.abs));
        const maxU = Math.max(maxU_upper, maxU_lower);
        const dt = this.params.dt;
        return maxU * dt / this.dx;
    }

    /**
     * Get velocity components decomposed into tidal, river, and baroclinic
     * Returns arrays for each component showing upper and lower layer velocities
     */
    getVelocityComponents() {
        const tidal = { upper: [], lower: [] };
        const river = { upper: [], lower: [] };
        const baroclinic = { upper: [], lower: [] };

        for (let i = 0; i < this.numBoxes; i++) {
            const H = this.depth[i];
            const W = this.width[i];
            const h_upper = this.layerFraction.upper * H;
            const h_lower = this.layerFraction.lower * H;
            const A_upper = W * h_upper;
            const A_lower = W * h_lower;

            // 1. RIVER COMPONENT (steady barotropic from discharge)
            // This is the depth-averaged velocity needed to transport the river discharge
            const u_river = -this.params.riverDischarge / (W * H);  // negative = seaward
            river.upper[i] = u_river;
            river.lower[i] = u_river;

            // 2. TIDAL COMPONENT (oscillating barotropic = total barotropic - river)
            const u_tidal = this.u_barotropic[i] - u_river;
            tidal.upper[i] = u_tidal;
            tidal.lower[i] = u_tidal;

            // 3. BAROCLINIC COMPONENT (density-driven exchange)
            // Upper layer: seaward (negative), Lower layer: landward (positive)
            const Q_ex = this.exchangeFlow[i];
            baroclinic.upper[i] = -Q_ex / A_upper;
            baroclinic.lower[i] = +Q_ex / A_lower;
        }

        return { tidal, river, baroclinic };
    }

    /**
     * Reset simulation
     */
    reset() {
        this.time = 0;
        this.elapsedDays = 0;
        this.eta.fill(0);
        this.u_barotropic.fill(0);
        this.velocity.upper.fill(0);
        this.velocity.lower.fill(0);
        this.exchangeFlow.fill(0);
        this.setInitialProfiles();
        this.initialTemperature.upper = [...this.temperature.upper];
        this.initialTemperature.lower = [...this.temperature.lower];
        this.initialSalinity.upper = [...this.salinity.upper];
        this.initialSalinity.lower = [...this.salinity.lower];

        // Clear time series
        this.timeSeries = {
            time: [],
            meanTempUpper: [],
            meanTempLower: [],
            meanSalinityUpper: [],
            meanSalinityLower: [],
            stratificationTemp: [],
            stratificationSalinity: [],
            heatFlux: [],
            expectedWarming: []
        };
        this.lastSampleTime = 0;
    }

    /**
     * Load a preset scenario
     */
    loadPreset(presetName) {
        const presets = {
            'spring-tide': {
                tidalAmplitude: 2.5,
                riverDischarge: 100,
                heatFluxAmplitude: 200,
                oceanTemp: 18,
                riverTemp: 12,
                diffusivity: 100,
                taperedGeometry: true
            },
            'flood': {
                tidalAmplitude: 1.0,
                riverDischarge: 400,
                heatFluxAmplitude: 150,
                oceanTemp: 18,
                riverTemp: 10,
                diffusivity: 150,
                taperedGeometry: true
            },
            'heat-wave': {
                tidalAmplitude: 0.5,
                riverDischarge: 50,
                heatFluxAmplitude: 450,
                oceanTemp: 22,
                riverTemp: 16,
                diffusivity: 80,
                taperedGeometry: true
            },
            'winter': {
                tidalAmplitude: 1.2,
                riverDischarge: 200,
                heatFluxAmplitude: 100,
                oceanTemp: 8,
                riverTemp: 6,
                diffusivity: 100,
                taperedGeometry: false
            }
        };

        if (presets[presetName]) {
            Object.assign(this.params, presets[presetName]);
            this.updateGeometry();
            this.reset();
        }
    }

    /**
     * Export current state to CSV
     */
    exportToCSV() {
        let csv = 'CSV Export - 2-Layer Estuary Simulator\n\n';

        // Spatial Profile
        csv += 'Spatial Profile (Current)\n';
        csv += 'Box,Distance (km),Depth (m),Width (m),T_upper (°C),T_lower (°C),S_upper (psu),S_lower (psu),U_upper (m/s),U_lower (m/s),Q_ex (m³/s)\n';
        for (let i = 0; i < this.numBoxes; i++) {
            const distance = (i * this.dx) / 1000;
            csv += `${i},${distance.toFixed(2)},${this.depth[i].toFixed(2)},${this.width[i].toFixed(0)},`;
            csv += `${this.temperature.upper[i].toFixed(3)},${this.temperature.lower[i].toFixed(3)},`;
            csv += `${this.salinity.upper[i].toFixed(3)},${this.salinity.lower[i].toFixed(3)},`;
            csv += `${this.velocity.upper[i].toFixed(4)},${this.velocity.lower[i].toFixed(4)},${this.exchangeFlow[i].toFixed(2)}\n`;
        }

        csv += '\n';

        // Time Series
        csv += 'Time Series\n';
        csv += 'Time (days),T_upper (°C),T_lower (°C),S_upper (psu),S_lower (psu),ΔT (°C),ΔS (psu),Heat Flux (W/m²)\n';
        for (let i = 0; i < this.timeSeries.time.length; i++) {
            csv += `${this.timeSeries.time[i].toFixed(4)},`;
            csv += `${this.timeSeries.meanTempUpper[i].toFixed(3)},${this.timeSeries.meanTempLower[i].toFixed(3)},`;
            csv += `${this.timeSeries.meanSalinityUpper[i].toFixed(3)},${this.timeSeries.meanSalinityLower[i].toFixed(3)},`;
            csv += `${this.timeSeries.stratificationTemp[i].toFixed(3)},${this.timeSeries.stratificationSalinity[i].toFixed(3)},`;
            csv += `${this.timeSeries.heatFlux[i].toFixed(2)}\n`;
        }

        csv += '\n';

        // Parameters
        csv += 'Parameters\n';
        csv += 'Parameter,Value\n';
        for (const [key, value] of Object.entries(this.params)) {
            csv += `${key},${value}\n`;
        }

        return csv;
    }

    /**
     * Download CSV file
     */
    downloadCSV() {
        const csv = this.exportToCSV();
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `estuary_simulation_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}
