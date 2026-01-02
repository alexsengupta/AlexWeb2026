/**
 * Charts_3layer.js
 * Manages Chart.js visualizations for temperature, salinity, and velocity components (3-layer model)
 */

class Charts_3layer {
    constructor(model) {
        this.model = model;
        this.tempProfileChart = null;
        this.salProfileChart = null;
        this.tidalVelocityChart = null;
        this.riverVelocityChart = null;
        this.baroclinicVelocityChart = null;

        // Track recent velocity data for smoothed y-axis limits
        this.velocityHistory = {
            tidal: { surface: [], middle: [], deep: [] },
            river: { surface: [], middle: [], deep: [] },
            baroclinic: { surface: [], middle: [], deep: [] }
        };
        this.maxHistoryPoints = 100; // Keep last 100 updates (~1 day at typical update rates)

        this.createCharts();
    }

    createCharts() {
        // Temperature Profile Chart
        const tempProfileCtx = document.getElementById('tempProfileChart').getContext('2d');
        this.tempProfileChart = new Chart(tempProfileCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Surface Layer',
                        data: [],
                        borderColor: 'rgb(255, 99, 71)',
                        backgroundColor: 'rgba(255, 99, 71, 0.1)',
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    },
                    {
                        label: 'Middle Layer',
                        data: [],
                        borderColor: 'rgb(255, 165, 0)',
                        backgroundColor: 'rgba(255, 165, 0, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    },
                    {
                        label: 'Deep Layer',
                        data: [],
                        borderColor: 'rgb(30, 144, 255)',
                        backgroundColor: 'rgba(30, 144, 255, 0.1)',
                        borderDash: [10, 5],
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Temperature Profile'
                    },
                    legend: {
                        display: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Temperature (°C)'
                        }
                    }
                }
            }
        });

        // Salinity Profile Chart
        const salProfileCtx = document.getElementById('salProfileChart').getContext('2d');
        this.salProfileChart = new Chart(salProfileCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Surface Layer',
                        data: [],
                        borderColor: 'rgb(139, 69, 19)',
                        backgroundColor: 'rgba(139, 69, 19, 0.1)',
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    },
                    {
                        label: 'Middle Layer',
                        data: [],
                        borderColor: 'rgb(218, 165, 32)',
                        backgroundColor: 'rgba(218, 165, 32, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    },
                    {
                        label: 'Deep Layer',
                        data: [],
                        borderColor: 'rgb(0, 119, 190)',
                        backgroundColor: 'rgba(0, 119, 190, 0.1)',
                        borderDash: [10, 5],
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Salinity Profile'
                    },
                    legend: {
                        display: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Salinity (psu)'
                        }
                    }
                }
            }
        });

        // Tidal Velocity Component Chart
        const tidalCtx = document.getElementById('tidalVelocityChart').getContext('2d');
        this.tidalVelocityChart = new Chart(tidalCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Surface Layer',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Middle Layer',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Deep Layer',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        borderDash: [10, 5],
                        tension: 0.1,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Tidal Velocity Component'
                    },
                    legend: {
                        display: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Velocity (m/s)'
                        }
                    }
                }
            }
        });

        // River Velocity Component Chart
        const riverCtx = document.getElementById('riverVelocityChart').getContext('2d');
        this.riverVelocityChart = new Chart(riverCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Surface Layer',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Middle Layer',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Deep Layer',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderDash: [10, 5],
                        tension: 0.1,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'River Velocity Component'
                    },
                    legend: {
                        display: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Velocity (m/s)'
                        }
                    }
                }
            }
        });

        // Baroclinic Velocity Component Chart
        const baroclinicCtx = document.getElementById('baroclinicVelocityChart').getContext('2d');
        this.baroclinicVelocityChart = new Chart(baroclinicCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Surface Layer (seaward)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Middle Layer',
                        data: [],
                        borderColor: 'rgb(255, 159, 64)',
                        backgroundColor: 'rgba(255, 159, 64, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Deep Layer (landward)',
                        data: [],
                        borderColor: 'rgb(153, 102, 255)',
                        backgroundColor: 'rgba(153, 102, 255, 0.1)',
                        tension: 0.1,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Baroclinic (Exchange) Velocity Component'
                    },
                    legend: {
                        display: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Velocity (m/s)'
                        }
                    }
                }
            }
        });
    }

    update() {
        this.updateTempProfileChart();
        this.updateSalinityProfileChart();
        this.updateVelocityCharts();
    }

    updateTempProfileChart() {
        // Create distance array (km)
        const distances = [];
        for (let i = 0; i < this.model.numBoxes; i++) {
            distances.push(((i * this.model.dx) / 1000).toFixed(1));
        }

        // Update Temperature Profile Chart
        this.tempProfileChart.data.labels = distances;
        this.tempProfileChart.data.datasets[0].data = [...this.model.temperature.surface];
        this.tempProfileChart.data.datasets[1].data = [...this.model.temperature.middle];
        this.tempProfileChart.data.datasets[2].data = [...this.model.temperature.deep];
        this.tempProfileChart.update('none');
    }

    updateSalinityProfileChart() {
        // Create distance array (km)
        const distances = [];
        for (let i = 0; i < this.model.numBoxes; i++) {
            distances.push(((i * this.model.dx) / 1000).toFixed(1));
        }

        // Update Salinity Profile Chart
        this.salProfileChart.data.labels = distances;
        this.salProfileChart.data.datasets[0].data = [...this.model.salinity.surface];
        this.salProfileChart.data.datasets[1].data = [...this.model.salinity.middle];
        this.salProfileChart.data.datasets[2].data = [...this.model.salinity.deep];
        this.salProfileChart.update('none');
    }

    updateVelocityCharts() {
        // Get velocity components from model
        const components = this.model.getVelocityComponents();

        // Create distance array (km)
        const distances = [];
        for (let i = 0; i < this.model.numBoxes; i++) {
            distances.push(((i * this.model.dx) / 1000).toFixed(1));
        }

        // Track velocity extremes for smoothed y-axis limits
        this.trackVelocityHistory(components);

        // Calculate smoothed y-axis limits
        const tidalLimits = this.getSmoothedYLimits('tidal');
        const riverLimits = this.getSmoothedYLimits('river');
        const baroclinicLimits = this.getSmoothedYLimits('baroclinic');

        // Update Tidal Velocity Chart
        this.tidalVelocityChart.data.labels = distances;
        this.tidalVelocityChart.data.datasets[0].data = components.tidal.surface;
        this.tidalVelocityChart.data.datasets[1].data = components.tidal.middle;
        this.tidalVelocityChart.data.datasets[2].data = components.tidal.deep;
        this.tidalVelocityChart.options.scales.y.min = tidalLimits.min;
        this.tidalVelocityChart.options.scales.y.max = tidalLimits.max;
        this.tidalVelocityChart.update('none');

        // Update River Velocity Chart
        this.riverVelocityChart.data.labels = distances;
        this.riverVelocityChart.data.datasets[0].data = components.river.surface;
        this.riverVelocityChart.data.datasets[1].data = components.river.middle;
        this.riverVelocityChart.data.datasets[2].data = components.river.deep;
        this.riverVelocityChart.options.scales.y.min = riverLimits.min;
        this.riverVelocityChart.options.scales.y.max = riverLimits.max;
        this.riverVelocityChart.update('none');

        // Update Baroclinic Velocity Chart
        this.baroclinicVelocityChart.data.labels = distances;
        this.baroclinicVelocityChart.data.datasets[0].data = components.baroclinic.surface;
        this.baroclinicVelocityChart.data.datasets[1].data = components.baroclinic.middle;
        this.baroclinicVelocityChart.data.datasets[2].data = components.baroclinic.deep;
        this.baroclinicVelocityChart.options.scales.y.min = baroclinicLimits.min;
        this.baroclinicVelocityChart.options.scales.y.max = baroclinicLimits.max;
        this.baroclinicVelocityChart.update('none');
    }

    trackVelocityHistory(components) {
        // Track max and min values across all boxes for each component and layer
        const tidalSurfaceMax = Math.max(...components.tidal.surface);
        const tidalSurfaceMin = Math.min(...components.tidal.surface);
        const tidalMiddleMax = Math.max(...components.tidal.middle);
        const tidalMiddleMin = Math.min(...components.tidal.middle);
        const tidalDeepMax = Math.max(...components.tidal.deep);
        const tidalDeepMin = Math.min(...components.tidal.deep);

        const riverSurfaceMax = Math.max(...components.river.surface);
        const riverSurfaceMin = Math.min(...components.river.surface);
        const riverMiddleMax = Math.max(...components.river.middle);
        const riverMiddleMin = Math.min(...components.river.middle);
        const riverDeepMax = Math.max(...components.river.deep);
        const riverDeepMin = Math.min(...components.river.deep);

        const baroclinicSurfaceMax = Math.max(...components.baroclinic.surface);
        const baroclinicSurfaceMin = Math.min(...components.baroclinic.surface);
        const baroclinicMiddleMax = Math.max(...components.baroclinic.middle);
        const baroclinicMiddleMin = Math.min(...components.baroclinic.middle);
        const baroclinicDeepMax = Math.max(...components.baroclinic.deep);
        const baroclinicDeepMin = Math.min(...components.baroclinic.deep);

        // Add to history
        this.velocityHistory.tidal.surface.push({ max: tidalSurfaceMax, min: tidalSurfaceMin });
        this.velocityHistory.tidal.middle.push({ max: tidalMiddleMax, min: tidalMiddleMin });
        this.velocityHistory.tidal.deep.push({ max: tidalDeepMax, min: tidalDeepMin });
        this.velocityHistory.river.surface.push({ max: riverSurfaceMax, min: riverSurfaceMin });
        this.velocityHistory.river.middle.push({ max: riverMiddleMax, min: riverMiddleMin });
        this.velocityHistory.river.deep.push({ max: riverDeepMax, min: riverDeepMin });
        this.velocityHistory.baroclinic.surface.push({ max: baroclinicSurfaceMax, min: baroclinicSurfaceMin });
        this.velocityHistory.baroclinic.middle.push({ max: baroclinicMiddleMax, min: baroclinicMiddleMin });
        this.velocityHistory.baroclinic.deep.push({ max: baroclinicDeepMax, min: baroclinicDeepMin });

        // Trim history to maxHistoryPoints
        if (this.velocityHistory.tidal.surface.length > this.maxHistoryPoints) {
            this.velocityHistory.tidal.surface.shift();
            this.velocityHistory.tidal.middle.shift();
            this.velocityHistory.tidal.deep.shift();
            this.velocityHistory.river.surface.shift();
            this.velocityHistory.river.middle.shift();
            this.velocityHistory.river.deep.shift();
            this.velocityHistory.baroclinic.surface.shift();
            this.velocityHistory.baroclinic.middle.shift();
            this.velocityHistory.baroclinic.deep.shift();
        }
    }

    getSmoothedYLimits(component) {
        const surfaceHistory = this.velocityHistory[component].surface;
        const middleHistory = this.velocityHistory[component].middle;
        const deepHistory = this.velocityHistory[component].deep;

        // If no history yet, use default range
        if (surfaceHistory.length === 0) {
            return { min: -1, max: 1 };
        }

        // Find overall max and min from history
        const surfaceMax = Math.max(...surfaceHistory.map(h => h.max));
        const surfaceMin = Math.min(...surfaceHistory.map(h => h.min));
        const middleMax = Math.max(...middleHistory.map(h => h.max));
        const middleMin = Math.min(...middleHistory.map(h => h.min));
        const deepMax = Math.max(...deepHistory.map(h => h.max));
        const deepMin = Math.min(...deepHistory.map(h => h.min));

        const overallMax = Math.max(surfaceMax, middleMax, deepMax);
        const overallMin = Math.min(surfaceMin, middleMin, deepMin);

        // Add 15% margin
        const range = overallMax - overallMin;
        const margin = range * 0.15;

        // Handle case where range is very small
        const effectiveMargin = range < 0.01 ? 0.05 : margin;

        return {
            min: overallMin - effectiveMargin,
            max: overallMax + effectiveMargin
        };
    }

    reset() {
        // Clear velocity history
        this.velocityHistory = {
            tidal: { surface: [], middle: [], deep: [] },
            river: { surface: [], middle: [], deep: [] },
            baroclinic: { surface: [], middle: [], deep: [] }
        };

        // Update all charts with fresh data
        this.updateTempProfileChart();
        this.updateSalinityProfileChart();
        this.updateVelocityCharts();
    }
}
