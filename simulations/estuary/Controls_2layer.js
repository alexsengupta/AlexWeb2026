/**
 * Controls_2layer.js
 * Creates and manages UI controls (sliders, toggles) for 2-layer model parameters
 */

class Controls_2layer {
    constructor(model, visualizer, charts) {
        this.model = model;
        this.visualizer = visualizer;
        this.charts = charts;
        this.controls = {};

        // Containers for the four spatial columns
        this.oceanContainer = select('#ocean-sliders');
        this.physicalContainer = select('#physical-sliders');
        this.configContainer = select('#config-sliders');
        this.riverContainer = select('#river-sliders');

        // Parameter descriptions for help tooltips
        this.paramDescriptions = {
            'tidalAmplitude': 'Height of the tidal wave at the ocean boundary.',
            'oceanTemp': 'Temperature of the incoming ocean water.',
            'oceanSalinity': 'Salinity of the ocean water.',
            'oceanMixing': 'Strength of tidal mixing at the mouth.',
            'riverDischarge': 'Volume of fresh water flowing in from the river.',
            'riverTemp': 'Temperature of the river water.',
            'riverSalinity': 'Salinity of the river inflow (usually 0).',
            'diffusivity': 'Rate at which properties spread horizontally.',
            'heatFluxAmplitude': 'Maximum intensity of solar heating/cooling.',
            'exchangeCoefficient': 'Rate of water exchange between the layers.',
            'verticalMixing': 'Rate of mixing across the density interface.',
            'frictionCoefficient': 'Drag force from the estuary bottom.',
            'boxLength': 'Length of each computational box segment.',
            'dt': 'Time step length for the simulation.',
            'animationSpeed': 'Multiplier for visualization playback speed.',
            'taperedGeometry': 'If checked, width decreases up-estuary.'
        };

        this.createControls();
        this.setupHelpModal();
    }

    setupHelpModal() {
        // Get modal elements
        this.modal = select('#help-modal');
        this.modalTitle = select('#modal-title');
        this.modalDesc = select('#modal-description');
        const closeBtn = select('#modal-close');

        // Close button handler
        if (closeBtn) {
            closeBtn.mousePressed(() => {
                this.modal.style('display', 'none');
                this.modal.removeClass('active');
            });
        }

        // Click outside to close
        if (this.modal) {
            this.modal.mousePressed((e) => {
                if (e.target === this.modal.elt) {
                    this.modal.style('display', 'none');
                    this.modal.removeClass('active');
                }
            });
        }
    }

    openHelpModal(title, description) {
        if (this.modal) {
            this.modalTitle.html(title);
            this.modalDesc.html(description);
            this.modal.style('display', 'flex');
            // Small delay to allow display:flex to apply before opacity transition
            setTimeout(() => this.modal.addClass('active'), 10);
        }
    }

    createControls() {
        // Control buttons at top
        this.addControlButtons();

        // === OCEAN (MOUTH) CONTROLS ===
        this.addSlider('tidalAmplitude', 'Tidal Amplitude', 0, 3, 1, 0.1, 'm', this.oceanContainer);
        this.addSlider('oceanTemp', 'Ocean Temperature', 5, 30, 18, 0.5, '°C', this.oceanContainer,
            () => this.onBoundaryChange());
        this.addSlider('oceanSalinity', 'Ocean Salinity', 0, 40, 35, 0.5, 'psu', this.oceanContainer,
            () => this.onBoundaryChange());
        this.addSlider('oceanMixing', 'Ocean Mixing (BC)', 0, 1, 0.5, 0.1, '', this.oceanContainer);

        // === PHYSICAL PARAMETERS ===
        this.addSlider('diffusivity', 'Horizontal Diffusivity', 1, 1000, 50, 10, 'm²/s', this.physicalContainer);
        this.addSlider('heatFluxAmplitude', 'Heat Flux Amplitude', 0, 500, 200, 10, 'W/m²', this.physicalContainer);
        this.addSlider('exchangeCoefficient', 'Exchange Coeff C_ex', 0, 0.05, 0.01, 0.001, '', this.physicalContainer);
        this.addSlider('verticalMixing', 'Vertical Mixing w_e', 0, 0.001, 0.00003, 0.00001, 'm/s', this.physicalContainer);
        this.addSlider('frictionCoefficient', 'Bottom Friction r', 0, 0.002, 0.0002, 0.0001, 's⁻¹', this.physicalContainer);

        // === MODEL CONFIGURATION ===
        this.addSlider('boxLength', 'Box Length', 1000, 10000, 2500, 500, 'm', this.configContainer,
            () => this.onBoxLengthChange());
        this.addSlider('dt', 'Time Step', 50, 300, 200, 10, 'seconds', this.configContainer);
        this.addSlider('animationSpeed', 'Animation Speed', 0.25, 5, 1, 0.25, 'x', this.configContainer);
        this.addCheckbox('taperedGeometry', 'Tapered Geometry', false, this.configContainer);



        // === RIVER (HEAD) CONTROLS ===
        this.addSlider('riverDischarge', 'River Discharge', 0, 200, 30, 10, 'm³/s', this.riverContainer);
        this.addSlider('riverTemp', 'River Temperature', 5, 30, 12, 0.5, '°C', this.riverContainer,
            () => this.onBoundaryChange());
        this.addSlider('riverSalinity', 'River Salinity', 0, 40, 0, 0.5, 'psu', this.riverContainer,
            () => this.onBoundaryChange());
    }

    addControlButtons() {
        // Button container (in the header)
        const buttonContainer = select('#control-buttons-top');

        // Start/Pause button
        this.startPauseButton = createButton('Start');
        this.startPauseButton.class('control-button primary-button');
        this.startPauseButton.parent(buttonContainer);
        this.startPauseButton.mousePressed(() => {
            if (isStarted) {
                isRunning = !isRunning;
                this.startPauseButton.html(isRunning ? 'Pause' : 'Resume');
            } else {
                startSimulation();
                this.startPauseButton.html('Pause');
            }
        });

        // Reset button
        const resetButton = createButton('Reset');
        resetButton.class('control-button');
        resetButton.parent(buttonContainer);
        resetButton.mousePressed(() => {
            resetSimulation();
            this.startPauseButton.html('Start');
        });
    }

    onBoundaryChange() {
        // If simulation hasn't started, update initial temperature and salinity profiles
        if (!isStarted) {
            this.model.setInitialProfiles();
            this.model.initialTemperature.upper = [...this.model.temperature.upper];
            this.model.initialTemperature.lower = [...this.model.temperature.lower];
            this.model.initialSalinity.upper = [...this.model.salinity.upper];
            this.model.initialSalinity.lower = [...this.model.salinity.lower];
            // Update the charts to show the new initial profiles
            if (this.charts) {
                this.charts.updateTempProfileChart();
                this.charts.updateSalinityProfileChart();
            }
        }
    }

    onBoxLengthChange() {
        // Update the domain length calculation
        this.model.updateDomainLength();

        // Show info about new estuary length
        const totalKm = (this.model.totalLength / 1000).toFixed(1);
        console.log(`Estuary length updated: ${totalKm} km (${this.model.numBoxes} boxes × ${this.model.params.boxLength}m)`);
    }

    addSlider(param, label, min, max, defaultValue, step, unit, container, extraCallback = null) {
        // Support old signature (without container parameter)
        if (typeof container === 'function') {
            extraCallback = container;
            container = this.globalContainer;
        }

        // Create container for this control
        const controlDiv = createDiv('');
        controlDiv.class('control-item');
        controlDiv.parent(container);

        // Header row: Label + Help (?) + Value
        const headerDiv = createDiv('');
        headerDiv.class('control-header');
        headerDiv.parent(controlDiv);

        // Left side: Label + Icon
        const labelGroup = createSpan('');
        labelGroup.class('control-label-group');
        labelGroup.parent(headerDiv);

        const labelSpan = createSpan(`${label}`);
        labelSpan.class('control-label');
        labelSpan.parent(labelGroup);

        // Help icon
        if (this.paramDescriptions[param]) {
            const helpSpan = createSpan('?');
            helpSpan.class('help-icon');
            // Remove native tooltip
            // helpSpan.attribute('title', this.paramDescriptions[param]); 
            helpSpan.parent(labelGroup);

            // Add click handler for modal
            helpSpan.mouseClicked(() => {
                this.openHelpModal(label, this.paramDescriptions[param]);
            });
        }

        // Right side: Value
        const valueSpan = createSpan(`${defaultValue} ${unit}`);
        valueSpan.class('control-value');
        valueSpan.parent(headerDiv);

        // Slider
        const slider = createSlider(min, max, defaultValue, step);
        slider.parent(controlDiv);
        slider.class('slider');

        // Update callback
        slider.input(() => {
            const value = slider.value();
            this.model.params[param] = value;
            valueSpan.html(`${value} ${unit}`);

            // Update geometry if needed
            if (param === 'taperedGeometry') {
                this.model.updateGeometry();
            }

            // Call extra callback if provided
            if (extraCallback) {
                extraCallback();
            }
        });

        this.controls[param] = { slider, valueSpan, unit };
    }

    addToggle(param, label, options, values, container = null) {
        if (!container) container = this.globalContainer;

        // Create container
        const controlDiv = createDiv('');
        controlDiv.class('control-item');
        controlDiv.parent(container);

        // Label
        const labelSpan = createSpan(`${label}: `);
        labelSpan.parent(controlDiv);

        // Create select dropdown
        const select = createSelect();
        select.parent(controlDiv);
        select.class('toggle-select');

        for (let i = 0; i < options.length; i++) {
            select.option(options[i], values[i]);
        }

        // Set initial value based on param type
        if (param === 'displayField') {
            select.value(this.visualizer.displayField);
        } else {
            select.value(this.model.params[param]);
        }

        // Update callback
        select.changed(() => {
            if (param === 'displayField') {
                // Update visualizer display field
                this.visualizer.displayField = select.value();
            } else {
                // Update model parameter
                this.model.params[param] = select.value();
            }
        });

        this.controls[param] = select;
    }

    addCheckbox(param, label, defaultValue, container = null) {
        if (!container) container = this.globalContainer;

        // Create container
        const controlDiv = createDiv('');
        controlDiv.class('control-item');
        controlDiv.parent(container);

        // Checkbox
        const checkbox = createCheckbox(label, defaultValue);
        checkbox.parent(controlDiv);
        checkbox.class('checkbox');

        // Update callback
        checkbox.changed(() => {
            this.model.params[param] = checkbox.checked();
            this.model.updateGeometry();
        });

        this.controls[param] = checkbox;
    }

    addButton(label, callback, container = null) {
        if (!container) container = this.globalContainer;

        // Create container
        const controlDiv = createDiv('');
        controlDiv.class('control-item');
        controlDiv.parent(container);

        // Button
        const button = createButton(label);
        button.parent(controlDiv);
        button.class('control-button');
        button.mousePressed(callback);
    }
}
