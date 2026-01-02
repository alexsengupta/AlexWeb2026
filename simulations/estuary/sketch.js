/**
 * sketch.js
 * Main p5.js sketch for 2-layer model - orchestrates the simulation
 */

let model;
let visualizer;
let controls;
let charts;
let isRunning = false; // Start paused
let isStarted = false; // Track if simulation has been started
let tempCanvas;
let salCanvas;

function setup() {
    // Don't create canvas in global mode - we'll use instance mode
    noCanvas();

    // Initialize 2-layer model
    model = new EstuaryModel_2layer(20);

    // Initialize visualizer (will create its own canvases)
    visualizer = new Visualizer_2layer(model);

    // Initialize charts
    charts = new Charts_2layer(model);

    // Initialize controls (pass visualizer and charts)
    controls = new Controls_2layer(model, visualizer, charts);

    // Wire up colorbar controls
    setupColorbarControls();

    // Set frame rate
    frameRate(30);
}

function setupColorbarControls() {
    // Temperature colorbar controls
    const tempAutoCheckbox = document.getElementById('temp-colorbar-auto');
    const tempMinSlider = document.getElementById('temp-colorbar-min');
    const tempMaxSlider = document.getElementById('temp-colorbar-max');
    const tempMinValueSpan = document.getElementById('temp-colorbar-min-value');
    const tempMaxValueSpan = document.getElementById('temp-colorbar-max-value');

    if (tempAutoCheckbox && tempMinSlider && tempMaxSlider) {
        tempAutoCheckbox.addEventListener('change', () => {
            tempMinSlider.disabled = tempAutoCheckbox.checked;
            tempMaxSlider.disabled = tempAutoCheckbox.checked;
            if (tempAutoCheckbox.checked) {
                visualizer.setTempColorbarAuto();
            } else {
                visualizer.setTempColorbarLimits(tempMinSlider.value, tempMaxSlider.value);
            }
        });

        tempMinSlider.addEventListener('input', () => {
            tempMinValueSpan.textContent = parseFloat(tempMinSlider.value).toFixed(1) + '°C';
            if (!tempAutoCheckbox.checked) {
                visualizer.setTempColorbarLimits(tempMinSlider.value, tempMaxSlider.value);
            }
        });

        tempMaxSlider.addEventListener('input', () => {
            tempMaxValueSpan.textContent = parseFloat(tempMaxSlider.value).toFixed(1) + '°C';
            if (!tempAutoCheckbox.checked) {
                visualizer.setTempColorbarLimits(tempMinSlider.value, tempMaxSlider.value);
            }
        });
    }

    // Salinity colorbar controls
    const salAutoCheckbox = document.getElementById('sal-colorbar-auto');
    const salMinSlider = document.getElementById('sal-colorbar-min');
    const salMaxSlider = document.getElementById('sal-colorbar-max');
    const salMinValueSpan = document.getElementById('sal-colorbar-min-value');
    const salMaxValueSpan = document.getElementById('sal-colorbar-max-value');

    if (salAutoCheckbox && salMinSlider && salMaxSlider) {
        salAutoCheckbox.addEventListener('change', () => {
            salMinSlider.disabled = salAutoCheckbox.checked;
            salMaxSlider.disabled = salAutoCheckbox.checked;
            if (salAutoCheckbox.checked) {
                visualizer.setSalColorbarAuto();
            } else {
                visualizer.setSalColorbarLimits(salMinSlider.value, salMaxSlider.value);
            }
        });

        salMinSlider.addEventListener('input', () => {
            salMinValueSpan.textContent = parseFloat(salMinSlider.value).toFixed(1) + ' psu';
            if (!salAutoCheckbox.checked) {
                visualizer.setSalColorbarLimits(salMinSlider.value, salMaxSlider.value);
            }
        });

        salMaxSlider.addEventListener('input', () => {
            salMaxValueSpan.textContent = parseFloat(salMaxSlider.value).toFixed(1) + ' psu';
            if (!salAutoCheckbox.checked) {
                visualizer.setSalColorbarLimits(salMinSlider.value, salMaxSlider.value);
            }
        });
    }
}

function draw() {
    // Adjust frame rate based on animation speed
    // Base frame rate of 30 fps, scaled by animationSpeed
    const targetFPS = 30 * model.params.animationSpeed;
    frameRate(targetFPS);

    // Update model if running
    if (isRunning) {
        model.update();
    }

    // Render visualization (draws to its own canvases)
    visualizer.render();

    // Update UI info
    updateInfo();
}

function updateInfo() {
    // Update charts every few frames for performance
    if (frameCount % 10 === 0) {
        charts.update();
    }
}

function keyPressed() {
    // Spacebar to pause/play
    if (key === ' ') {
        togglePause();
        return false; // prevent default
    }

    // 'R' to reset
    if (key === 'r' || key === 'R') {
        resetSimulation();
        return false;
    }
}

// Control functions (called by UI buttons)
function startSimulation() {
    isRunning = true;
    isStarted = true;
}

function togglePause() {
    if (!isStarted) {
        startSimulation();
    } else {
        isRunning = !isRunning;
    }
}

function resetSimulation() {
    model.reset();
    isRunning = false;
    isStarted = false;
    charts.reset();
}
