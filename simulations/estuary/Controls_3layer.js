/**
 * Controls_3layer.js
 * Creates and manages UI controls for 3-layer model parameters
 * Organized into 4 spatial columns: Ocean | Physical | Config | River
 */

class Controls_3layer {
    constructor(model, visualizer, charts) {
        this.model = model;
        this.visualizer = visualizer;
        this.charts = charts;
        this.controls = {};

        // Get container elements for each column
        this.oceanContainer = document.getElementById('ocean-sliders');
        this.physicalContainer = document.getElementById('physical-sliders');
        this.configContainer = document.getElementById('config-sliders');
        this.riverContainer = document.getElementById('river-sliders');
        this.controlButtonsTop = document.getElementById('control-buttons-top');
        // this.exportContainer = document.getElementById('export-container'); // REMOVED

        // Parameter descriptions
        this.paramDescriptions = {
            'tidalAmplitude': 'Height of the tidal wave at the ocean boundary.',
            'oceanTemp': 'Temperature of the incoming ocean water.',
            'oceanSalinity': 'Salinity of the ocean water.',
            'oceanMixing': 'Strength of tidal mixing at the mouth.',
            'riverDischarge': 'Volume of fresh water flowing in from the river.',
            'riverTemp': 'Temperature of the river water.',
            'riverSalinity': 'Salinity of the river inflow (usually 0).',
            'diffusivity': 'Rate at which properties spread horizontally.',
            'exchangeCoefficient': 'Rate of water exchange between the layers.',
            'verticalMixing': 'Rate of mixing across the density interface.',
            'frictionCoefficient': 'Drag force from the estuary bottom.',
            'heatFluxAmplitude': 'Maximum intensity of solar heating/cooling.',
            'boxLength': 'Length of each computational box segment.',
            'dt': 'Time step length for the simulation.',
            'animationSpeed': 'Multiplier for visualization playback speed.',
            'taperedGeometry': 'If checked, width decreases up-estuary.'
        };

        this.createControls();
        this.setupHelpModal();
    }

    setupHelpModal() {
        this.modal = document.getElementById('help-modal');
        this.modalTitle = document.getElementById('modal-title');
        this.modalDesc = document.getElementById('modal-description');
        const closeBtn = document.getElementById('modal-close');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.modal.style.display = 'none';
                this.modal.classList.remove('active');
            });
        }

        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.modal.style.display = 'none';
                    this.modal.classList.remove('active');
                }
            });
        }
    }

    openHelpModal(title, description) {
        if (this.modal) {
            this.modalTitle.textContent = title;
            this.modalDesc.textContent = description;
            this.modal.style.display = 'flex';
            setTimeout(() => this.modal.classList.add('active'), 10);
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
        this.addSlider('exchangeCoefficient', 'Exchange Coeff C_ex', 0, 0.05, 0.01, 0.001, '', this.physicalContainer);
        this.addSlider('verticalMixing', 'Vertical Mixing w_e', 0, 0.0001, 0.000001, 0.000001, 'm/s', this.physicalContainer);
        this.addSlider('frictionCoefficient', 'Bottom Friction r', 0, 0.002, 0.0002, 0.0001, 's⁻¹', this.physicalContainer);
        this.addSlider('heatFluxAmplitude', 'Heat Flux Amplitude', 0, 500, 200, 10, 'W/m²', this.physicalContainer);

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
        // Start/Pause button
        const startPauseButton = document.createElement('button');
        startPauseButton.textContent = 'Start';
        startPauseButton.className = 'control-button primary-button';
        startPauseButton.addEventListener('click', () => {
            if (isStarted) {
                isRunning = !isRunning;
                startPauseButton.textContent = isRunning ? 'Pause' : 'Resume';
            } else {
                startSimulation();
                startPauseButton.textContent = 'Pause';
            }
        });
        this.controlButtonsTop.appendChild(startPauseButton);
        this.startPauseButton = startPauseButton;

        // Reset button
        const resetButton = document.createElement('button');
        resetButton.textContent = 'Reset';
        resetButton.className = 'control-button';
        resetButton.addEventListener('click', () => {
            resetSimulation();
            this.startPauseButton.textContent = 'Start';
        });
        this.controlButtonsTop.appendChild(resetButton);
    }

    addSlider(param, label, min, max, defaultValue, step, unit, container, extraCallback = null) {
        // Create container for this control
        const controlDiv = document.createElement('div');
        controlDiv.className = 'control-item';
        container.appendChild(controlDiv);

        // Header row: Label + Help (?) + Value
        const headerDiv = document.createElement('div');
        headerDiv.className = 'control-header';
        controlDiv.appendChild(headerDiv);

        // Left side: Label + Icon
        const labelGroup = document.createElement('span');
        labelGroup.className = 'control-label-group';
        headerDiv.appendChild(labelGroup);

        const labelSpan = document.createElement('span');
        labelSpan.className = 'control-label';
        labelSpan.textContent = label;
        labelGroup.appendChild(labelSpan);

        // Help icon
        if (this.paramDescriptions[param]) {
            const helpSpan = document.createElement('span');
            helpSpan.className = 'help-icon';
            helpSpan.textContent = '?';
            labelGroup.appendChild(helpSpan);

            helpSpan.addEventListener('click', () => {
                this.openHelpModal(label, this.paramDescriptions[param]);
            });
        }

        // Right side: Value
        const valueSpan = document.createElement('span');
        valueSpan.className = 'control-value';
        valueSpan.textContent = `${defaultValue} ${unit}`;
        headerDiv.appendChild(valueSpan);

        // Slider
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = min;
        slider.max = max;
        slider.value = defaultValue;
        slider.step = step;
        slider.className = 'slider';
        controlDiv.appendChild(slider);

        // Update callback
        slider.addEventListener('input', () => {
            const value = parseFloat(slider.value);
            this.model.params[param] = value;
            valueSpan.textContent = `${value} ${unit}`;

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

    addCheckbox(param, label, defaultValue, container) {
        // Create container
        const controlDiv = document.createElement('div');
        controlDiv.className = 'control-item';
        container.appendChild(controlDiv);

        // Create label element
        const labelElement = document.createElement('label');
        labelElement.className = 'checkbox';
        controlDiv.appendChild(labelElement);

        // Checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = defaultValue;
        labelElement.appendChild(checkbox);

        // Label text
        const labelText = document.createTextNode(label);
        labelElement.appendChild(labelText);

        // Update callback
        checkbox.addEventListener('change', () => {
            this.model.params[param] = checkbox.checked;
            this.model.updateGeometry();
        });

        this.controls[param] = checkbox;
    }



    onBoundaryChange() {
        // If simulation hasn't started, update initial temperature and salinity profiles for THREE LAYERS
        if (!isStarted) {
            this.model.setInitialProfiles();
            this.model.initialTemperature.surface = [...this.model.temperature.surface];
            this.model.initialTemperature.middle = [...this.model.temperature.middle];
            this.model.initialTemperature.deep = [...this.model.temperature.deep];
            this.model.initialSalinity.surface = [...this.model.salinity.surface];
            this.model.initialSalinity.middle = [...this.model.salinity.middle];
            this.model.initialSalinity.deep = [...this.model.salinity.deep];
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
}
