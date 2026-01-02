/**
 * Visualizer_2layer.js
 * Handles rendering of dual estuary views (temperature and salinity)
 */

class Visualizer_2layer {
    constructor(model) {
        this.model = model;

        // Colorbar limits for temperature and salinity (separate)
        this.tempColorbar = { min: null, max: null, auto: true };
        this.salColorbar = { min: null, max: null, auto: true };

        // Layout parameters for each view
        this.margin = { left: 60, right: 120, top: 60, bottom: 5 };
        this.estuaryHeight = 100; // visual height of estuary boxes

        // Canvas dimensions
        this.canvasWidth = 1000;
        this.canvasHeight = 200; // Much shorter - just enough for the visualization

        // Create two separate canvases
        this.tempCanvas = createGraphics(this.canvasWidth, this.canvasHeight);
        this.salCanvas = createGraphics(this.canvasWidth, this.canvasHeight);

        // Append to DOM
        document.getElementById('temp-canvas-container').appendChild(this.tempCanvas.canvas);
        document.getElementById('sal-canvas-container').appendChild(this.salCanvas.canvas);

        // Style the canvases
        this.tempCanvas.canvas.style.display = 'block';
        this.tempCanvas.canvas.style.borderRadius = '6px';
        this.salCanvas.canvas.style.display = 'block';
        this.salCanvas.canvas.style.borderRadius = '6px';
    }

    render() {
        // Render temperature view
        this.renderTemperatureView();

        // Render salinity view
        this.renderSalinityView();
    }

    renderTemperatureView() {
        const g = this.tempCanvas;

        // Background
        g.background(250);

        // Title and time
        g.fill(0);
        g.textAlign(CENTER, TOP);
        g.textSize(14);
        g.textStyle(BOLD);
        g.text('Temperature (°C)', this.canvasWidth / 2, 10);
        g.textStyle(NORMAL);
        g.textSize(11);
        g.text(`Time: ${this.model.elapsedDays.toFixed(2)} days`, this.canvasWidth / 2, 30);

        // Draw estuary boxes
        this.drawEstuaryBoxes('temperature', g);

        // Draw heat flux arrows above boxes
        this.drawHeatFluxArrows(g);

        // Draw velocity vectors
        this.drawVelocityVectors('temperature', g);
    }

    renderSalinityView() {
        const g = this.salCanvas;

        // Background
        g.background(245);

        // Title
        g.fill(0);
        g.textAlign(CENTER, TOP);
        g.textSize(14);
        g.textStyle(BOLD);
        g.text('Salinity (psu)', this.canvasWidth / 2, 10);
        g.textStyle(NORMAL);

        // Draw estuary boxes
        this.drawEstuaryBoxes('salinity', g);

        // Draw sea level line
        this.drawSeaLevelLine(g);

        // Draw velocity vectors
        this.drawVelocityVectors('salinity', g);
    }

    drawSeaLevelLine(g) {
        const numBoxes = this.model.numBoxes;
        const availableWidth = this.canvasWidth - this.margin.left - this.margin.right;

        // Calculate box widths for tapered geometry
        const totalWidth = this.model.width.reduce((a, b) => a + b, 0);
        const boxWidths = this.model.width.map(w => (w / totalWidth) * availableWidth);

        const estuaryY = this.margin.top + this.estuaryHeight / 2;
        const yTop = estuaryY - this.estuaryHeight / 2;

        g.push();
        g.stroke(0, 100, 200, 150);
        g.strokeWeight(2);
        g.noFill();

        g.beginShape();
        let currentX = this.margin.left;
        for (let i = 0; i < numBoxes; i++) {
            const boxWidth = boxWidths[i];
            const x = currentX + boxWidth / 2;
            const eta = this.model.eta[i];
            // Exaggerate for visibility
            const etaScale = 20;
            const y = yTop - eta * etaScale;
            g.vertex(x, y);
            currentX += boxWidth;
        }
        g.endShape();

        g.pop();
    }

    drawEstuaryBoxes(field, g) {
        const numBoxes = this.model.numBoxes;
        const availableWidth = this.canvasWidth - this.margin.left - this.margin.right;
        const boxSpacing = 1;

        // For tapered geometry, calculate box widths proportional to model.width
        // For uniform geometry, all boxes have equal width
        const totalWidth = this.model.width.reduce((a, b) => a + b, 0);
        const boxWidths = this.model.width.map(w => (w / totalWidth) * availableWidth);

        // Center vertically in the view
        const estuaryY = this.margin.top + this.estuaryHeight / 2;

        // Track cumulative x position
        let currentX = this.margin.left;

        for (let i = 0; i < numBoxes; i++) {
            const boxWidth = boxWidths[i];

            // Get values for this box
            const valueUpper = field === 'temperature' ?
                this.model.temperature.upper[i] : this.model.salinity.upper[i];
            const valueLower = field === 'temperature' ?
                this.model.temperature.lower[i] : this.model.salinity.lower[i];

            // Layer heights - scale with depth for tapered geometry
            const depthScale = this.model.depth[i] / 10; // Normalize to default depth of 10m
            const scaledHeight = this.estuaryHeight * depthScale;
            const upperHeight = scaledHeight * this.model.layerFraction.upper;
            const lowerHeight = scaledHeight * this.model.layerFraction.lower;

            // Vertical position - align tops (water surface is largely flat)
            const yTop = estuaryY - this.estuaryHeight / 2;

            // Draw upper layer
            g.push();
            const colorUpper = this.valueToColor(valueUpper, field);
            g.fill(colorUpper[0], colorUpper[1], colorUpper[2]);
            g.stroke(100);
            g.strokeWeight(0.5);
            g.rect(currentX, yTop, boxWidth - boxSpacing, upperHeight);
            g.pop();

            // Draw lower layer
            g.push();
            const colorLower = this.valueToColor(valueLower, field);
            g.fill(colorLower[0], colorLower[1], colorLower[2]);
            g.stroke(100);
            g.strokeWeight(0.5);
            g.rect(currentX, yTop + upperHeight, boxWidth - boxSpacing, lowerHeight);
            g.pop();

            // Draw interface line
            g.push();
            g.stroke(50);
            g.strokeWeight(1);
            g.line(currentX, yTop + upperHeight, currentX + boxWidth - boxSpacing, yTop + upperHeight);
            g.pop();

            currentX += boxWidth;
        }

        // Draw labels
        g.push();
        g.fill(0);
        g.noStroke();
        g.textAlign(CENTER, CENTER);
        g.textSize(10);
        g.text('OCEAN', this.margin.left / 2, estuaryY);
        g.text('RIVER', this.canvasWidth - this.margin.right / 2, estuaryY);
        g.pop();
    }

    drawHeatFluxArrows(g) {
        const numBoxes = this.model.numBoxes;
        const availableWidth = this.canvasWidth - this.margin.left - this.margin.right;

        // Calculate box widths for tapered geometry
        const totalWidth = this.model.width.reduce((a, b) => a + b, 0);
        const boxWidths = this.model.width.map(w => (w / totalWidth) * availableWidth);

        const estuaryY = this.margin.top + this.estuaryHeight / 2;
        const yTop = estuaryY - this.estuaryHeight / 2;

        const heatFlux = this.model.getSurfaceHeatFlux();
        const maxArrowLength = 25; // pixels

        let currentX = this.margin.left;
        for (let i = 0; i < numBoxes; i++) {
            const boxWidth = boxWidths[i];
            const x = currentX + boxWidth / 2;

            // Arrow length proportional to heat flux
            // Normalize by typical max value
            const arrowLength = constrain(heatFlux / 500 * maxArrowLength, -maxArrowLength, maxArrowLength);

            if (Math.abs(arrowLength) > 2) {
                this.drawHeatArrow(g, x, yTop - 5, arrowLength);
            }

            currentX += boxWidth;
        }

        // Legend for heat flux
        g.push();
        g.fill(0);
        g.textAlign(LEFT, TOP);
        g.textSize(9);
        g.text(`Heat Flux: ${heatFlux.toFixed(0)} W/m²`, this.margin.left, yTop - 30);
        g.pop();
    }

    drawHeatArrow(g, x, y, length) {
        g.push();

        // Color based on sign
        if (length > 0) {
            g.fill(255, 100, 100); // Heating = red
            g.stroke(255, 100, 100);
        } else {
            g.fill(100, 100, 255); // Cooling = blue
            g.stroke(100, 100, 255);
        }

        g.strokeWeight(2);

        // Arrow shaft
        const y2 = y - length;
        g.line(x, y, x, y2);

        // Arrowhead
        const arrowSize = 4;
        if (length > 0) {
            // Upward arrow
            g.triangle(x, y2, x - arrowSize, y2 + arrowSize, x + arrowSize, y2 + arrowSize);
        } else {
            // Downward arrow
            g.triangle(x, y2, x - arrowSize, y2 - arrowSize, x + arrowSize, y2 - arrowSize);
        }

        g.pop();
    }

    drawVelocityVectors(field, g) {
        const numBoxes = this.model.numBoxes;
        const availableWidth = this.canvasWidth - this.margin.left - this.margin.right;

        // Calculate box widths for tapered geometry
        const totalWidth = this.model.width.reduce((a, b) => a + b, 0);
        const boxWidths = this.model.width.map(w => (w / totalWidth) * availableWidth);

        const estuaryY = this.margin.top + this.estuaryHeight / 2;

        // Velocity scale (pixels per m/s)
        const velScale = 30;

        let currentX = this.margin.left;
        for (let i = 0; i < numBoxes; i++) {
            const boxWidth = boxWidths[i];
            const x = currentX + boxWidth / 2;

            // Layer heights - scale with depth for tapered geometry
            const depthScale = this.model.depth[i] / 10;
            const scaledHeight = this.estuaryHeight * depthScale;
            const upperHeight = scaledHeight * this.model.layerFraction.upper;
            const yTop = estuaryY - this.estuaryHeight / 2;

            // Upper layer velocity
            const velUpper = this.model.velocity.upper[i];
            const yUpper = yTop + upperHeight / 2;
            this.drawVelocityArrow(g, x, yUpper, velUpper, velScale, true);

            // Lower layer velocity
            const velLower = this.model.velocity.lower[i];
            const yLower = yTop + upperHeight + (scaledHeight - upperHeight) / 2;
            this.drawVelocityArrow(g, x, yLower, velLower, velScale, false);

            currentX += boxWidth;
        }
    }

    drawVelocityArrow(g, x, y, velocity, scale, isUpper) {
        const arrowLength = velocity * scale;

        // Skip if too small
        if (Math.abs(arrowLength) < 3) return;

        g.push();
        g.stroke(255, 255, 255, 200);
        g.strokeWeight(1.5);
        g.fill(255, 255, 255, 200);

        // Arrow shaft
        const endX = x + arrowLength;
        g.line(x, y, endX, y);

        // Arrowhead
        const arrowSize = 4;
        const direction = Math.sign(velocity);
        g.triangle(
            endX, y,
            endX - direction * arrowSize, y - arrowSize,
            endX - direction * arrowSize, y + arrowSize
        );

        g.pop();
    }

    valueToColor(value, field) {
        if (field === 'temperature') {
            return this.tempToColor(value);
        } else {
            return this.salinityToColor(value);
        }
    }

    tempToColor(temp) {
        const range = this.getTempColorRange();
        const t = constrain(map(temp, range.min, range.max, 0, 1), 0, 1);

        // Blue → Cyan → Green → Yellow → Red
        let r, g, b;
        if (t < 0.25) {
            const localT = map(t, 0, 0.25, 0, 1);
            r = 0;
            g = localT * 255;
            b = 255;
        } else if (t < 0.5) {
            const localT = map(t, 0.25, 0.5, 0, 1);
            r = 0;
            g = 255;
            b = (1 - localT) * 255;
        } else if (t < 0.75) {
            const localT = map(t, 0.5, 0.75, 0, 1);
            r = localT * 255;
            g = 255;
            b = 0;
        } else {
            const localT = map(t, 0.75, 1.0, 0, 1);
            r = 255;
            g = (1 - localT) * 255;
            b = 0;
        }

        return [r, g, b];
    }

    salinityToColor(salinity) {
        const range = this.getSalColorRange();
        const t = constrain(map(salinity, range.min, range.max, 0, 1), 0, 1);

        // Blue → Cyan → Yellow → Brown (Fresh → Salty)
        // t=0: Blue (0,0,255)
        // t=0.33: Cyan (0,255,255)
        // t=0.67: Yellow (255,255,0)
        // t=1.0: Brown (139,69,19)
        let r, g, b;
        if (t < 0.33) {
            // Blue to Cyan
            const localT = map(t, 0, 0.33, 0, 1);
            r = 0;
            g = localT * 255;
            b = 255;
        } else if (t < 0.67) {
            // Cyan to Yellow
            const localT = map(t, 0.33, 0.67, 0, 1);
            r = localT * 255;
            g = 255;
            b = (1 - localT) * 255;
        } else {
            // Yellow to Brown
            const localT = map(t, 0.67, 1.0, 0, 1);
            r = 255 - (255 - 139) * localT;
            g = 255 - (255 - 69) * localT;
            b = 0 + (19) * localT;
        }

        return [r, g, b];
    }

    // Temperature colorbar controls
    setTempColorbarLimits(min, max) {
        this.tempColorbar.auto = false;
        this.tempColorbar.min = parseFloat(min);
        this.tempColorbar.max = parseFloat(max);
    }

    setTempColorbarAuto() {
        this.tempColorbar.auto = true;
    }

    // Salinity colorbar controls
    setSalColorbarLimits(min, max) {
        this.salColorbar.auto = false;
        this.salColorbar.min = parseFloat(min);
        this.salColorbar.max = parseFloat(max);
    }

    setSalColorbarAuto() {
        this.salColorbar.auto = true;
    }

    getTempColorRange() {
        if (!this.tempColorbar.auto) {
            return { min: this.tempColorbar.min, max: this.tempColorbar.max };
        }
        const minBoundary = Math.min(this.model.params.oceanTemp, this.model.params.riverTemp);
        const maxBoundary = Math.max(this.model.params.oceanTemp, this.model.params.riverTemp);
        return { min: minBoundary - 2, max: maxBoundary + 2 };
    }

    getSalColorRange() {
        if (!this.salColorbar.auto) {
            return { min: this.salColorbar.min, max: this.salColorbar.max };
        }
        const minBoundary = Math.min(this.model.params.oceanSalinity, this.model.params.riverSalinity);
        const maxBoundary = Math.max(this.model.params.oceanSalinity, this.model.params.riverSalinity);
        const range = maxBoundary - minBoundary;
        return { min: Math.max(0, minBoundary - range * 0.1), max: maxBoundary + range * 0.1 };
    }
}
