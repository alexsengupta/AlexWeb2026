/**
 * EstuaryModel_3layer.js
 * Core physics model for 1D estuary with THREE vertical layers
 * Surface mixed layer + thermocline/pycnocline + deep layer
 * Realistic surface temperature dynamics
 */

class EstuaryModel_3layer {
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

        // Layer thickness fractions - THREE LAYERS for realistic surface temperature
        this.layerFraction = {
            surface: 0.2,  // 20% of total depth (~2m) - receives heat flux, responds quickly
            middle: 0.4,   // 40% of total depth (~4m) - thermocline/pycnocline forms here
            deep: 0.4      // 40% of total depth (~4m) - insulated, slow response
        };

        // State variables (arrays for each box)
        // THREE-layer structure: surface, middle, deep
        this.temperature = {
            surface: new Array(numBoxes).fill(15),
            middle: new Array(numBoxes).fill(15),
            deep: new Array(numBoxes).fill(15)
        };
        this.salinity = {
            surface: new Array(numBoxes).fill(30),
            middle: new Array(numBoxes).fill(30),
            deep: new Array(numBoxes).fill(30)
        };
        this.eta = new Array(numBoxes).fill(0); // sea level (m)
        this.depth = new Array(numBoxes).fill(10); // total depth (m)
        this.width = new Array(numBoxes).fill(1000); // width (m)

        // Barotropic (depth-averaged) velocity for shallow water
        this.u_barotropic = new Array(numBoxes).fill(0);

        // Layer-specific velocities
        this.velocity = {
            surface: new Array(numBoxes).fill(0),
            middle: new Array(numBoxes).fill(0),
            deep: new Array(numBoxes).fill(0)
        };

        // Exchange flow magnitudes at two interfaces (m³/s)
        this.exchangeFlow = {
            surface_middle: new Array(numBoxes).fill(0), // Q_ex at surface-middle interface
            middle_deep: new Array(numBoxes).fill(0)     // Q_ex at middle-deep interface
        };

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

        // Time series data storage - THREE LAYERS
        this.timeSeries = {
            time: [],                      // elapsed days
            meanTempSurface: [],           // domain-mean surface layer temperature
            meanTempMiddle: [],            // domain-mean middle layer temperature
            meanTempDeep: [],              // domain-mean deep layer temperature
            meanSalinitySurface: [],       // domain-mean surface layer salinity
            meanSalinityMiddle: [],        // domain-mean middle layer salinity
            meanSalinityDeep: [],          // domain-mean deep layer salinity
            stratificationTemp_SM: [],     // ΔT (middle - surface) - diurnal thermocline
            stratificationTemp_MD: [],     // ΔT (deep - middle) - seasonal thermocline
            stratificationSalinity_SM: [], // ΔS (middle - surface)
            stratificationSalinity_MD: [], // ΔS (deep - middle)
            heatFlux: [],                  // surface heat flux
            expectedWarming: []            // cumulative expected warming from heat flux
        };

        // Initial profiles (t=0 reference)
        this.initialTemperature = {
            surface: null,
            middle: null,
            deep: null
        };
        this.initialSalinity = {
            surface: null,
            middle: null,
            deep: null
        };

        // Sampling interval for time series (every N seconds)
        this.sampleInterval = 1800; // 30 minutes
        this.lastSampleTime = 0;

        // Initialize geometry
        this.updateGeometry();

        // Initialize temperature and salinity profiles
        this.setInitialProfiles();

        // Store initial profiles
        this.initialTemperature.surface = [...this.temperature.surface];
        this.initialTemperature.middle = [...this.temperature.middle];
        this.initialTemperature.deep = [...this.temperature.deep];
        this.initialSalinity.surface = [...this.salinity.surface];
        this.initialSalinity.middle = [...this.salinity.middle];
        this.initialSalinity.deep = [...this.salinity.deep];
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
     * All layers start with same values (well-mixed vertically)
     */
    setInitialProfiles() {
        for (let i = 0; i < this.numBoxes; i++) {
            const x = i / (this.numBoxes - 1); // 0 at mouth, 1 at head

            // Temperature: linear ramp from ocean to river (all layers equal)
            const temp = this.params.oceanTemp + x * (this.params.riverTemp - this.params.oceanTemp);
            this.temperature.surface[i] = temp;
            this.temperature.middle[i] = temp;
            this.temperature.deep[i] = temp;

            // Salinity: linear ramp from ocean to river (all layers equal)
            const salinity = this.params.oceanSalinity + x * (this.params.riverSalinity - this.params.oceanSalinity);
            this.salinity.surface[i] = salinity;
            this.salinity.middle[i] = salinity;
            this.salinity.deep[i] = salinity;
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

        // 3. Add baroclinic component to get layer velocities (TWO INTERFACES)
        this.updateLayerVelocities();

        // 4. Update temperature (advection + diffusion + heat flux to surface only)
        this.updateTemperature(dt);

        // 5. Update salinity (advection + diffusion)
        this.updateSalinity(dt);

        // 6. Convective mixing (remove static instabilities)
        this.convectiveMixing();

        // 7. Apply boundary conditions
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
        this.timeSeries.meanTempSurface.push(diagnostics.meanTempSurface);
        this.timeSeries.meanTempMiddle.push(diagnostics.meanTempMiddle);
        this.timeSeries.meanTempDeep.push(diagnostics.meanTempDeep);
        this.timeSeries.meanSalinitySurface.push(diagnostics.meanSalinitySurface);
        this.timeSeries.meanSalinityMiddle.push(diagnostics.meanSalinityMiddle);
        this.timeSeries.meanSalinityDeep.push(diagnostics.meanSalinityDeep);
        this.timeSeries.stratificationTemp_SM.push(diagnostics.stratificationTemp_SM);
        this.timeSeries.stratificationTemp_MD.push(diagnostics.stratificationTemp_MD);
        this.timeSeries.stratificationSalinity_SM.push(diagnostics.stratificationSalinity_SM);
        this.timeSeries.stratificationSalinity_MD.push(diagnostics.stratificationSalinity_MD);
        this.timeSeries.heatFlux.push(diagnostics.currentHeatFlux);

        // Calculate cumulative expected warming from heat flux (only surface layer)
        const meanDepth = this.depth.reduce((a, b) => a + b) / this.depth.length;
        const h_surface = this.layerFraction.surface * meanDepth;
        const expectedWarmingRate = diagnostics.currentHeatFlux / (this.rho * this.cp * h_surface);
        const dt = this.sampleInterval;

        const prevExpectedWarming = this.timeSeries.expectedWarming.length > 0 ?
            this.timeSeries.expectedWarming[this.timeSeries.expectedWarming.length - 1] : 0;

        this.timeSeries.expectedWarming.push(prevExpectedWarming + expectedWarmingRate * dt);
    }

    /**
     * Update barotropic velocity using shallow water momentum equation
     * ∂u/∂t = -g·∂η/∂x - r·u
     * Uses FORWARD difference at ocean boundary, BACKWARD difference in interior
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
            const dEta_dx = (this.eta[i] - this.eta[i - 1]) / this.dx;
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
            const flux_here = this.u_barotropic[i] * this.depth[i];
            const flux_right = this.u_barotropic[i + 1] * this.depth[i + 1];
            const dFlux_dx = (flux_right - flux_here) / this.dx;

            // Forward Euler time step
            newEta[i] = this.eta[i] - dFlux_dx * dt;
        }

        // Boundary condition at river: zero gradient or slight elevation from river input
        const river_effect = this.params.riverDischarge / (this.width[this.numBoxes - 1] * this.depth[this.numBoxes - 1] * 100);
        newEta[this.numBoxes - 1] = newEta[this.numBoxes - 2] + river_effect;

        this.eta = newEta;
    }

    /**
     * Calculate layer velocities by adding baroclinic component to barotropic flow
     * THREE-layer velocities = barotropic flow ± exchange at TWO INTERFACES
     */
    updateLayerVelocities() {
        for (let i = 0; i < this.numBoxes; i++) {
            const H = this.depth[i];
            const W = this.width[i];

            // Layer thicknesses
            const h_surface = this.layerFraction.surface * H;
            const h_middle = this.layerFraction.middle * H;
            const h_deep = this.layerFraction.deep * H;

            // === SURFACE-MIDDLE INTERFACE ===
            // Calculate reduced gravity from density difference
            const deltaT_SM = this.temperature.middle[i] - this.temperature.surface[i];
            const deltaS_SM = this.salinity.middle[i] - this.salinity.surface[i];
            const gPrime_SM = this.g * (this.beta * deltaS_SM - this.alpha * deltaT_SM);

            // Exchange flow magnitude at surface-middle interface
            let Q_ex_SM = 0;
            if (gPrime_SM > 0) {
                // FIXED: Use Total Depth H for scaling, not layer thickness (matches 2-layer model)
                Q_ex_SM = this.params.exchangeCoefficient * W * H * Math.sqrt(gPrime_SM * H);
            }

            // === MIDDLE-DEEP INTERFACE ===
            // Calculate reduced gravity from density difference
            const deltaT_MD = this.temperature.deep[i] - this.temperature.middle[i];
            const deltaS_MD = this.salinity.deep[i] - this.salinity.middle[i];
            const gPrime_MD = this.g * (this.beta * deltaS_MD - this.alpha * deltaT_MD);

            // Exchange flow magnitude at middle-deep interface
            let Q_ex_MD = 0;
            if (gPrime_MD > 0) {
                // FIXED: Use Total Depth H for scaling, not layer thickness (matches 2-layer model)
                Q_ex_MD = this.params.exchangeCoefficient * W * H * Math.sqrt(gPrime_MD * H);
            }

            // Store exchange flows for diagnostics
            this.exchangeFlow.surface_middle[i] = Q_ex_SM;
            this.exchangeFlow.middle_deep[i] = Q_ex_MD;

            // === LAYER VELOCITIES ===
            // Mass-conserving velocities
            // S-M Exchange: Surface goes SEAWARD (-), Middle+Deep go LANDWARD (+)
            // M-D Exchange: Middle goes SEAWARD (-), Deep goes LANDWARD (+)

            const A_surface = W * h_surface;
            const A_middle = W * h_middle;
            const A_deep = W * h_deep;

            // 1. Surface-Middle Exchange Contribution
            // Drives Surface one way, and (Middle + Deep) the other way
            const u_SM_surface = -Q_ex_SM / A_surface;
            const u_SM_return = Q_ex_SM / (A_middle + A_deep); // Distributed return flow

            // 2. Middle-Deep Exchange Contribution
            // Drives Middle one way, and Deep the other way
            const u_MD_middle = -Q_ex_MD / A_middle;
            const u_MD_deep = +Q_ex_MD / A_deep;

            // Total Velocities
            this.velocity.surface[i] = this.u_barotropic[i] + u_SM_surface;
            this.velocity.middle[i] = this.u_barotropic[i] + u_SM_return + u_MD_middle;
            this.velocity.deep[i] = this.u_barotropic[i] + u_SM_return + u_MD_deep;
        }
    }

    /**
     * Update temperature field for THREE layers
     * Heat flux ONLY to surface layer - key for realistic surface temperature!
     */
    updateTemperature(dt) {
        const newTempSurface = [...this.temperature.surface];
        const newTempMiddle = [...this.temperature.middle];
        const newTempDeep = [...this.temperature.deep];

        for (let i = 1; i < this.numBoxes - 1; i++) {
            const H = this.depth[i];
            const h_surface = this.layerFraction.surface * H;
            const h_middle = this.layerFraction.middle * H;
            const h_deep = this.layerFraction.deep * H;

            // === SURFACE LAYER ===
            let dTdt_surface = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dTdt_surface += this.advectionUpwind(i, 'surface', 'temperature');
            } else {
                dTdt_surface += this.advectionTVD(i, 'surface', 'temperature');
            }

            // 2. Diffusion
            const diffSurface = this.params.diffusivity *
                (this.temperature.surface[i + 1] - 2 * this.temperature.surface[i] + this.temperature.surface[i - 1]) / (this.dx * this.dx);
            dTdt_surface += diffSurface;

            // 3. Surface heat flux (ONLY to surface layer - key change!)
            const heatFlux = this.getSurfaceHeatFlux();
            const heatFluxTerm = heatFlux / (this.rho * this.cp * h_surface);
            dTdt_surface += heatFluxTerm;

            // 4. Vertical mixing with middle layer
            const verticalMixing_S = this.params.verticalMixing *
                (this.temperature.middle[i] - this.temperature.surface[i]) / h_surface;
            dTdt_surface += verticalMixing_S;

            newTempSurface[i] = this.temperature.surface[i] + dTdt_surface * dt;

            // === MIDDLE LAYER ===
            let dTdt_middle = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dTdt_middle += this.advectionUpwind(i, 'middle', 'temperature');
            } else {
                dTdt_middle += this.advectionTVD(i, 'middle', 'temperature');
            }

            // 2. Diffusion
            const diffMiddle = this.params.diffusivity *
                (this.temperature.middle[i + 1] - 2 * this.temperature.middle[i] + this.temperature.middle[i - 1]) / (this.dx * this.dx);
            dTdt_middle += diffMiddle;

            // 3. Vertical mixing with surface layer (above)
            const verticalMixing_M_up = this.params.verticalMixing *
                (this.temperature.surface[i] - this.temperature.middle[i]) / h_middle;
            dTdt_middle += verticalMixing_M_up;

            // 4. Vertical mixing with deep layer (below)
            const verticalMixing_M_down = this.params.verticalMixing *
                (this.temperature.deep[i] - this.temperature.middle[i]) / h_middle;
            dTdt_middle += verticalMixing_M_down;

            newTempMiddle[i] = this.temperature.middle[i] + dTdt_middle * dt;

            // === DEEP LAYER ===
            let dTdt_deep = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dTdt_deep += this.advectionUpwind(i, 'deep', 'temperature');
            } else {
                dTdt_deep += this.advectionTVD(i, 'deep', 'temperature');
            }

            // 2. Diffusion
            const diffDeep = this.params.diffusivity *
                (this.temperature.deep[i + 1] - 2 * this.temperature.deep[i] + this.temperature.deep[i - 1]) / (this.dx * this.dx);
            dTdt_deep += diffDeep;

            // 3. Vertical mixing with middle layer (above)
            const verticalMixing_D = this.params.verticalMixing *
                (this.temperature.middle[i] - this.temperature.deep[i]) / h_deep;
            dTdt_deep += verticalMixing_D;

            newTempDeep[i] = this.temperature.deep[i] + dTdt_deep * dt;
        }

        this.temperature.surface = newTempSurface;
        this.temperature.middle = newTempMiddle;
        this.temperature.deep = newTempDeep;
    }

    /**
     * Update salinity field for THREE layers
     * (advection + diffusion + vertical mixing between adjacent layers)
     */
    updateSalinity(dt) {
        const newSalSurface = [...this.salinity.surface];
        const newSalMiddle = [...this.salinity.middle];
        const newSalDeep = [...this.salinity.deep];

        for (let i = 1; i < this.numBoxes - 1; i++) {
            const H = this.depth[i];
            const h_surface = this.layerFraction.surface * H;
            const h_middle = this.layerFraction.middle * H;
            const h_deep = this.layerFraction.deep * H;

            // === SURFACE LAYER ===
            let dSdt_surface = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dSdt_surface += this.advectionUpwind(i, 'surface', 'salinity');
            } else {
                dSdt_surface += this.advectionTVD(i, 'surface', 'salinity');
            }

            // 2. Diffusion
            const diffSurface = this.params.diffusivity *
                (this.salinity.surface[i + 1] - 2 * this.salinity.surface[i] + this.salinity.surface[i - 1]) / (this.dx * this.dx);
            dSdt_surface += diffSurface;

            // 3. Vertical mixing
            const verticalMixing_S = this.params.verticalMixing *
                (this.salinity.middle[i] - this.salinity.surface[i]) / h_surface;
            dSdt_surface += verticalMixing_S;

            newSalSurface[i] = this.salinity.surface[i] + dSdt_surface * dt;

            // === MIDDLE LAYER ===
            let dSdt_middle = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dSdt_middle += this.advectionUpwind(i, 'middle', 'salinity');
            } else {
                dSdt_middle += this.advectionTVD(i, 'middle', 'salinity');
            }

            // 2. Diffusion
            const diffMiddle = this.params.diffusivity *
                (this.salinity.middle[i + 1] - 2 * this.salinity.middle[i] + this.salinity.middle[i - 1]) / (this.dx * this.dx);
            dSdt_middle += diffMiddle;

            // 3. Vertical mixing with surface (above)
            const verticalMixing_M_up = this.params.verticalMixing *
                (this.salinity.surface[i] - this.salinity.middle[i]) / h_middle;
            dSdt_middle += verticalMixing_M_up;

            // 4. Vertical mixing with deep (below)
            const verticalMixing_M_down = this.params.verticalMixing *
                (this.salinity.deep[i] - this.salinity.middle[i]) / h_middle;
            dSdt_middle += verticalMixing_M_down;

            newSalMiddle[i] = this.salinity.middle[i] + dSdt_middle * dt;

            // === DEEP LAYER ===
            let dSdt_deep = 0;

            // 1. Advection
            if (this.params.advectionScheme === 'upwind') {
                dSdt_deep += this.advectionUpwind(i, 'deep', 'salinity');
            } else {
                dSdt_deep += this.advectionTVD(i, 'deep', 'salinity');
            }

            // 2. Diffusion
            const diffDeep = this.params.diffusivity *
                (this.salinity.deep[i + 1] - 2 * this.salinity.deep[i] + this.salinity.deep[i - 1]) / (this.dx * this.dx);
            dSdt_deep += diffDeep;

            // 3. Vertical mixing with middle (above)
            const verticalMixing_D = this.params.verticalMixing *
                (this.salinity.middle[i] - this.salinity.deep[i]) / h_deep;
            dSdt_deep += verticalMixing_D;

            newSalDeep[i] = this.salinity.deep[i] + dSdt_deep * dt;
        }

        this.salinity.surface = newSalSurface;
        this.salinity.middle = newSalMiddle;
        this.salinity.deep = newSalDeep;
    }

    /**
     * Check for and remove static instabilities (heavy over light)
     * Mixes adjacent layers if density inversion exists
     */
    convectiveMixing() {
        for (let i = 0; i < this.numBoxes; i++) {
            // Calculate densities
            const rho_surface = this.rho * (1 - this.alpha * (this.temperature.surface[i] - 15) + this.beta * (this.salinity.surface[i] - 35));
            const rho_middle = this.rho * (1 - this.alpha * (this.temperature.middle[i] - 15) + this.beta * (this.salinity.middle[i] - 35));
            const rho_deep = this.rho * (1 - this.alpha * (this.temperature.deep[i] - 15) + this.beta * (this.salinity.deep[i] - 35));

            // Check Surface vs Middle
            if (rho_surface > rho_middle) {
                // Mix T and S
                const T_mix = (this.temperature.surface[i] * this.layerFraction.surface + this.temperature.middle[i] * this.layerFraction.middle) / (this.layerFraction.surface + this.layerFraction.middle);
                const S_mix = (this.salinity.surface[i] * this.layerFraction.surface + this.salinity.middle[i] * this.layerFraction.middle) / (this.layerFraction.surface + this.layerFraction.middle);

                this.temperature.surface[i] = T_mix;
                this.temperature.middle[i] = T_mix;
                this.salinity.surface[i] = S_mix;
                this.salinity.middle[i] = S_mix;
            }

            // Re-calculate density for middle (it might have changed)
            const rho_middle_new = this.rho * (1 - this.alpha * (this.temperature.middle[i] - 15) + this.beta * (this.salinity.middle[i] - 35));

            // Check Middle vs Deep
            if (rho_middle_new > rho_deep) {
                // Mix T and S
                const T_mix = (this.temperature.middle[i] * this.layerFraction.middle + this.temperature.deep[i] * this.layerFraction.deep) / (this.layerFraction.middle + this.layerFraction.deep);
                const S_mix = (this.salinity.middle[i] * this.layerFraction.middle + this.salinity.deep[i] * this.layerFraction.deep) / (this.layerFraction.middle + this.layerFraction.deep);

                this.temperature.middle[i] = T_mix;
                this.temperature.deep[i] = T_mix;
                this.salinity.middle[i] = S_mix;
                this.salinity.deep[i] = S_mix;
            }
        }
    }

    /**
     * Upwind advection scheme for specified layer and field
     */
    advectionUpwind(i, layer, field) {
        const u = this.velocity[layer][i];
        const values = this[field][layer];

        if (u > 0) {
            // Flow to the right, use left-side difference
            return -u * (values[i] - values[i - 1]) / this.dx;
        } else {
            // Flow to the left, use right-side difference
            return -u * (values[i + 1] - values[i]) / this.dx;
        }
    }

    /**
     * TVD scheme for specified layer and field
     */
    advectionTVD(i, layer, field) {
        const u = this.velocity[layer][i];
        const values = this[field][layer];

        // Compute slopes
        const slopeLeft = values[i] - values[i - 1];
        const slopeRight = values[i + 1] - values[i];

        // Minmod limiter
        let limitedSlope = 0;
        if (slopeLeft * slopeRight > 0) {
            limitedSlope = Math.sign(slopeLeft) * Math.min(Math.abs(slopeLeft), Math.abs(slopeRight));
        }

        // Second-order correction
        const value_face = values[i] + 0.5 * limitedSlope * (u > 0 ? -1 : 1);

        return -u * (u > 0 ?
            (value_face - values[i - 1]) :
            (values[i + 1] - value_face)
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
     * Apply boundary conditions at mouth and head for THREE layers
     */
    applyBoundaryConditions() {
        // MOUTH (ocean end - box 0)
        // Coastal mixing parameter applies to ALL layers equally
        // oceanMixing parameter: 0 = pure estuarine recirculation, 1 = pure ocean, 0.5 = 50/50 mix
        const alpha = this.params.oceanMixing;

        // Deep layer: coastal mixing
        this.temperature.deep[0] = this.params.oceanTemp;
        this.salinity.deep[0] = alpha * this.params.oceanSalinity +
            (1 - alpha) * this.salinity.deep[1];

        // Middle layer: coastal mixing
        this.temperature.middle[0] = this.params.oceanTemp;
        this.salinity.middle[0] = alpha * this.params.oceanSalinity +
            (1 - alpha) * this.salinity.middle[1];

        // Surface layer: coastal mixing
        this.temperature.surface[0] = this.params.oceanTemp;
        this.salinity.surface[0] = alpha * this.params.oceanSalinity +
            (1 - alpha) * this.salinity.surface[1];

        // HEAD (river end - box numBoxes-1)
        // River water enters well-mixed - ALL layers have same river properties
        // No stratification at river boundary (river water is fresh and well-mixed)
        this.temperature.surface[this.numBoxes - 1] = this.params.riverTemp;
        this.salinity.surface[this.numBoxes - 1] = this.params.riverSalinity;
        this.temperature.middle[this.numBoxes - 1] = this.params.riverTemp;
        this.salinity.middle[this.numBoxes - 1] = this.params.riverSalinity;
        this.temperature.deep[this.numBoxes - 1] = this.params.riverTemp;
        this.salinity.deep[this.numBoxes - 1] = this.params.riverSalinity;
    }

    /**
     * Get diagnostic statistics for THREE layers
     */
    getDiagnostics() {
        // Surface layer stats
        const tempsSurface = this.temperature.surface.slice(1, -1);
        const salsSurface = this.salinity.surface.slice(1, -1);
        const meanTempSurface = tempsSurface.reduce((a, b) => a + b) / tempsSurface.length;
        const meanSalinitySurface = salsSurface.reduce((a, b) => a + b) / salsSurface.length;

        // Middle layer stats
        const tempsMiddle = this.temperature.middle.slice(1, -1);
        const salsMiddle = this.salinity.middle.slice(1, -1);
        const meanTempMiddle = tempsMiddle.reduce((a, b) => a + b) / tempsMiddle.length;
        const meanSalinityMiddle = salsMiddle.reduce((a, b) => a + b) / salsMiddle.length;

        // Deep layer stats
        const tempsDeep = this.temperature.deep.slice(1, -1);
        const salsDeep = this.salinity.deep.slice(1, -1);
        const meanTempDeep = tempsDeep.reduce((a, b) => a + b) / tempsDeep.length;
        const meanSalinityDeep = salsDeep.reduce((a, b) => a + b) / salsDeep.length;

        // Stratification at both interfaces
        const stratificationTemp_SM = meanTempMiddle - meanTempSurface;  // Diurnal thermocline
        const stratificationTemp_MD = meanTempDeep - meanTempMiddle;     // Seasonal thermocline
        const stratificationSalinity_SM = meanSalinityMiddle - meanSalinitySurface;
        const stratificationSalinity_MD = meanSalinityDeep - meanSalinityMiddle;

        // Overall mean (depth-weighted)
        const meanTemp = (this.layerFraction.surface * meanTempSurface +
            this.layerFraction.middle * meanTempMiddle +
            this.layerFraction.deep * meanTempDeep);
        const meanSalinity = (this.layerFraction.surface * meanSalinitySurface +
            this.layerFraction.middle * meanSalinityMiddle +
            this.layerFraction.deep * meanSalinityDeep);

        // Calculate observed warming
        const initialTempsSurface = this.initialTemperature.surface.slice(1, -1);
        const initialTempsMiddle = this.initialTemperature.middle.slice(1, -1);
        const initialTempsDeep = this.initialTemperature.deep.slice(1, -1);
        const initialMeanTempSurface = initialTempsSurface.reduce((a, b) => a + b) / initialTempsSurface.length;
        const initialMeanTempMiddle = initialTempsMiddle.reduce((a, b) => a + b) / initialTempsMiddle.length;
        const initialMeanTempDeep = initialTempsDeep.reduce((a, b) => a + b) / initialTempsDeep.length;
        const initialMeanTemp = (this.layerFraction.surface * initialMeanTempSurface +
            this.layerFraction.middle * initialMeanTempMiddle +
            this.layerFraction.deep * initialMeanTempDeep);
        const observedWarming = meanTemp - initialMeanTemp;

        // Expected warming from time series
        const expectedWarming = this.timeSeries.expectedWarming.length > 0 ?
            this.timeSeries.expectedWarming[this.timeSeries.expectedWarming.length - 1] : 0;

        // Warming rates
        const observedWarmingRate = this.elapsedDays > 0 ? observedWarming / this.elapsedDays : 0;
        const expectedWarmingRate = this.elapsedDays > 0 ? expectedWarming / this.elapsedDays : 0;

        return {
            meanTemp,
            meanTempSurface,
            meanTempMiddle,
            meanTempDeep,
            minTemp: Math.min(...tempsSurface, ...tempsMiddle, ...tempsDeep),
            maxTemp: Math.max(...tempsSurface, ...tempsMiddle, ...tempsDeep),
            meanSalinity,
            meanSalinitySurface,
            meanSalinityMiddle,
            meanSalinityDeep,
            minSalinity: Math.min(...salsSurface, ...salsMiddle, ...salsDeep),
            maxSalinity: Math.max(...salsSurface, ...salsMiddle, ...salsDeep),
            stratificationTemp_SM,
            stratificationTemp_MD,
            stratificationSalinity_SM,
            stratificationSalinity_MD,
            currentHeatFlux: this.getSurfaceHeatFlux(),
            cfl: this.calculateCFL(),
            observedWarming,
            expectedWarming,
            observedWarmingRate,
            expectedWarmingRate
        };
    }

    /**
     * Calculate CFL number for stability check
     */
    calculateCFL() {
        const maxU_surface = Math.max(...this.velocity.surface.map(Math.abs));
        const maxU_middle = Math.max(...this.velocity.middle.map(Math.abs));
        const maxU_deep = Math.max(...this.velocity.deep.map(Math.abs));
        const maxU = Math.max(maxU_surface, maxU_middle, maxU_deep);
        const dt = this.params.dt;
        return maxU * dt / this.dx;
    }

    /**
     * Get velocity components decomposed into tidal, river, and baroclinic
     * Returns arrays for each component showing surface, middle, and deep layer velocities
     */
    getVelocityComponents() {
        const tidal = { surface: [], middle: [], deep: [] };
        const river = { surface: [], middle: [], deep: [] };
        const baroclinic = { surface: [], middle: [], deep: [] };

        for (let i = 0; i < this.numBoxes; i++) {
            const H = this.depth[i];
            const W = this.width[i];
            const h_surface = this.layerFraction.surface * H;
            const h_middle = this.layerFraction.middle * H;
            const h_deep = this.layerFraction.deep * H;
            const A_surface = W * h_surface;
            const A_middle = W * h_middle;
            const A_deep = W * h_deep;

            // 1. RIVER COMPONENT (steady barotropic from discharge)
            // This is the depth-averaged velocity needed to transport the river discharge
            const u_river = -this.params.riverDischarge / (W * H);  // negative = seaward
            river.surface[i] = u_river;
            river.middle[i] = u_river;
            river.deep[i] = u_river;

            // 2. TIDAL COMPONENT (oscillating barotropic = total barotropic - river)
            const u_tidal = this.u_barotropic[i] - u_river;
            tidal.surface[i] = u_tidal;
            tidal.middle[i] = u_tidal;
            tidal.deep[i] = u_tidal;

            // 3. BAROCLINIC COMPONENT (density-driven exchange at TWO interfaces)
            // Surface: seaward flow from losing Q_ex_SM to middle
            // Middle: complex flow receiving from surface and giving to deep
            // Deep: landward flow from receiving Q_ex_MD from middle
            const Q_ex_SM = this.exchangeFlow.surface_middle[i];
            const Q_ex_MD = this.exchangeFlow.middle_deep[i];

            baroclinic.surface[i] = -Q_ex_SM / A_surface;
            baroclinic.middle[i] = +Q_ex_SM / A_middle - Q_ex_MD / A_middle;
            baroclinic.deep[i] = +Q_ex_MD / A_deep;
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
        this.velocity.surface.fill(0);
        this.velocity.middle.fill(0);
        this.velocity.deep.fill(0);
        this.exchangeFlow.surface_middle.fill(0);
        this.exchangeFlow.middle_deep.fill(0);
        this.setInitialProfiles();
        this.initialTemperature.surface = [...this.temperature.surface];
        this.initialTemperature.middle = [...this.temperature.middle];
        this.initialTemperature.deep = [...this.temperature.deep];
        this.initialSalinity.surface = [...this.salinity.surface];
        this.initialSalinity.middle = [...this.salinity.middle];
        this.initialSalinity.deep = [...this.salinity.deep];

        // Clear time series
        this.timeSeries = {
            time: [],
            meanTempSurface: [],
            meanTempMiddle: [],
            meanTempDeep: [],
            meanSalinitySurface: [],
            meanSalinityMiddle: [],
            meanSalinityDeep: [],
            stratificationTemp_SM: [],
            stratificationTemp_MD: [],
            stratificationSalinity_SM: [],
            stratificationSalinity_MD: [],
            heatFlux: [],
            expectedWarming: []
        };
        this.lastSampleTime = 0;
    }

    /**
     * Export current state to CSV
     */
    exportToCSV() {
        let csv = 'CSV Export - 3-Layer Estuary Simulator\n\n';

        // Spatial Profile
        csv += 'Spatial Profile (Current)\n';
        csv += 'Box,Distance (km),Depth (m),Width (m),';
        csv += 'T_surface (°C),T_middle (°C),T_deep (°C),';
        csv += 'S_surface (psu),S_middle (psu),S_deep (psu),';
        csv += 'U_surface (m/s),U_middle (m/s),U_deep (m/s),';
        csv += 'Q_ex_SM (m³/s),Q_ex_MD (m³/s)\n';

        for (let i = 0; i < this.numBoxes; i++) {
            const distance = (i * this.dx) / 1000;
            csv += `${i},${distance.toFixed(2)},${this.depth[i].toFixed(2)},${this.width[i].toFixed(0)},`;
            csv += `${this.temperature.surface[i].toFixed(3)},${this.temperature.middle[i].toFixed(3)},${this.temperature.deep[i].toFixed(3)},`;
            csv += `${this.salinity.surface[i].toFixed(3)},${this.salinity.middle[i].toFixed(3)},${this.salinity.deep[i].toFixed(3)},`;
            csv += `${this.velocity.surface[i].toFixed(4)},${this.velocity.middle[i].toFixed(4)},${this.velocity.deep[i].toFixed(4)},`;
            csv += `${this.exchangeFlow.surface_middle[i].toFixed(2)},${this.exchangeFlow.middle_deep[i].toFixed(2)}\n`;
        }

        csv += '\n';

        // Time Series
        csv += 'Time Series\n';
        csv += 'Time (days),T_surface (°C),T_middle (°C),T_deep (°C),';
        csv += 'S_surface (psu),S_middle (psu),S_deep (psu),';
        csv += 'ΔT_SM (°C),ΔT_MD (°C),ΔS_SM (psu),ΔS_MD (psu),Heat Flux (W/m²)\n';

        for (let i = 0; i < this.timeSeries.time.length; i++) {
            csv += `${this.timeSeries.time[i].toFixed(4)},`;
            csv += `${this.timeSeries.meanTempSurface[i].toFixed(3)},${this.timeSeries.meanTempMiddle[i].toFixed(3)},${this.timeSeries.meanTempDeep[i].toFixed(3)},`;
            csv += `${this.timeSeries.meanSalinitySurface[i].toFixed(3)},${this.timeSeries.meanSalinityMiddle[i].toFixed(3)},${this.timeSeries.meanSalinityDeep[i].toFixed(3)},`;
            csv += `${this.timeSeries.stratificationTemp_SM[i].toFixed(3)},${this.timeSeries.stratificationTemp_MD[i].toFixed(3)},`;
            csv += `${this.timeSeries.stratificationSalinity_SM[i].toFixed(3)},${this.timeSeries.stratificationSalinity_MD[i].toFixed(3)},`;
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
        a.download = `estuary_3layer_simulation_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}
