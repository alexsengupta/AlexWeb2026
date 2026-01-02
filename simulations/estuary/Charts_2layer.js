/**
 * Charts_2layer.js
 * Manages Chart.js visualizations for temperature, salinity, and velocity components (2-layer model)
 */

class Charts_2layer {
    constructor(model) {
        this.model = model;
        this.tempProfileChart = null;
        this.salProfileChart = null;
        this.tidalVelocityChart = null;
        this.riverVelocityChart = null;
        this.baroclinicVelocityChart = null;

        // Track recent velocity data for smoothed y-axis limits
        // Store last ~1 day of data (track max/min across all boxes)
        this.velocityHistory = {
            tidal: { upper: [], lower: [] },
            river: { upper: [], lower: [] },
            baroclinic: { upper: [], lower: [] }
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
                        label: 'Upper Layer',
                        data: [],
                        borderColor: 'rgb(255, 99, 71)',
                        backgroundColor: 'rgba(255, 99, 71, 0.1)',
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    },
                    {
                        label: 'Lower Layer',
                        data: [],
                        borderColor: 'rgb(30, 144, 255)',
                        backgroundColor: 'rgba(30, 144, 255, 0.1)',
                        borderDash: [5, 5],
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
                        label: 'Upper Layer',
                        data: [],
                        borderColor: 'rgb(139, 69, 19)',
                        backgroundColor: 'rgba(139, 69, 19, 0.1)',
                        tension: 0.1,
                        fill: false,
                        borderWidth: 2
                    },
                    {
                        label: 'Lower Layer',
                        data: [],
                        borderColor: 'rgb(0, 119, 190)',
                        backgroundColor: 'rgba(0, 119, 190, 0.1)',
                        borderDash: [5, 5],
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
                        label: 'Upper Layer',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Lower Layer',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        borderDash: [5, 5],
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
                        label: 'Upper Layer',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Lower Layer',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderDash: [5, 5],
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
                        label: 'Upper Layer (seaward)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Lower Layer (landward)',
                        data: [],
                        borderColor: 'rgb(255, 159, 64)',
                        backgroundColor: 'rgba(255, 159, 64, 0.1)',
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
        this.tempProfileChart.data.datasets[0].data = [...this.model.temperature.upper];
        this.tempProfileChart.data.datasets[1].data = [...this.model.temperature.lower];
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
        this.salProfileChart.data.datasets[0].data = [...this.model.salinity.upper];
        this.salProfileChart.data.datasets[1].data = [...this.model.salinity.lower];
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
        this.tidalVelocityChart.data.datasets[0].data = components.tidal.upper;
        this.tidalVelocityChart.data.datasets[1].data = components.tidal.lower;
        this.tidalVelocityChart.options.scales.y.min = tidalLimits.min;
        this.tidalVelocityChart.options.scales.y.max = tidalLimits.max;
        this.tidalVelocityChart.update('none');

        // Update River Velocity Chart
        this.riverVelocityChart.data.labels = distances;
        this.riverVelocityChart.data.datasets[0].data = components.river.upper;
        this.riverVelocityChart.data.datasets[1].data = components.river.lower;
        this.riverVelocityChart.options.scales.y.min = riverLimits.min;
        this.riverVelocityChart.options.scales.y.max = riverLimits.max;
        this.riverVelocityChart.update('none');

        // Update Baroclinic Velocity Chart
        this.baroclinicVelocityChart.data.labels = distances;
        this.baroclinicVelocityChart.data.datasets[0].data = components.baroclinic.upper;
        this.baroclinicVelocityChart.data.datasets[1].data = components.baroclinic.lower;
        this.baroclinicVelocityChart.options.scales.y.min = baroclinicLimits.min;
        this.baroclinicVelocityChart.options.scales.y.max = baroclinicLimits.max;
        this.baroclinicVelocityChart.update('none');
    }

    trackVelocityHistory(components) {
        // Track max and min values across all boxes for each component and layer
        const tidalUpperMax = Math.max(...components.tidal.upper);
        const tidalUpperMin = Math.min(...components.tidal.upper);
        const tidalLowerMax = Math.max(...components.tidal.lower);
        const tidalLowerMin = Math.min(...components.tidal.lower);

        const riverUpperMax = Math.max(...components.river.upper);
        const riverUpperMin = Math.min(...components.river.upper);
        const riverLowerMax = Math.max(...components.river.lower);
        const riverLowerMin = Math.min(...components.river.lower);

        const baroclinicUpperMax = Math.max(...components.baroclinic.upper);
        const baroclinicUpperMin = Math.min(...components.baroclinic.upper);
        const baroclinicLowerMax = Math.max(...components.baroclinic.lower);
        const baroclinicLowerMin = Math.min(...components.baroclinic.lower);

        // Add to history
        this.velocityHistory.tidal.upper.push({ max: tidalUpperMax, min: tidalUpperMin });
        this.velocityHistory.tidal.lower.push({ max: tidalLowerMax, min: tidalLowerMin });
        this.velocityHistory.river.upper.push({ max: riverUpperMax, min: riverUpperMin });
        this.velocityHistory.river.lower.push({ max: riverLowerMax, min: riverLowerMin });
        this.velocityHistory.baroclinic.upper.push({ max: baroclinicUpperMax, min: baroclinicUpperMin });
        this.velocityHistory.baroclinic.lower.push({ max: baroclinicLowerMax, min: baroclinicLowerMin });

        // Trim history to maxHistoryPoints
        if (this.velocityHistory.tidal.upper.length > this.maxHistoryPoints) {
            this.velocityHistory.tidal.upper.shift();
            this.velocityHistory.tidal.lower.shift();
            this.velocityHistory.river.upper.shift();
            this.velocityHistory.river.lower.shift();
            this.velocityHistory.baroclinic.upper.shift();
            this.velocityHistory.baroclinic.lower.shift();
        }
    }

    getSmoothedYLimits(component) {
        const upperHistory = this.velocityHistory[component].upper;
        const lowerHistory = this.velocityHistory[component].lower;

        // If no history yet, use default range
        if (upperHistory.length === 0) {
            return { min: -1, max: 1 };
        }

        // Find overall max and min from history
        const upperMax = Math.max(...upperHistory.map(h => h.max));
        const upperMin = Math.min(...upperHistory.map(h => h.min));
        const lowerMax = Math.max(...lowerHistory.map(h => h.max));
        const lowerMin = Math.min(...lowerHistory.map(h => h.min));

        const overallMax = Math.max(upperMax, lowerMax);
        const overallMin = Math.min(upperMin, lowerMin);

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
            tidal: { upper: [], lower: [] },
            river: { upper: [], lower: [] },
            baroclinic: { upper: [], lower: [] }
        };

        // Update all charts with fresh data
        this.updateTempProfileChart();
        this.updateSalinityProfileChart();
        this.updateVelocityCharts();
    }
}
