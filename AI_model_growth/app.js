const DATA_PATH = 'example_data/ai_models/frontier_ai_models.csv';

// Configuration
const margin = { top: 60, right: 150, bottom: 80, left: 100 };
const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
const height = document.getElementById('chart').clientHeight - margin.top - margin.bottom;

const svg = d3.select('#chart')
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

const tooltip = d3.select('#tooltip');
const FILTER_START_DATE = new Date('2023-01-01');

// Global state
let allModelData = [];
let benchmarkDatasets = {}; // raw data from csvs
let metrData = []; // METR Time Horizons data
let currentView = 'market';
let currentBenchmarkMode = 'eci'; // eci or combined
let autonomyMetric = 'p50'; // 'p50' or 'p80'
let autonomyXAxis = 'Release date'; // 'Release date' or 'Training compute (FLOP)'
let selectedOrgs = ["Google", "OpenAI", "Meta AI", "Anthropic", "xAI", "Other"];
let selectedBenchmarks = ['gpqa', 'weirdml', 'frontiermath', 'swe', 'arc'];

const BENCHMARKS = {
    eci: { path: 'example_data/benchmark_data/epoch_capabilities_index.csv', valueCol: 'ECI Score', nameCol: 'Model name', normFactor: 1, label: 'ECI', symbol: d3.symbolCircle },
    gpqa: { path: 'example_data/benchmark_data/gpqa_diamond.csv', valueCol: 'mean_score', nameCol: 'Model version', normFactor: 100, label: 'GPQA Diamond', symbol: d3.symbolDiamond },
    weirdml: { path: 'example_data/benchmark_data/weirdml_external.csv', valueCol: 'Accuracy', nameCol: 'Model version', normFactor: 100, label: 'WeirdML V2', symbol: d3.symbolSquare },
    frontiermath: { path: 'example_data/benchmark_data/frontiermath.csv', valueCol: 'mean_score', nameCol: 'Model version', normFactor: 100, label: 'FrontierMath T1-3', symbol: d3.symbolTriangle },
    swe: { path: 'example_data/benchmark_data/swe_bench_verified.csv', valueCol: 'mean_score', nameCol: 'Model version', normFactor: 100, label: 'SWE-bench Verified', symbol: d3.symbolStar },
    arc: { path: 'example_data/benchmark_data/arc_agi_external.csv', valueCol: 'Score', nameCol: 'Model version', normFactor: 100, label: 'ARC', symbol: d3.symbolCross }
};

let xScale, yScale, colorScale;
let yColumn = 'Training compute (FLOP)';
let colorColumn = 'Domain';

// Helper: Format large numbers
const formatSI = d3.format(".2s");
const formatScale = (d) => {
    if (d === 0) return "0";
    if (d < 1e3 && d > -1e3) return d3.format(".2n")(d);
    return d.toExponential(1);
};

// Helper: Linear regression (for trend lines)
function calculateLinearRegression(data, xAccessor, yAccessor) {
    const validData = data.filter(d => yAccessor(d) > 0);
    const n = validData.length;
    if (n < 2) return null;

    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    validData.forEach(d => {
        const x = xAccessor(d);
        const y = Math.log10(yAccessor(d));
        sumX += x;
        sumY += y;
        sumXY += x * y;
        sumXX += x * x;
    });

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    return x => Math.pow(10, slope * x + intercept);
}

// Helper: Normalize Organization
function getNormalizedOrg(orgName) {
    if (!orgName) return 'Other';
    const name = orgName.toLowerCase();
    if (name.includes('google') || name.includes('deepmind')) return 'Google';
    if (name.includes('openai')) return 'OpenAI';
    if (name.includes('meta') || name.includes('facebook')) return 'Meta AI';
    if (name.includes('anthropic')) return 'Anthropic';
    if (name.includes('xai')) return 'xAI';
    return 'Other';
}

// Helper: Parse METR YAML (Lightweight parser for specific schema)
function parseMETRYaml(text) {
    const models = [];
    const lines = text.split('\n');
    let currentModel = null;
    let modelData = {};
    let context = []; 

    let inResults = false;

    for (let line of lines) {
        if (!line.trim() || line.trim().startsWith('#')) continue;
        const indent = line.search(/\S/);
        const content = line.trim();

        if (content === 'results:') {
            inResults = true;
            continue;
        }
        if (!inResults) continue;

        if (indent === 2) {
            if (currentModel) models.push(modelData);
            currentModel = content.replace(':', '');
            modelData = { id: currentModel, metrics: {} };
        }
        
        if (currentModel) {
            if (content.startsWith('release_date:')) {
                modelData.releaseDate = content.split(':')[1].trim();
            }
            
            // Track context for metrics (p50 vs p80)
            if (indent === 6) {
                if (content.startsWith('p50_horizon_length:')) context = ['p50'];
                else if (content.startsWith('p80_horizon_length:')) context = ['p80'];
                else context = [];
            }
            
            if (indent === 8 && content.startsWith('estimate:') && context.length > 0) {
                const val = parseFloat(content.split(':')[1].trim());
                if (context[0] === 'p50') modelData.metrics.p50 = val;
                if (context[0] === 'p80') modelData.metrics.p80 = val;
            }
        }
    }
    if (currentModel) models.push(modelData);
    return models;
}

// Helper: Match YAML ID to Main Data for Metadata
function matchModelToMainData(yamlId, mainData) {
    const normId = yamlId.toLowerCase().replace(/[^a-z0-9]/g, '');
    
    // Try to find match in main dataset
    let match = mainData.find(d => {
        const normModel = d.Model.toLowerCase().replace(/[^a-z0-9]/g, '');
        return normModel === normId || normModel.includes(normId) || normId.includes(normModel);
    });

    if (match) return { org: match.Organization, compute: match['Training compute (FLOP)'] };

    // Fallback inference
    let org = 'Other';
    if (yamlId.includes('claude')) org = 'Anthropic';
    else if (yamlId.includes('gpt') || yamlId.includes('o1') || yamlId.includes('davinci')) org = 'OpenAI';
    else if (yamlId.includes('gemini')) org = 'Google';
    else if (yamlId.includes('llama') || yamlId.includes('meta')) org = 'Meta AI';
    else if (yamlId.includes('grok')) org = 'xAI';
    return { org, compute: null };
}

// Load All Data
async function initApp() {
    const mainData = await d3.csv(DATA_PATH);

    // Load all benchmarks
    const benchmarkPromises = Object.entries(BENCHMARKS).map(async ([key, config]) => {
        try {
            const data = await d3.csv(config.path);
            return [key, data];
        } catch (e) {
            console.error(`Failed to load benchmark: ${key}`, e);
            return [key, []];
        }
    });

    const benchmarkResults = await Promise.all(benchmarkPromises);
    benchmarkDatasets = Object.fromEntries(benchmarkResults);

    // Process Main Data
    mainData.forEach(d => {
        d['Publication date'] = new Date(d['Publication date']);
        d['Training compute (FLOP)'] = parseFloat(d['Training compute (FLOP)']) || null;
        d['Parameters'] = parseFloat(d['Parameters']) || null;

        let ds = d['Training dataset size (gradients)'];
        if (ds && typeof ds === 'string') ds = ds.replace(/,/g, '');
        d['Training dataset size (gradients)'] = parseFloat(ds) || null;

        d['Training compute cost (2023 USD)'] = parseFloat(d['Training compute cost (2023 USD)']) || null;
        Object.keys(BENCHMARKS).forEach(key => d[key] = null);
    });

    const allowedCountries = ["United States of America", "China", "United Kingdom", "France", "Canada", "Germany", "South Korea", "Hong Kong", "Singapore"];
    const allowedDomains = ["Language", "Vision", "Multimodal", "Biology", "Games", "Speech", "Image generation", "Video", "Robotics"];

    allModelData = mainData.filter(d => !isNaN(d['Publication date'])).map(d => {
        let country = d['Country (of organization)'] || 'Other';
        if (country.includes('United Kingdom')) country = 'United Kingdom';
        if (country.includes('United States')) country = 'United States of America';
        let matchedCountry = 'Other';
        for (const ac of allowedCountries) { if (country.includes(ac)) { matchedCountry = ac; break; } }
        d['Country (of organization)'] = matchedCountry;

        let domain = d['Domain'] || 'Other';
        let matchedDomain = 'Other';
        for (const ad of allowedDomains) { if (domain.toLowerCase().includes(ad.toLowerCase())) { matchedDomain = ad; break; } }
        d['Domain'] = matchedDomain;
        return d;
    });

    // Post-process benchmarks to include metadata from mainData
    Object.entries(benchmarkDatasets).forEach(([benchKey, data]) => {
        const config = BENCHMARKS[benchKey];
        data.forEach(row => {
            const scoreValue = parseFloat(row[config.valueCol]);
            if (isNaN(scoreValue)) return;

            // Standardize score
            row.score = scoreValue;
            if (config.normFactor === 100 && scoreValue <= 1.0) {
                row.score = scoreValue * 100;
            } else if (config.normFactor === 100 && scoreValue > 100) {
                // Handle cases where scores might be 0-100 but some are outliers
            }

            row.date = row['Release date'] ? new Date(row['Release date']) : null;
            if (isNaN(row.date)) row.date = null;

            // Match with mainData for metadata
            const name = (row[config.nameCol] || "").toLowerCase().trim();
            const match = allModelData.find(m => {
                const mName = m.Model.toLowerCase().trim();
                return mName === name || mName.includes(name) || name.includes(mName);
            });

            if (match) {
                row.frontier = match['Frontier model'] === 'True';
                row.orgType = match['Organization categorization'];
                row.country = match['Country (of organization)'];
                row.modelName = match.Model;
                if (!row.date) row.date = match['Publication date'];

                // Add score back to mainData for market growth view
                if (match[benchKey] === null || row.score > match[benchKey]) {
                    match[benchKey] = row.score;
                }
            } else {
                row.frontier = false; // Assume false if not in main list
                row.modelName = row[config.nameCol];
            }
        });

        // Final filter for valid benchmarks
        benchmarkDatasets[benchKey] = data.filter(d => d.date && !isNaN(d.score));
    });

    // Load METR Time Horizons data (YAML)
    try {
        const response = await fetch('METR/benchmark_results.yaml');
        const yamlText = await response.text();
        const parsedMetr = parseMETRYaml(yamlText);
        
        metrData = parsedMetr.map(d => {
            const releaseDate = d.releaseDate ? new Date(d.releaseDate) : null;
            const match = matchModelToMainData(d.id, allModelData);
            
            if (!releaseDate) return null;

            return {
                model: d.id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ').replace(/Gpt/g, 'GPT'),
                timeHorizonP50: d.metrics.p50,
                timeHorizonP80: d.metrics.p80,
                releaseDate: releaseDate,
                organization: match.org,
                normalizedOrg: getNormalizedOrg(match.org),
                compute: match.compute,
                notes: ''
            };
        }).filter(d => d !== null && (d.timeHorizonP50 || d.timeHorizonP80));
        
        injectAutonomyControls();
    } catch (e) {
        console.error('Failed to load METR data:', e);
        metrData = [];
    }

    setupViewSwitcher();
    renderGranularFilters();
    updateVariableExplanations();
    updateChart();
}

initApp();

function injectAutonomyControls() {
    const container = document.getElementById('autonomy-controls');
    if (container && !document.getElementById('autonomy-metric-toggle')) {
        const div = document.createElement('div');
        div.id = 'autonomy-metric-toggle';
        div.className = 'control-group';
        div.style.marginTop = '10px';
        div.innerHTML = `
            <label class="control-label">Metric:</label>
            <select id="autonomy-metric-select" class="control-select">
                <option value="p50" selected>P50 (Median Estimate)</option>
                <option value="p80">P80 (High Confidence)</option>
            </select>
        `;
        // Insert after the X-axis selector
        const xAxisControl = document.getElementById('autonomy-x-axis').parentNode;
        xAxisControl.parentNode.insertBefore(div, xAxisControl.nextSibling);

        document.getElementById('autonomy-metric-select').addEventListener('change', (e) => {
            autonomyMetric = e.target.value;
            updateChart();
        });
    }
}

function setupViewSwitcher() {
    const tabs = document.querySelectorAll('.view-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentView = tab.dataset.view;

            // Toggle controls
            document.getElementById('market-controls').style.display = currentView === 'market' ? 'block' : 'none';
            document.getElementById('benchmark-controls').style.display = currentView === 'benchmarks' ? 'block' : 'none';
            document.getElementById('autonomy-controls').style.display = currentView === 'autonomy' ? 'block' : 'none';

            updateChart();
            updateVariableExplanations();
            renderGranularFilters();
        });
    });

    document.getElementById('y-axis').addEventListener('change', () => {
        updateChart();
        updateVariableExplanations();
    });

    document.querySelectorAll('input[name="benchmark-mode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentBenchmarkMode = e.target.value;
            updateChart();
            updateVariableExplanations();
            renderGranularFilters();
        });
    });

    document.getElementById('autonomy-x-axis').addEventListener('change', (e) => {
        autonomyXAxis = e.target.value;
        updateChart();
    });
}

function renderGranularFilters() {
    const container = d3.select("#granular-filters");
    container.selectAll("*").remove();

    // 1. Organization Filters
    const orgGroup = container.append("div").attr("class", "filter-group");
    orgGroup.append("span").attr("class", "filter-group-title").text("Filter by Organization");

    const orgs = ["Google", "OpenAI", "Meta AI", "Anthropic", "xAI", "Other"];
    orgs.forEach(org => {
        const item = orgGroup.append("label").attr("class", "filter-checkbox-item");
        item.append("input")
            .attr("type", "checkbox")
            .attr("value", org)
            .property("checked", selectedOrgs.includes(org))
            .on("change", function () {
                if (this.checked) {
                    if (!selectedOrgs.includes(this.value)) selectedOrgs.push(this.value);
                } else {
                    selectedOrgs = selectedOrgs.filter(o => o !== this.value);
                }
                updateChart();
            });
        item.append("span").text(org);
    });

    // 2. Benchmark Filters (Only in Benchmarks Combined mode)
    if (currentView === 'benchmarks' && currentBenchmarkMode === 'combined') {
        const benchGroup = container.append("div").attr("class", "filter-group");
        benchGroup.append("span").attr("class", "filter-group-title").text("Filter by Benchmark");

        const benchmarks = Object.keys(BENCHMARKS).filter(k => k !== 'eci');
        benchmarks.forEach(key => {
            const item = benchGroup.append("label").attr("class", "filter-checkbox-item");
            item.append("input")
                .attr("type", "checkbox")
                .attr("value", key)
                .property("checked", selectedBenchmarks.includes(key))
                .on("change", function () {
                    if (this.checked) {
                        if (!selectedBenchmarks.includes(this.value)) selectedBenchmarks.push(this.value);
                    } else {
                        selectedBenchmarks = selectedBenchmarks.filter(k => k !== this.value);
                    }
                    updateChart();
                });
            item.append("span").text(BENCHMARKS[key].label);
        });
    }
}

function updateChart() {
    svg.selectAll("*").remove();

    if (currentView === 'market') {
        const filteredData = allModelData.filter(d => {
            const org = getNormalizedOrg(d.Organization);
            return selectedOrgs.includes(org);
        });
        renderMarketGrowth(filteredData);
    } else if (currentView === 'autonomy') {
        const filteredData = metrData.filter(d => {
            return selectedOrgs.includes(d.normalizedOrg);
        });
        renderAutonomy(filteredData);
    } else {
        renderBenchmarks();
    }
}

function updateVariableExplanations() {
    const container = d3.select("#variable-explanations");
    container.selectAll("*").remove();

    let title = "Variable Definitions";
    let content = [];

    if (currentView === 'market') {
        const yVar = document.getElementById('y-axis').value;
        const definitions = {
            'Training compute (FLOP)': {
                term: 'Training Compute',
                text: 'Training compute refers to the total computational resources—measured in FLOPs (floating-point operations)—used to train an LLM on its dataset. It scales with model size, dataset size, and training duration. Higher training compute generally correlates with improved model capabilities, following empirical scaling laws.'
            },
            'Parameters': {
                term: 'Parameters',
                text: 'The number of adjustable weights in a neural network that are learned during training. More parameters generally enable greater model capacity to capture complex patterns, though efficiency depends on architecture and training approach.'
            },
            'Training dataset size (gradients)': {
                term: 'Dataset Size',
                text: 'The volume of text (measured in tokens) used to train an LLM. Scaling laws suggest optimal performance requires balancing dataset size with model parameters—undertrained large models waste compute.'
            },
            'Training compute cost (2023 USD)': {
                term: 'Training Cost',
                text: 'The total financial expenditure to train a model, encompassing compute infrastructure (GPU/TPU rental or ownership), electricity, cooling, engineering personnel, and data acquisition. Frontier models now cost tens to hundreds of millions of dollars.'
            }
        };

        const def = definitions[yVar];
        if (def) {
            content.push(def);
        }
    } else if (currentView === 'autonomy') {
        content.push({
            term: 'Time Horizon (METR)',
            text: 'The time an expert typically takes to complete tasks that AI models can complete with 50%/80% success rate'
        });
    } else {
        if (currentBenchmarkMode === 'eci') {
            content.push({
                term: 'ECI (Capability Index)',
                text: 'The Epoch Capabilities Index (ECI) combines scores from many different AI benchmarks into a single "general capability" scale, allowing comparisons between models even over timespans long enough for single benchmarks to reach saturation.'
            });
        } else {
            content.push({
                term: 'Standardised Benchmarks',
                text: 'GPQA Diamond tests expert-level science questions designed to resist web search. WeirdML V2 evaluates reasoning on novel, out-of-distribution problems. FrontierMath (Tiers 1-3) presents research-level mathematics problems unsolved by current models. SWE-bench Verified measures real-world software engineering through actual GitHub issue resolution. ARC assesses abstract reasoning and generalisation. These benchmarks enable cross-model comparison, though critics note they may incentivise teaching-to-the-test.'
            });
        }
    }

    container.append("h4").text(title);
    content.forEach(item => {
        const div = container.append("div").attr("class", "explanation-item");
        div.append("span").attr("class", "explanation-term").text(item.term + ":");
        div.append("p").attr("class", "explanation-text").text(item.text);
    });
}

function renderMarketGrowth(data) {
    yColumn = document.getElementById('y-axis').value;
    colorColumn = document.getElementById('color-by').value;
    const showTrends = document.getElementById('show-trends').checked;

    const chartData = data.filter(d => d[yColumn] !== null && d[yColumn] > 0);

    // X Scale
    xScale = d3.scaleTime()
        .domain(d3.extent(allModelData, d => d['Publication date']))
        .range([0, width]);

    // Y Scale
    yScale = d3.scaleLog()
        .domain(d3.extent(chartData, d => d[yColumn]))
        .nice()
        .range([height, 0]);

    // Color Scale for Market Growth
    const categories = Array.from(new Set(allModelData.map(d => d[colorColumn]))).filter(Boolean).sort((a, b) => {
        if (a === 'Other') return 1;
        if (b === 'Other') return -1;
        return a.localeCompare(b);
    });
    colorScale = d3.scaleOrdinal(d3.schemeTableau10).domain(categories);

    renderBaseChart(chartData, xScale, yScale, 'Publication Year', yColumn, true);

    if (showTrends) renderTrends(chartData);
    renderPoints(chartData, 'Publication date', yColumn);
    renderLegend(categories);
}

function renderBenchmarks() {
    const mode = currentBenchmarkMode;

    let datasetsToPlot = [];
    let yAxisLabel = "";
    let isLogY = false;

    if (mode === 'eci') {
        datasetsToPlot = [{ key: 'eci', data: benchmarkDatasets['eci'], label: 'ECI' }];
        yAxisLabel = "Epoch Capabilities Index (ECI)";
    } else {
        // Combined mode
        const combinedKeys = ['gpqa', 'weirdml', 'frontiermath', 'swe', 'arc'];
        datasetsToPlot = combinedKeys.map(key => ({
            key: key,
            data: benchmarkDatasets[key],
            label: BENCHMARKS[key].label
        }));
        yAxisLabel = "Benchmark Score (%)";
    }

    // Apply Date Filter to datasets (2023+) and normalize orgs
    // Also apply filters (Org and Benchmark)
    datasetsToPlot.forEach(ds => {
        ds.data = ds.data.filter(d => d.date >= FILTER_START_DATE);

        // Filter by Benchmark Key
        if (mode === 'combined' && !selectedBenchmarks.includes(ds.key)) {
            ds.data = [];
        }

        ds.data.forEach(d => {
            d.normOrg = getNormalizedOrg(d.Organization || d.orgType || d.Organization);
            d.symbolType = BENCHMARKS[ds.key].symbol;
        });

        // Filter by Organization
        ds.data = ds.data.filter(d => selectedOrgs.includes(d.normOrg));
    });

    // Flatten for scales
    const allVisiblePoints = datasetsToPlot.flatMap(ds => ds.data);
    if (allVisiblePoints.length === 0) {
        svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle").text("No data points available for this selection.");
        return;
    }

    // X Scale (Fixed to Date)
    xScale = d3.scaleTime()
        .domain(d3.extent(allVisiblePoints, d => d.date))
        .nice()
        .range([0, width]);

    // Color Scale for Orgs
    const orgs = ["Google", "OpenAI", "Meta AI", "Anthropic", "xAI", "Other"];
    const orgColors = d3.scaleOrdinal()
        .domain(orgs)
        .range(["#4285F4", "#10a37f", "#0668E1", "#D97757", "#000000", "#adb5bd"]);

    // Y Scale (Dynamic calculation)
    const yExtent = d3.extent(allVisiblePoints, d => d.score);
    yScale = d3.scaleLinear()
        .domain([Math.max(0, yExtent[0] * (mode === 'combined' ? 0.5 : 0.9)), yExtent[1] * 1.05])
        .nice()
        .range([height, 0]);

    renderBaseChart([], xScale, yScale, 'Publication Date', yAxisLabel, isLogY);

    // Render points with org-based coloring and distinctive shapes
    datasetsToPlot.forEach(ds => {
        renderBenchmarkPoints(ds.data, orgColors, ds.label, BENCHMARKS[ds.key].symbol);
    });

    renderBenchmarkLegend(orgs, orgColors, datasetsToPlot);
}

function renderBenchmarkPoints(data, colorScale, benchLabel, symbolType) {
    const symbolGenerator = d3.symbol().size(60);

    svg.selectAll(`.dot-${benchLabel.replace(/[^a-z0-9]/gi, '')}`)
        .data(data)
        .enter()
        .append("path")
        .attr("class", `dot dot-benchmark`)
        .attr("d", d => symbolGenerator.type(symbolType)())
        .attr("transform", d => `translate(${xScale(d.date)},${yScale(d.score)})`)
        .attr("fill", d => colorScale(d.normOrg))
        .attr("stroke", "#fff")
        .attr("stroke-width", 1)
        .attr("opacity", 0.7)
        .style("cursor", "pointer")
        .on("mouseover", (event, d) => {
            d3.select(event.currentTarget).attr("r", 8).attr("opacity", 1).attr("stroke-width", 2);
            tooltip.style("opacity", 1)
                .html(`
                    <div class="tooltip-title">${d.modelName}</div>
                    <div class="tooltip-row"><span class="tooltip-label">Benchmark:</span><span class="tooltip-value">${benchLabel}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Organization:</span><span class="tooltip-value">${d.normOrg}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Date:</span><span class="tooltip-value">${d.date.toLocaleDateString()}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Score:</span><span class="tooltip-value highlight-score">${d.score.toFixed(2)}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Frontier:</span><span class="tooltip-value">${d.frontier ? 'Yes' : 'No'}</span></div>
                `)
                .style("left", (event.pageX + 20) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseout", (event) => {
            d3.select(event.currentTarget).attr("r", 5).attr("opacity", 0.7).attr("stroke-width", 1);
            tooltip.style("opacity", 0);
        });
}

function renderBenchmarkLegend(orgs, orgColorScale, datasets) {
    const legend = d3.select("#legend");
    legend.selectAll("*").remove();

    // Section 1: Organizations (Colors)
    legend.append("div").attr("class", "legend-section-title").text("By Organization");
    orgs.forEach(org => {
        const item = legend.append("div").attr("class", "legend-item");
        item.append("div").attr("class", "legend-color").style("background", orgColorScale(org));
        item.append("span").text(org);
    });

    // Section 2: Benchmarks (Shapes) - only in combined mode
    if (currentBenchmarkMode === 'combined') {
        legend.append("div").attr("class", "legend-section-title").style("margin-top", "1rem").text("By Benchmark");
        const symbolGenerator = d3.symbol().size(40);
        datasets.forEach(ds => {
            const item = legend.append("div").attr("class", "legend-item");
            const svgIcon = item.append("svg").attr("width", 12).attr("height", 12).append("path")
                .attr("d", symbolGenerator.type(BENCHMARKS[ds.key].symbol)())
                .attr("transform", "translate(6,6)")
                .attr("fill", "#6c757d");
            item.append("span").text(ds.label);
        });
    }
}

function renderBaseChart(data, xSc, ySc, xLabel, yLabel, isLogY) {
    // Era Shading (only for date X axis)
    if (xLabel.includes('Date') || xLabel.includes('Year')) {
        const deepLearningStart = new Date('2010-01-01');
        const dlStartX = xSc(deepLearningStart);
        if (dlStartX > 0 && dlStartX < width) {
            svg.append("rect").attr("x", dlStartX).attr("y", 0).attr("width", width - dlStartX).attr("height", height).attr("class", "era-shading");
            svg.append("line").attr("x1", dlStartX).attr("x2", dlStartX).attr("y1", 0).attr("y2", height).attr("stroke", "#dee2e6").attr("stroke-dasharray", "4,4");
            svg.append("text").attr("x", dlStartX + 10).attr("y", -10).attr("class", "era-label").text("Deep Learning Era →");
        }
    }

    // Grid lines
    svg.append("g").attr("class", "grid").attr("transform", `translate(0,${height})`).call(d3.axisBottom(xSc).ticks(8).tickSize(-height).tickFormat(""));
    svg.append("g").attr("class", "grid").call(d3.axisLeft(ySc).ticks(10).tickSize(-width).tickFormat(""));

    // Axes
    const xAxis = d3.axisBottom(xSc).ticks(8).tickFormat(d3.timeFormat("%b %Y"));
    const yAxis = isLogY ? d3.axisLeft(ySc).ticks(10, formatScale) : d3.axisLeft(ySc).tickFormat(formatScale);

    svg.append("g").attr("transform", `translate(0,${height})`).attr("class", "axis").call(xAxis)
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", ".15em")
        .attr("transform", "rotate(-45)");
    svg.append("g").attr("class", "axis").call(yAxis);

    // Labels
    svg.append("text").attr("class", "axis-label").attr("text-anchor", "middle").attr("x", width / 2).attr("y", height + 50).text(xLabel);
    svg.append("text").attr("class", "axis-label").attr("text-anchor", "middle").attr("transform", "rotate(-90)").attr("y", -70).attr("x", -height / 2).text(yLabel);
}

function renderPoints(data, xCol, yCol) {
    svg.selectAll(".dot")
        .data(data)
        .enter()
        .append("circle")
        .attr("class", "dot")
        .attr("cx", d => xScale(d[xCol]))
        .attr("cy", d => yScale(d[yCol]))
        .attr("r", 6)
        .attr("fill", d => colorScale(d[colorColumn]))
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .attr("opacity", 0.8)
        .style("cursor", "pointer")
        .on("mouseover", (event, d) => {
            d3.select(event.currentTarget).attr("r", 9).attr("opacity", 1).attr("stroke-width", 2);

            const isBenchmark = Object.keys(BENCHMARKS).includes(yCol);
            const scoreDisplay = d[yCol] !== null ?
                (isBenchmark ? d[yCol].toFixed(2) : formatScale(d[yCol])) :
                'N/A';

            tooltip.style("opacity", 1)
                .html(`
                    <div class="tooltip-title">${d.Model}</div>
                    <div class="tooltip-row"><span class="tooltip-label">Date:</span><span class="tooltip-value">${d['Publication date'].toLocaleDateString()}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Organization:</span><span class="tooltip-value">${d.Organization}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">${yCol}:</span><span class="tooltip-value highlight-score">${scoreDisplay}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Compute (FLOP):</span><span class="tooltip-value">${d['Training compute (FLOP)'] ? formatScale(d['Training compute (FLOP)']) : 'N/A'}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Parameters:</span><span class="tooltip-value">${d.Parameters ? formatScale(d.Parameters) : 'N/A'}</span></div>
                `)
                .style("left", (event.pageX + 20) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseout", (event) => {
            d3.select(event.currentTarget).attr("r", 6).attr("opacity", 0.8).attr("stroke-width", 1.5);
            tooltip.style("opacity", 0);
        });
}

function renderTrends(data) {
    const deepLearningStart = new Date('2010-01-01');
    const pre2010Data = data.filter(d => d['Publication date'] < deepLearningStart);
    const post2010Data = data.filter(d => d['Publication date'] >= deepLearningStart);

    const preRegression = calculateLinearRegression(pre2010Data, d => d['Publication date'].getTime(), d => d[yColumn]);
    const postRegression = calculateLinearRegression(post2010Data, d => d['Publication date'].getTime(), d => d[yColumn]);

    if (preRegression) {
        const line = d3.line().x(d => xScale(d)).y(d => yScale(preRegression(d.getTime())));
        const domain = d3.extent(pre2010Data, d => d['Publication date']);
        svg.append("path").datum([domain[0], domain[1]]).attr("class", "trend-line").attr("stroke", "#adb5bd").attr("d", line);
    }

    if (postRegression) {
        const line = d3.line().x(d => xScale(d)).y(d => yScale(postRegression(d.getTime())));
        const domain = d3.extent(post2010Data, d => d['Publication date']);
        svg.append("path").datum([domain[0], domain[1]]).attr("class", "trend-line").attr("stroke", "var(--accent)").attr("d", line);
    }
}

function renderLegend(categories) {
    const legend = d3.select("#legend");
    legend.selectAll("*").remove();
    categories.forEach(cat => {
        const item = legend.append("div").attr("class", "legend-item");
        item.append("div").attr("class", "legend-color").style("background", colorScale(cat));
        item.append("span").text(cat);
    });
}

// Event Listeners
document.getElementById('y-axis').addEventListener('change', updateChart);
document.getElementById('color-by').addEventListener('change', updateChart);
document.getElementById('show-trends').addEventListener('change', updateChart);

function renderAutonomy(data) {
    // Filter data based on x-axis selection
    const chartData = data.filter(d => {
        const val = autonomyMetric === 'p50' ? d.timeHorizonP50 : d.timeHorizonP80;
        if (autonomyXAxis === 'Release date') {
            return d.releaseDate !== null && val > 0;
        } else {
            return d.compute !== null && val > 0;
        }
    });

    if (chartData.length === 0) {
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height / 2)
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .style("fill", "#666")
            .text("No data available for this view");
        return;
    }

    // X Scale
    if (autonomyXAxis === 'Release date') {
        xScale = d3.scaleTime()
            .domain(d3.extent(chartData, d => d.releaseDate))
            .range([0, width]);
    } else {
        xScale = d3.scaleLog()
            .domain(d3.extent(chartData, d => d.compute))
            .nice()
            .range([0, width]);
    }

    // Y Scale (Time Horizon in minutes)
    const minMinutes = d3.min(chartData, d => autonomyMetric === 'p50' ? d.timeHorizonP50 : d.timeHorizonP80);
    const maxMinutes = d3.max(chartData, d => autonomyMetric === 'p50' ? d.timeHorizonP50 : d.timeHorizonP80);

    yScale = d3.scaleLog()
        .domain([minMinutes, maxMinutes])
        .nice()
        .range([height, 0]);

    // Custom time formatter for y-axis
    const formatTime = (minutes) => {
        if (minutes < 1) {
            const seconds = minutes * 60;
            return `${seconds.toFixed(0)}s`;
        } else if (minutes < 60) {
            return `${minutes.toFixed(0)}m`;
        } else if (minutes < 1440) {
            const hours = minutes / 60;
            return `${hours.toFixed(0)}h`;
        } else {
            const days = minutes / 1440;
            return `${days.toFixed(0)}d`;
        }
    };

    // Custom tick values: 1s, 4s, 15s, 1m, 4m, 15m, 1h, 4h, 15h, 1d, 4d, 15d, etc.
    const customTicks = [];
    // Base units in minutes: seconds, minutes, hours, days, months, years
    const timeBases = [1/60, 1, 60, 1440, 43200, 525600];
    const multipliers = [1, 4, 15];

    timeBases.forEach(base => {
        multipliers.forEach(mult => {
            const val = base * mult;
            if (val >= minMinutes * 0.5 && val <= maxMinutes * 2) {
                customTicks.push(val);
            }
        });
    });
    const uniqueTicks = [...new Set(customTicks)].sort((a, b) => a - b);

    // Color Scale by Organization
    const orgs = Array.from(new Set(chartData.map(d => d.normalizedOrg))).filter(Boolean).sort((a, b) => {
        if (a === 'Other') return 1;
        if (b === 'Other') return -1;
        return a.localeCompare(b);
    });
    colorScale = d3.scaleOrdinal(d3.schemeTableau10).domain(orgs);

    // Grid lines
    const xAxisGrid = autonomyXAxis === 'Release date'
        ? d3.axisBottom(xScale).ticks(8)
        : d3.axisBottom(xScale).ticks(8);
    svg.append("g").attr("class", "grid").attr("transform", `translate(0,${height})`)
        .call(xAxisGrid.tickSize(-height).tickFormat(""));
    svg.append("g").attr("class", "grid")
        .call(d3.axisLeft(yScale).tickValues(uniqueTicks).tickSize(-width).tickFormat(""));

    // Axes
    const xAxis = autonomyXAxis === 'Release date'
        ? d3.axisBottom(xScale).ticks(8).tickFormat(d3.timeFormat("%b %Y"))
        : d3.axisBottom(xScale).ticks(8, formatScale);
    const yAxis = d3.axisLeft(yScale).tickValues(uniqueTicks).tickFormat(formatTime);

    svg.append("g").attr("transform", `translate(0,${height})`).attr("class", "axis").call(xAxis)
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", ".15em")
        .attr("transform", "rotate(-45)");
    svg.append("g").attr("class", "axis").call(yAxis);

    // Labels
    const xLabel = autonomyXAxis === 'Release date' ? 'RELEASE DATE' : 'TRAINING COMPUTE (FLOP)';
    svg.append("text").attr("class", "axis-label").attr("text-anchor", "middle")
        .attr("x", width / 2).attr("y", height + 50).text(xLabel);
    svg.append("text").attr("class", "axis-label").attr("text-anchor", "middle")
        .attr("transform", "rotate(-90)").attr("y", -70).attr("x", -height / 2)
        .text("TIME HORIZON");

    // Render points
    svg.selectAll(".dot")
        .data(chartData)
        .enter()
        .append("circle")
        .attr("class", "dot")
        .attr("cx", d => autonomyXAxis === 'Release date' ? xScale(d.releaseDate) : xScale(d.compute))
        .attr("cy", d => yScale(autonomyMetric === 'p50' ? d.timeHorizonP50 : d.timeHorizonP80))
        .attr("r", 6)
        .attr("fill", d => colorScale(d.normalizedOrg))
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .attr("opacity", 0.8)
        .style("cursor", "pointer")
        .on("mouseover", (event, d) => {
            d3.select(event.currentTarget).attr("r", 9).attr("opacity", 1).attr("stroke-width", 2);

            // Format time horizon nicely
            const minutes = autonomyMetric === 'p50' ? d.timeHorizonP50 : d.timeHorizonP80;
            let timeDisplay;
            if (minutes < 1) {
                timeDisplay = `${(minutes * 60).toFixed(0)} seconds`;
            } else if (minutes < 60) {
                timeDisplay = `${minutes.toFixed(1)} minutes`;
            } else {
                const hours = minutes / 60;
                timeDisplay = `${hours.toFixed(1)} hours`;
            }

            tooltip.style("opacity", 1)
                .html(`
                    <div class="tooltip-title">${d.model}</div>
                    <div class="tooltip-row"><span class="tooltip-label">Organization:</span><span class="tooltip-value">${d.organization}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Time Horizon (${autonomyMetric.toUpperCase()}):</span><span class="tooltip-value highlight-score">${timeDisplay}</span></div>
                    <div class="tooltip-row"><span class="tooltip-label">Release Date:</span><span class="tooltip-value">${d.releaseDate.toLocaleDateString()}</span></div>
                    ${d.compute ? `<div class="tooltip-row"><span class="tooltip-label">Training Compute:</span><span class="tooltip-value">${formatScale(d.compute)} FLOP</span></div>` : ''}
                `)
                .style("left", (event.pageX + 20) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mousemove", (event) => {
            tooltip.style("left", (event.pageX + 20) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseout", (event) => {
            d3.select(event.currentTarget).attr("r", 6).attr("opacity", 0.8).attr("stroke-width", 1.5);
            tooltip.style("opacity", 0);
        });

    // Update legend
    renderLegend(orgs);
}

window.addEventListener('resize', () => {
    const newWidth = document.getElementById('chart').clientWidth - margin.left - margin.right;
    const newHeight = document.getElementById('chart').clientHeight - margin.top - margin.bottom;
    d3.select('svg')
        .attr('width', newWidth + margin.left + margin.right)
        .attr('height', newHeight + margin.top + margin.bottom);
    // Rough redraw
    location.reload();
});
