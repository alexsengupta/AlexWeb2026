// Panel Management
let activePanelId = null;
let activeButton = null;

function openPanel(id, btn) {
    // If clicking the same button, close it
    if (activePanelId === id) {
        closePanel(id);
        return;
    }

    // Close any currently open panel
    if (activePanelId) {
        closePanel(activePanelId);
    }

    const panel = document.getElementById(id);
    if (panel) {
        // Force iframe reload to ensure latest content (cache busting)
        const iframe = panel.querySelector('iframe');
        if (iframe) {
            const baseUrl = iframe.getAttribute('src').split('?')[0];
            iframe.src = `${baseUrl}?v=${new Date().getTime()}`;
        }

        // Load AI News content
        if (id === 'ai-news-panel') {
            loadAINews();
        }

        panel.classList.add('active');
        // Prevent body scroll when modal is open
        document.body.style.overflow = 'hidden';

        if (btn) {
            btn.classList.add('active');
            activeButton = btn;
        }
        activePanelId = id;
    }
}

// Parse AI news markdown into HTML
function parseAINewsMarkdown(markdown) {
    const lines = markdown.split('\n');
        let html = '';
        let inArticles = false;
        let inPodcasts = false;
        let currentItem = {};
        let itemCounter = 0;

        const finishItem = () => {
            if (!currentItem.title) return;

            itemCounter++;
            const detailId = `detail-${itemCounter}`;

            if (inArticles) {
                // Article format
                html += `<div style="margin-bottom: 20px; padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #3498db; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">`;
                html += `<a href="${currentItem.url}" target="_blank" style="text-decoration: none; color: inherit; display: block; margin-bottom: 8px;">`;
                html += `<strong style="color: #2c3e50; font-size: 1.1em;">${currentItem.source}: ${currentItem.title}</strong>`;
                html += `</a>`;
                html += `<p style="margin: 8px 0; color: #555; line-height: 1.5;">${currentItem.oneLine}</p>`;
                html += `<details style="margin-top: 12px;">`;
                html += `<summary style="cursor: pointer; color: #3498db; font-size: 0.9em; user-select: none;">Show details...</summary>`;
                html += `<div style="margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 4px;">`;
                html += `<p style="line-height: 1.6; color: #2c3e50; margin-bottom: 10px;">${currentItem.detailed}</p>`;
                if (currentItem.keywords) {
                    html += `<p style="font-size: 0.85em; color: #7f8c8d;"><strong>Keywords:</strong> ${currentItem.keywords}</p>`;
                }
                html += `</div></details>`;
                html += `</div>`;
            } else if (inPodcasts) {
                // Podcast format
                html += `<div style="margin-bottom: 20px; padding: 16px; background: white; border-radius: 8px; border-left: 4px solid #9b59b6; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">`;
                html += `<a href="${currentItem.url}" target="_blank" style="text-decoration: none; color: #2c3e50; display: block; margin-bottom: 8px;">`;
                html += `<strong style="font-size: 1.1em;">${currentItem.title}</strong>`;
                html += `</a>`;
                html += `<p style="margin: 8px 0; color: #555; line-height: 1.6;">${currentItem.summary}</p>`;
                html += `</div>`;
            }
            currentItem = {};
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();

            // Check for main sections
            if (line.startsWith('# AI & AGI News Briefing')) {
                html += `<h1 style="color: #1a252f; margin-bottom: 24px; font-size: 1.8em; border-bottom: 3px solid #3498db; padding-bottom: 10px;">AI & AGI News Briefing</h1>`;
                inArticles = true;
                continue;
            }

            if (line.startsWith('# AI & AGI Podcast Episodes')) {
                finishItem();
                html += `<h1 style="color: #1a252f; margin: 32px 0 24px 0; font-size: 1.8em; border-bottom: 3px solid #9b59b6; padding-bottom: 10px;">AI & AGI Podcast Episodes</h1>`;
                inArticles = false;
                inPodcasts = true;
                continue;
            }

            // Skip separator lines and footer text
            if (line.startsWith('---') || line.startsWith('If you\'d like') || line.startsWith('_Generated') || line.startsWith('_Tokens') || line.startsWith('_Cost')) {
                continue;
            }

            // Parse article items
            if (inArticles && line.match(/^## N\d+\./)) {
                finishItem();
                currentItem.title = line.replace(/^## N\d+\.\s*/, '');
            } else if (line.startsWith('- **Source:**')) {
                currentItem.source = line.replace('- **Source:**', '').trim();
            } else if (line.startsWith('- **URL:**')) {
                const urlText = line.replace('- **URL:**', '').trim();
                // Extract URL from markdown link format [text](url)
                const urlMatch = urlText.match(/\[.*?\]\((.*?)\)/);
                currentItem.url = urlMatch ? urlMatch[1] : urlText;
            } else if (line.startsWith('- **One-line summary:**')) {
                currentItem.oneLine = line.replace('- **One-line summary:**', '').trim();
            } else if (line.startsWith('- **Detailed summary')) {
                currentItem.detailed = line.replace(/- \*\*Detailed summary[^:]*:\*\*/, '').trim();
            } else if (line.startsWith('- **Keywords')) {
                currentItem.keywords = line.replace(/- \*\*Keywords[^:]*:\*\*/, '').trim();
            }

            // Parse podcast items
            if (inPodcasts && line.match(/^## P\d+\./)) {
                finishItem();
                currentItem.title = line.replace(/^## P\d+\.\s*/, '');
            } else if (line.startsWith('- **Show:**')) {
                // Skip - already in title
            } else if (line.startsWith('- **Episode:**')) {
                // Skip - already in title
            } else if (line.startsWith('- **Summary')) {
                currentItem.summary = line.replace(/- \*\*Summary[^:]*:\*\*/, '').trim();
            } else if (line.startsWith('- **URL:**')) {
                const urlText = line.replace('- **URL:**', '').trim();
                // Extract URL from markdown link format [text](url)
                const urlMatch = urlText.match(/\[.*?\]\((.*?)\)/);
                currentItem.url = urlMatch ? urlMatch[1] : urlText;
            }
        }

        finishItem(); // Don't forget the last item

    return html;
}

// Load and display AI news from markdown file
async function loadAINews() {
    const contentDiv = document.getElementById('ai-news-content');
    try {
        // Load latest news
        const response = await fetch('AI_RSSfeed/ai_news_outputs/ai_news_latest.md?v=' + new Date().getTime());
        if (!response.ok) throw new Error('Failed to load AI news');

        const markdown = await response.text();
        let html = parseAINewsMarkdown(markdown);

        // Load archives
        try {
            const archiveResponse = await fetch('AI_RSSfeed/ai_news_outputs/archive_index.json?v=' + new Date().getTime());
            if (archiveResponse.ok) {
                const archiveIndex = await archiveResponse.json();

                if (archiveIndex.archives && archiveIndex.archives.length > 0) {
                    html += `<div style="margin-top: 48px; padding-top: 24px; border-top: 2px solid #ddd;">`;
                    html += `<h2 style="color: #1a252f; margin-bottom: 20px; font-size: 1.4em;">📚 News Archives</h2>`;

                    for (const archive of archiveIndex.archives) {
                        // Create collapsible section for each archive
                        html += `<details style="margin-bottom: 16px; border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: #f9f9f9;">`;
                        html += `<summary style="cursor: pointer; font-weight: bold; color: #2c3e50; font-size: 1.1em; user-select: none;">`;
                        html += `📅 ${archive.display_date}`;
                        html += `</summary>`;
                        html += `<div class="archive-content" data-filename="${archive.filename}" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #ddd;">`;
                        html += `<p style="color: #7f8c8d; font-style: italic;">Loading archive...</p>`;
                        html += `</div>`;
                        html += `</details>`;
                    }

                    html += `</div>`;
                }
            }
        } catch (archiveError) {
            console.warn('Could not load archive index:', archiveError);
        }

        contentDiv.innerHTML = html;

        // Set up event listeners for archive expansion
        document.querySelectorAll('.archive-content').forEach(archiveDiv => {
            const details = archiveDiv.closest('details');
            if (details) {
                details.addEventListener('toggle', async function() {
                    if (this.open && archiveDiv.innerHTML.includes('Loading archive...')) {
                        const filename = archiveDiv.dataset.filename;
                        try {
                            const archiveResponse = await fetch(`AI_RSSfeed/ai_news_outputs/${filename}?v=${new Date().getTime()}`);
                            if (archiveResponse.ok) {
                                const archiveMarkdown = await archiveResponse.text();
                                archiveDiv.innerHTML = parseAINewsMarkdown(archiveMarkdown);
                            } else {
                                archiveDiv.innerHTML = '<p style="color: #e74c3c;">Failed to load archive.</p>';
                            }
                        } catch (error) {
                            archiveDiv.innerHTML = '<p style="color: #e74c3c;">Error loading archive: ' + error.message + '</p>';
                        }
                    }
                });
            }
        });

    } catch (error) {
        contentDiv.innerHTML = '<p style="color: #e74c3c;">Error loading AI news: ' + error.message + '</p><p>Please check that the file exists at: AI_RSSfeed/ai_news_outputs/ai_news_latest.md</p>';
    }
}

function closePanel(id) {
    const panel = document.getElementById(id);
    if (panel) {
        panel.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (activeButton) {
        activeButton.classList.remove('active');
        activeButton = null;
    }
    activePanelId = null;
}

// Close on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const activePanel = document.querySelector('.modal-panel.active');
        if (activePanel) closePanel(activePanel.id);
    }
});

(() => {
    const SVG_NS = 'http://www.w3.org/2000/svg';

    const TAU = Math.PI * 2;

    const tooltip = document.createElement('div');
    tooltip.className = 'dial-tooltip';
    document.body.appendChild(tooltip);

    const statusEl = document.createElement('div');
    statusEl.className = 'dial-status';
    statusEl.textContent = 'Loading papers...';
    document.body.appendChild(statusEl);

    const tooltipState = { visible: false, text: '' };

    const showTooltip = (text) => {
        if (!text) return;
        tooltipState.text = text;
        tooltip.textContent = text;
        if (!tooltipState.visible) {
            tooltipState.visible = true;
            tooltip.classList.add('is-visible');
        }
    };

    const hideTooltip = () => {
        if (!tooltipState.visible) return;
        tooltipState.visible = false;
        tooltipState.text = '';
        tooltip.classList.remove('is-visible');
        tooltip.style.transform = 'translate(-9999px, -9999px)';
    };

    const positionTooltip = (x, y) => {
        if (!tooltipState.visible) return;
        const offsetX = 22;
        const offsetY = 22;
        const minX = 12;
        const minY = 12;
        const maxX = window.innerWidth - tooltip.offsetWidth - 24;
        const maxY = window.innerHeight - tooltip.offsetHeight - 24;
        const nextX = Math.min(Math.max(minX, x + offsetX), maxX);
        const nextY = Math.min(Math.max(minY, y + offsetY), maxY);
        tooltip.style.transform = `translate(${nextX}px, ${nextY}px)`;
    };

    const degToRad = (deg) => (deg * Math.PI) / 180;

    const computeColors = (count, offset = 216) =>
        Array.from({ length: count }, (_, idx) => {
            const hue = (offset + idx * (360 / count)) % 360;
            return [
                { offset: '0%', color: `hsla(${hue}, 82%, 68%, 0.95)` },
                { offset: '65%', color: `hsla(${(hue + 18) % 360}, 70%, 48%, 0.92)` },
                { offset: '100%', color: `hsla(${(hue + 36) % 360}, 65%, 36%, 0.88)` }
            ];
        });

    const wrapTextLines = (text, maxCharsPerLine, maxLines) => {
        if (!text) return [''];
        if (maxLines === 1) return [text];
        const words = text.split(/\s+/).filter(Boolean);
        if (!words.length) return [text];
        const lines = [];
        let current = '';
        words.forEach((word) => {
            const candidate = current ? `${current} ${word}` : word;
            if (candidate.length <= maxCharsPerLine) {
                current = candidate;
            } else {
                if (current) lines.push(current);
                current = word;
            }
        });
        if (current) lines.push(current);
        if (lines.length > maxLines) {
            const trimmed = lines.slice(0, maxLines);
            let last = trimmed[trimmed.length - 1];
            last = last.replace(/[\s\-–—,:;]+$/, '');
            if (last.length >= maxCharsPerLine) {
                last = last.slice(0, maxCharsPerLine - 1).replace(/[\s\-–—,:;]+$/, '');
            }
            trimmed[trimmed.length - 1] = `${last}…`;
            return trimmed;
        }
        return lines;
    };

    const createArcDial = (el, options) => {
        const defaults = {
            outerRadius: 360,
            innerRadius: 240,
            viewportInner: 180,
            viewportOuter: 360,
            iconOrbit: 300,
            thumbRadius: 60,
            windowStart: degToRad(-90),
            windowEnd: degToRad(-8),
            edgeThreshold: degToRad(9),
            spinSpeedBase: degToRad(0.5),
            spinSpeedBoost: degToRad(1),
            snapSpring: 0.14,
            idleThreshold: degToRad(0.0004),
            lineHeight: 1.2,
            showTooltip: true,
            labelMode: 'svg',
            pointerMode: 'edges', // 'edges' for top/bottom zones, 'sides' for left/right zones
            onlyActiveInteractive: false, // If true, only center segment is clickable
            centerLabel: false, // If true, show center label display
            scaleCenter: false, // If true, scale center segment larger
            useClipping: true, // If false, don't apply clip path (for full circle dials)
            initialRotation: 0,
            items: [],
            label: {
                maxLines: 1,
                maxCharsPerLine: 18
            },
            labelClickable: false,
            labelPosition: 'above-icon', // Changed to 'above-icon'
            hideSegments: false,
            labelHit: {
                thickness: 0
            },
            hitArea: {
                innerOffset: 0,
                outerOffset: 0
            },
            iconSize: 40
        };

        const settings = {
            ...defaults,
            ...options,
            label: {
                ...defaults.label,
                ...(options && options.label)
            },
            labelClickable: options && typeof options.labelClickable === 'boolean'
                ? options.labelClickable
                : defaults.labelClickable,
            labelHit: {
                ...defaults.labelHit,
                ...((options && options.labelHit) || {})
            },
            hitArea: {
                ...defaults.hitArea,
                ...((options && options.hitArea) || {})
            },
            items: (options && options.items ? options.items : []).slice()
        };

        const svg = el.querySelector('svg');
        if (!svg) { return; }

        const segmentsGroup = svg.querySelector('.segments');
        const clipPathNode = svg.querySelector('path[id$="viewport-window"]');
        const paletteGroup = svg.querySelector('.dial-palette');
        let svgDefs = svg.querySelector('defs');
        if (!svgDefs) {
            svgDefs = document.createElementNS(SVG_NS, 'defs');
            svg.insertBefore(svgDefs, svg.firstChild);
        }
        const point = svg.createSVGPoint();
        const screenPoint = svg.createSVGPoint();

        const overlayId = `${el.id || 'dial'}-labels-overlay`;
        let labelsOverlay = document.getElementById(overlayId);
        if (!labelsOverlay) {
            labelsOverlay = document.createElement('div');
            labelsOverlay.id = overlayId;
            labelsOverlay.className = 'dial-labels-overlay';
            document.body.appendChild(labelsOverlay);
        }

        // Fix Selector: Target the container parent, not the label itself
        const centerContainer = el.querySelector('.dial-center');

        // Update Center Label
        const updateCenterText = (forceItem = null) => {
            if (!centerContainer) return;

            if (settings.centerLabel === false && !forceItem) return;

            // Strict Tooltip Mode: Only show if explicitly hovered (forceItem exists)
            const item = forceItem;

            const titleEl = centerContainer.querySelector('.dial-center-label');
            const subEl = centerContainer.querySelector('.dial-center-sub');

            if (!item) {
                if (titleEl) titleEl.textContent = '';
                if (subEl) subEl.textContent = '';
                return;
            }

            if (titleEl) {
                titleEl.textContent = item.tooltip || '';
            }
            if (subEl) {
                subEl.textContent = '';
            }
        };

        let yearDisplay = svg.querySelector('.dial-year-display');
        if (!yearDisplay && settings.showYearDisplay) {
            yearDisplay = document.createElementNS(SVG_NS, 'text');
            yearDisplay.classList.add('dial-year-display');
            yearDisplay.setAttribute('x', '-120');
            yearDisplay.setAttribute('y', '-120');
            yearDisplay.setAttribute('text-anchor', 'middle');
            yearDisplay.setAttribute('dominant-baseline', 'middle');
            yearDisplay.setAttribute('alignment-baseline', 'middle');
            yearDisplay.setAttribute('font-size', '54');
            yearDisplay.setAttribute('fill', '#e4e9fa');
            yearDisplay.setAttribute('font-weight', 'bold');
            yearDisplay.setAttribute('opacity', '0.92');
            svg.appendChild(yearDisplay);
        }

        let colors = settings.colorStrategy
            ? settings.items.map(settings.colorStrategy)
            : (settings.colors || computeColors(Math.max(settings.items.length, 1)));
        let angleStep = settings.items.length ? TAU / settings.items.length : TAU;

        const maxRadius = Math.max(settings.outerRadius, settings.iconOrbit ? settings.iconOrbit + (settings.iconSize || 0) : 0);
        const viewExtent = maxRadius + 600; // Aggressive buffer for text
        svg.setAttribute('viewBox', `${-viewExtent} ${-viewExtent} ${viewExtent * 2} ${viewExtent * 2}`);
        svg.style.overflow = 'visible';

        const state = {
            rotation: settings.initialRotation,
            spinDirection: 0,
            edgeBoost: 0,
            raf: null,
            segments: [],
            needsRender: true,
            activeItem: null, // Track the currently active (centered) item
            hoveredItem: null // Track hovered item for sync logic
        };

        const wrapAngle = (angle) => {
            let a = angle % TAU;
            if (a < 0) a += TAU;
            return a;
        };

        const shortDiff = (a, b) => {
            let diff = wrapAngle(a) - wrapAngle(b);
            if (diff > Math.PI) diff -= TAU;
            if (diff < -Math.PI) diff += TAU;
            return diff;
        };

        const angleWithin = (angle, start, end) => {
            const s = wrapAngle(start);
            const e = wrapAngle(end);
            const a = wrapAngle(angle);
            return s <= e ? (a >= s && a <= e) : (a >= s || a <= e);
        };

        const polar = (radius, angle) => ({
            x: radius * Math.cos(angle),
            y: radius * -Math.sin(angle)
        });

        const donutSlicePath = (innerR, outerR, start, end) => {
            const largeArc = Math.abs(end - start) > Math.PI ? 1 : 0;
            const p1 = polar(outerR, start);
            const p2 = polar(outerR, end);
            const p3 = polar(innerR, end);
            const p4 = polar(innerR, start);
            return [
                `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`,
                `A ${outerR.toFixed(2)} ${outerR.toFixed(2)} 0 ${largeArc} 0 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`,
                `L ${p3.x.toFixed(2)} ${p3.y.toFixed(2)}`,
                `A ${innerR.toFixed(2)} ${innerR.toFixed(2)} 0 ${largeArc} 1 ${p4.x.toFixed(2)} ${p4.y.toFixed(2)}`,
                'Z'
            ].join(' ');
        };

        const svgPointFromEvent = (ev) => {
            point.x = ev.clientX;
            point.y = ev.clientY;
            const ctm = svg.getScreenCTM();
            if (!ctm) return { x: 0, y: 0 };
            return point.matrixTransform(ctm.inverse());
        };

        const svgPointToScreen = (x, y) => {
            screenPoint.x = x;
            screenPoint.y = y;
            const ctm = svg.getScreenCTM();
            if (!ctm) return { x: 0, y: 0 };
            const transformed = screenPoint.matrixTransform(ctm);
            return { x: transformed.x, y: transformed.y };
        };

        const buildClipWindow = () => {
            if (!clipPathNode) return;
            const d = donutSlicePath(settings.viewportInner, settings.viewportOuter, settings.windowStart, settings.windowEnd);
            clipPathNode.setAttribute('d', d);
        };

        const setLabelText = (node, text) => {
            node.textContent = '';
            const lines = wrapTextLines(text, settings.label.maxCharsPerLine, settings.label.maxLines);
            const lineCount = lines.length;
            const lh = settings.lineHeight || 1.2;
            const startOffset = lineCount > 1 ? -((lineCount - 1) / 2) * lh : 0;
            lines.forEach((line, idx) => {
                const span = document.createElementNS(SVG_NS, 'tspan');
                span.setAttribute('x', '0');
                const dy = lineCount === 1
                    ? 0
                    : (idx === 0 ? startOffset : lh);
                span.setAttribute('dy', `${dy}em`);
                span.textContent = line;
                node.appendChild(span);
            });
        };

        const createSegments = () => {
            paletteGroup.innerHTML = '';
            segmentsGroup.innerHTML = '';

            const backgroundsGroup = document.createElementNS(SVG_NS, 'g');
            backgroundsGroup.classList.add('segment-backgrounds');
            if (settings.useClipping && clipPathNode) {
                backgroundsGroup.setAttribute('clip-path', `url(#${clipPathNode.parentElement.id})`);
            }

            const labelsGroup = document.createElementNS(SVG_NS, 'g');
            labelsGroup.classList.add('segment-labels');
            labelsGroup.style.pointerEvents = 'none'; // Ensure events pass through to hitPaths

            const iconsGroup = document.createElementNS(SVG_NS, 'g');
            iconsGroup.classList.add('segment-icons');
            iconsGroup.style.pointerEvents = 'none'; // Ensure events pass through to hitPaths

            segmentsGroup.appendChild(backgroundsGroup);
            segmentsGroup.appendChild(labelsGroup);
            segmentsGroup.appendChild(iconsGroup);

            if (labelsOverlay) labelsOverlay.innerHTML = '';
            state.segments = [];
            if (!settings.items.length) return;

            settings.items.forEach((item, idx) => {
                let stops = colors[idx];
                if (!Array.isArray(stops)) {
                    stops = [
                        { offset: '0%', color: '#5e8bff' },
                        { offset: '55%', color: '#3f66d9' },
                        { offset: '100%', color: '#24388f' }
                    ];
                }
                const grad = document.createElementNS(SVG_NS, 'radialGradient');
                grad.id = `${el.id || 'dial'}-grad-${idx}`;
                grad.setAttribute('cx', '50%');
                grad.setAttribute('cy', '44%');
                grad.setAttribute('r', '82%');
                grad.innerHTML = stops.map(
                    (stop) => `<stop offset="${stop.offset}" stop-color="${stop.color}"></stop>`
                ).join('');
                svgDefs.appendChild(grad);

                const group = document.createElementNS(SVG_NS, 'g');
                group.classList.add('segment');
                group.setAttribute('role', 'menuitem');
                group.setAttribute('tabindex', '-1');
                group.dataset.index = String(idx);

                const hitPath = document.createElementNS(SVG_NS, 'path');
                hitPath.classList.add('segment-hit');
                // Ensure hit path has paint for efficient hit testing - increased opacity for reliable detection
                hitPath.style.fill = 'rgba(255, 255, 255, 0.01)';
                hitPath.style.stroke = 'transparent';
                hitPath.style.strokeWidth = '1px';
                hitPath.style.pointerEvents = 'auto'; // Explicitly enable pointer events
                hitPath.setAttribute('tabindex', '-1');
                hitPath.setAttribute('aria-hidden', 'true');

                const path = document.createElementNS(SVG_NS, 'path');
                path.classList.add('segment-path');
                if (settings.hideSegments) {
                    path.style.display = 'none'; // Completely hide visual segment
                }
                path.setAttribute('fill', `url(#${grad.id})`);
                path.style.fill = `url(#${grad.id})`;
                path.setAttribute('tabindex', '-1');

                const labelHit = (settings.labelClickable && settings.labelMode === 'svg' && settings.labelHit.thickness > 0)
                    ? document.createElementNS(SVG_NS, 'path')
                    : null;
                if (labelHit) {
                    labelHit.classList.add('segment-label-hit');
                    // DEBUG: Visuals reset to transparent
                    labelHit.setAttribute('fill', 'rgba(0,0,0,0)'); // Transparent
                    labelHit.setAttribute('stroke', 'none');
                    labelHit.setAttribute('stroke-width', '0');
                    labelHit.style.pointerEvents = 'auto'; // Ensure it captures events
                    labelHit.setAttribute('tabindex', '-1');
                    labelHit.setAttribute('aria-hidden', 'true');
                    // labelHit.style.pointerEvents = 'none'; // Commented out for debug visibility
                }

                const label = settings.labelMode === 'overlay'
                    ? document.createElement('div')
                    : document.createElementNS(SVG_NS, 'text');

                label.className = 'segment-label';
                label.setAttribute('aria-hidden', 'true');
                label.style.pointerEvents = 'none'; // Disable pointer events on labels to prevent flickering
                if (settings.labelClickable) {
                    label.classList.add('is-clickable');
                }

                if (settings.labelMode === 'svg') {
                    label.setAttribute('text-anchor', 'middle');
                    label.setAttribute('alignment-baseline', 'middle');
                    setLabelText(label, item.display || item.label || '');
                    if (labelHit) labelsGroup.appendChild(labelHit);
                    labelsGroup.appendChild(label);
                } else {
                    const lines = wrapTextLines(item.display || item.label || '', settings.label.maxCharsPerLine, settings.label.maxLines);
                    lines.forEach((l, li) => {
                        const span = document.createElement('span');
                        span.textContent = l;
                        label.appendChild(span);
                        if (li !== lines.length - 1) label.appendChild(document.createElement('br'));
                    });
                    labelsOverlay.appendChild(label);
                }

                let iconInfo = null;
                if (item.icon) {
                    const iconSize = settings.iconSize || 40;

                    // Create a group for the icon to handle positioning
                    const iconG = document.createElementNS(SVG_NS, 'g');
                    iconsGroup.appendChild(iconG);

                    const img = document.createElementNS(SVG_NS, 'image');
                    img.setAttributeNS('http://www.w3.org/1999/xlink', 'href', item.icon);
                    img.setAttribute('width', iconSize);
                    img.setAttribute('height', iconSize);
                    img.setAttribute('x', -iconSize / 2); // Center within group
                    img.setAttribute('y', -iconSize / 2);
                    img.setAttribute('class', 'segment-icon');
                    img.style.pointerEvents = 'none'; // DISABLE direct events. Pass through to wedge.
                    img.style.opacity = '0.7'; // Base opacity
                    img.style.transition = 'opacity 0.3s ease, transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.27), filter 0.3s ease';

                    // CSS Hover Effect
                    const styleId = `hover-style-${Math.random().toString(36).substr(2, 9)}`;
                    img.setAttribute('data-style-id', styleId);
                    // We can rely on global CSS instead of inline scripts

                    iconG.appendChild(img);
                    iconInfo = { group: iconG, el: img, size: iconSize };
                }

                const tooltipText = item.tooltip || item.label || item.display || '';
                const segData = { group, path, hitPath, labelHit, label, iconInfo, tooltipText, item, tooltipPos: null, isSelectable: true };

                const openTarget = (ev) => {
                    if (ev) ev.preventDefault();
                    if (settings.onlyActiveInteractive && !segData.isSelectable) return;
                    if (!item.url) return;
                    if (item.url.startsWith('#')) {
                        const target = document.querySelector(item.url);
                        if (target && target.scrollIntoView) {
                            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        } else {
                            window.location.hash = item.url.slice(1);
                        }
                        return;
                    }
                    const absoluteLink = /^(https?:)?\/\//i.test(item.url) || item.url.startsWith('mailto:');
                    if (absoluteLink) {
                        window.open(item.url, '_blank', 'noopener,noreferrer');
                    } else {
                        window.location.href = item.url;
                    }
                };

                const setActive = (active) => {
                    if (settings.onlyActiveInteractive && !segData.isSelectable) return;
                    group.classList.toggle('active', active);
                };

                const getTooltipPosition = () => {
                    const pos = segData.tooltipPos;
                    if (pos && Number.isFinite(pos.x) && Number.isFinite(pos.y)) return pos;
                    const box = path.getBoundingClientRect();
                    return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
                };

                const handlePointerEnter = (ev) => {
                    setActive(true);
                    if (settings.showTooltip) {
                        showTooltip(tooltipText);
                        positionTooltip(ev.clientX, ev.clientY);
                    }
                };

                const handlePointerMove = (ev) => {
                    if (settings.showTooltip && tooltipState.visible) {
                        positionTooltip(ev.clientX, ev.clientY);
                    }
                };

                const handlePointerLeave = () => {
                    setActive(false);
                    if (settings.showTooltip) hideTooltip();
                };

                const handleFocus = () => {
                    setActive(true);
                    if (settings.showTooltip) {
                        showTooltip(tooltipText);
                        const pos = getTooltipPosition();
                        positionTooltip(pos.x, pos.y);
                    }
                };

                const handleBlur = () => {
                    setActive(false);
                    if (settings.showTooltip) hideTooltip();
                };

                const handleKeyDown = (ev) => {
                    if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault();
                        openTarget(ev);
                    }
                };

                const attachInteractive = (node, includeKeyboard = false) => {
                    if (!node) return;
                    node.addEventListener('pointerenter', handlePointerEnter);
                    node.addEventListener('pointermove', handlePointerMove);
                    node.addEventListener('pointerleave', handlePointerLeave);
                    node.addEventListener('click', openTarget);
                    if (includeKeyboard) {
                        node.addEventListener('focus', handleFocus);
                        node.addEventListener('blur', handleBlur);
                        node.addEventListener('keydown', handleKeyDown);
                    }
                };

                // Only attach click and keyboard to group - pointer hover handled by hitPath to prevent conflicts
                group.addEventListener('click', openTarget);
                group.addEventListener('focus', handleFocus);
                group.addEventListener('blur', handleBlur);
                group.addEventListener('keydown', handleKeyDown);

                if (settings.labelClickable) {
                    attachInteractive(label, false);
                    if (segData.labelHit) {
                        attachInteractive(segData.labelHit, false);
                    }
                }

                group.append(hitPath);
                group.append(path);

                // CRITICAL FIX: Append the segment group to the backgrounds group so it exists in DOM
                backgroundsGroup.appendChild(group);

                const onEnter = () => {
                    console.log('DEBUG: onEnter Triggered for', item.label);
                    state.hoveredItem = item;
                    state.needsRender = true; // Trigger render to update highlighting
                    updateCenterText(item);
                    setActive(true); // Set active state for hover styling
                };
                const onLeave = () => {
                    if (state.hoveredItem === item) {
                        state.hoveredItem = null;
                        state.needsRender = true;
                        updateCenterText(null);
                        setActive(false); // Remove active state
                    }
                };

                // Initial clear
                updateCenterText(null);

                segData.hitPath.addEventListener('pointerenter', onEnter);
                segData.hitPath.addEventListener('pointerleave', onLeave);

                // Remove redundant listeners on visuals to prevent flickering.
                // Rely 100% on the Hit Wedge (hitPath).
                // Ensure visual groups are transparent to events via CSS/JS.
                if (segData.iconInfo) {
                    segData.iconInfo.group.style.pointerEvents = 'none';
                }
                if (segData.labelHit) {
                    segData.labelHit.style.pointerEvents = 'none';
                }

                segData.group.appendChild(path);

                backgroundsGroup.append(group);
                state.segments.push(segData);
            });
        };

        const renderSegments = () => {
            if (!state.segments.length) return;
            const pad = degToRad(2.4);
            angleStep = settings.items.length ? TAU / settings.items.length : TAU;
            let centerIdx = null;
            let maxVisible = Infinity;
            const arcCenter = (settings.windowStart + settings.windowEnd) / 2;

            state.segments.forEach((seg, idx) => {
                const start = state.rotation + idx * angleStep;
                const end = start + angleStep;
                const mid = start + angleStep / 2;

                const visible = angleWithin(mid, settings.windowStart + pad, settings.windowEnd - pad);
                const dist = Math.abs(shortDiff(mid, arcCenter));
                if (visible && dist < maxVisible) {
                    maxVisible = dist;
                    centerIdx = idx;
                }
            });

            const hitInnerOffset = (settings.hitArea && settings.hitArea.innerOffset) || 0;
            const hitOuterOffset = (settings.hitArea && settings.hitArea.outerOffset) || 0;

            state.segments.forEach((seg, idx) => {
                const start = state.rotation + idx * angleStep;
                const end = start + angleStep;
                const mid = start + angleStep / 2;
                const isCenter = idx === centerIdx;

                const innerR = settings.scaleCenter && isCenter
                    ? settings.innerRadius - 14
                    : settings.innerRadius;
                const outerR = settings.scaleCenter && isCenter
                    ? settings.outerRadius + 12
                    : settings.outerRadius;

                const pathD = donutSlicePath(innerR, outerR, start, end);
                seg.path.setAttribute('d', pathD);

                if (seg.hitPath) {
                    const hitInner = Math.max(0, innerR - hitInnerOffset);
                    const hitOuter = outerR + hitOuterOffset;
                    seg.hitPath.setAttribute('d', donutSlicePath(hitInner, hitOuter, start, end));
                }

                if (settings.labelMode === 'svg') {
                    const labelRadius = (innerR + outerR) / 2;
                    const { x, y } = polar(labelRadius, mid);
                    seg.label.setAttribute('transform', `translate(${x.toFixed(2)},${y.toFixed(2)})`);

                    if (settings.scaleCenter) {
                        seg.label.style.fontSize = isCenter ? 'clamp(27px, 3.6vw, 42px)' : 'clamp(18px, 2.4vw, 27px)';
                        seg.label.style.fontWeight = '400';
                    }

                    if (seg.labelHit && settings.labelHit.thickness > 0) {
                        const desiredThickness = Math.min(settings.labelHit.thickness, Math.max(4, outerR - innerR));
                        const halfThickness = desiredThickness / 2;
                        const bandInner = Math.max(innerR, labelRadius - halfThickness);
                        const bandOuter = Math.min(outerR, labelRadius + halfThickness);
                        seg.labelHit.setAttribute('d', donutSlicePath(bandInner, bandOuter, start, end));
                    }
                } else {
                    const svgRect = svg.getBoundingClientRect();
                    const baseRadius = settings.outerRadius;
                    const scaleFactor = Math.min(svgRect.width, svgRect.height) / (baseRadius * 2);
                    const labelOffset = Math.max(20, settings.thumbRadius * 0.6) * scaleFactor;
                    const labelRadius = (baseRadius + labelOffset);
                    const labelOrbit = polar(labelRadius, mid);
                    const lx = Number(labelOrbit.x.toFixed(2));
                    const ly = Number(labelOrbit.y.toFixed(2));

                    let screenX = 0;
                    let screenY = 0;
                    try {
                        const pt = svg.createSVGPoint();
                        pt.x = lx;
                        pt.y = ly;
                        const ctm = svg.getScreenCTM();
                        if (ctm) {
                            const transformed = pt.matrixTransform(ctm);
                            screenX = transformed.x;
                            screenY = transformed.y;
                        }
                    } catch (e) {
                        const svgCenter = {
                            x: svgRect.left + svgRect.width / 2,
                            y: svgRect.top + svgRect.height / 2
                        };
                        const scale = Math.min(svgRect.width, svgRect.height) / (baseRadius * 2);
                        screenX = svgCenter.x + lx * scale;
                        screenY = svgCenter.y + ly * scale;
                    }

                    const isRight = Math.cos(mid) >= 0;
                    const basePad = Math.max(8, Math.min(16, svgRect.width / 60));
                    const padX = isRight ? basePad : -basePad;

                    // Calculate rotation angle for radial text orientation
                    // Convert angle to degrees (negative because SVG y-axis is inverted)
                    const rotationDeg = -(mid * 180 / Math.PI);

                    // Prevent upside-down text: flip 180° for left side of dial
                    let finalRotation = rotationDeg;
                    if (!isRight) {
                        finalRotation = rotationDeg + 180;
                    }

                    if (seg.label.style) {
                        seg.label.style.left = `${Math.round(screenX)}px`;
                        seg.label.style.top = `${Math.round(screenY)}px`;
                        seg.label.style.transform = `translate(${padX}px, -50%) rotate(${finalRotation}deg)`;
                        seg.label.style.textAlign = isRight ? 'left' : 'right';
                    }
                }

                // Override label position for 'below-icon' or 'above-icon' mode
                if ((settings.labelPosition === 'below-icon' || settings.labelPosition === 'above-icon') && seg.iconInfo) {
                    const iconR = settings.iconOrbit;
                    const iconPos = polar(iconR, mid);

                    let labelYOffset = 0;
                    if (settings.labelPosition === 'above-icon') {
                        // Place above: -iconSize/2 - padding
                        labelYOffset = -(seg.iconInfo.size / 2) - 60; // Increased clearance
                    } else {
                        // Place below: +iconSize/2 + padding
                        labelYOffset = (seg.iconInfo.size / 2) + 45;
                    }

                    const lx = iconPos.x;
                    const ly = iconPos.y + labelYOffset;
                    seg.label.setAttribute('transform', `translate(${lx.toFixed(2)},${ly.toFixed(2)})`);

                    // Reset styles
                    seg.label.style.fontSize = '54px'; // Scaled 100% bigger (Link Text)
                    seg.label.style.fontWeight = '700';
                    seg.label.style.fill = '#b8c5d6'; // Darker Off-white
                    seg.label.style.textShadow = '0 3px 12px rgba(0,0,0,1)';
                    seg.label.style.pointerEvents = 'none'; // Ensure clicks pass through

                    // Manual word wrap force (simple split for now)
                    if (seg.item.label && seg.item.label.length > 15) {
                        // This is a naive wrap visualization if needed, but for now just scaling.
                    }
                }

                const visible = angleWithin(mid, settings.windowStart + pad, settings.windowEnd - pad);
                // Sync Highlight with Hover State
                const highlight = state.hoveredItem === seg.item;

                if (seg.label) {
                    // Aggressive visibility force
                    seg.label.style.opacity = '1';
                    seg.label.style.fill = '#ffffff';
                    seg.label.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.9))';
                    seg.label.style.display = 'block'; // Ensure not hidden
                    seg.label.style.pointerEvents = 'none'; // Ensure click-through to hit wedge
                }
                if (seg.iconInfo) {
                    // Highlight effect - handled by 'active' class status or hover
                    const isActive = highlight;
                    if (isActive) console.log('DEBUG: Highlighting icon', seg.item.label);
                    // Only scale/glow if it is the center item
                    seg.iconInfo.el.style.opacity = isActive ? '1' : '0.8';
                    seg.iconInfo.el.style.transform = isActive ? 'scale(1.1)' : 'scale(1)';
                    seg.iconInfo.el.style.filter = isActive ? 'drop-shadow(0 0 15px rgba(118, 163, 255, 0.5))' : 'none';

                    // Update icon group position (orbit)
                    const iconR = settings.iconOrbit;
                    const iconPos = polar(iconR, mid);
                    seg.iconInfo.group.setAttribute('transform', `translate(${iconPos.x}, ${iconPos.y})`);
                }
                if (seg.labelHit) {
                    seg.labelHit.style.pointerEvents = highlight ? 'auto' : 'none';
                }
                seg.group.setAttribute('tabindex', highlight ? '0' : '-1');
                seg.isSelectable = highlight;

                if (settings.scaleCenter) {
                    const tipRadius = outerR + 18;
                    const tip = svgPointToScreen(tipRadius * Math.cos(mid), tipRadius * -Math.sin(mid));
                    seg.tooltipPos = tip;
                }
            });

            if (settings.onlyActiveInteractive && centerIdx !== null) {
                state.segments.forEach((seg, idx) => {
                    if (idx !== centerIdx) seg.group.classList.remove('active');
                });
            }

            if (settings.showYearDisplay && yearDisplay && centerIdx !== null) {
                const segment = state.segments[centerIdx];
                const currentYear = segment.item.year || segment.item.Year;

                let yearIndicator = svg.querySelector('.year-indicator');
                if (!yearIndicator) {
                    yearIndicator = document.createElementNS(SVG_NS, 'path');
                    yearIndicator.classList.add('year-indicator');
                    yearIndicator.setAttribute('marker-end', 'url(#papers-arrow-head)');
                    svg.appendChild(yearIndicator);
                }

                if (currentYear) {
                    yearDisplay.textContent = currentYear;
                    yearDisplay.setAttribute('opacity', '0.92');
                    const bbox = yearDisplay.getBBox();
                    const startX = bbox.x;
                    const startY = bbox.y + bbox.height / 2;
                    const endX = -settings.innerRadius * 0.86;
                    const path = `M ${startX.toFixed(1)},${startY.toFixed(1)} L ${endX.toFixed(1)},${startY.toFixed(1)}`;
                    yearIndicator.setAttribute('d', path);
                    yearIndicator.style.opacity = '0.9';
                } else {
                    yearDisplay.textContent = '';
                    yearDisplay.setAttribute('opacity', '0');
                    yearIndicator.style.opacity = '0';
                }
            }
        };

        const createSectorPath = (innerRadius, outerRadius, startAngle, endAngle) => {
            const inner1 = polar(innerRadius, startAngle);
            const inner2 = polar(innerRadius, endAngle);
            const outer1 = polar(outerRadius, startAngle);
            const outer2 = polar(outerRadius, endAngle);
            const largeArcFlag = Math.abs(endAngle - startAngle) > Math.PI ? 1 : 0;
            return `M ${inner1.x} ${inner1.y}
              L ${outer1.x} ${outer1.y}
              A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outer2.x} ${outer2.y}
              L ${inner2.x} ${inner2.y}
              A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${inner1.x} ${inner1.y}
              Z`;
        };

        const pointerMove = (ev) => {
            if (!state.segments.length) return;

            // CRITICAL: If hovering over any icon, completely disable rotation to prevent conflicts
            if (state.hoveredItem) {
                state.spinDirection = 0;
                state.edgeBoost = 0;
                if (tooltipState.visible) positionTooltip(ev.clientX, ev.clientY);
                return;
            }

            const { x, y } = svgPointFromEvent(ev);
            const radius = Math.hypot(x, y);
            const angle = Math.atan2(-y, x);

            // Rotation Trigger Band:
            const iconOuterEdge = (settings.iconOrbit || 0) + ((settings.iconSize || 0) / 2);
            const rotationMinRadius = iconOuterEdge + 20;

            const inRing = radius > rotationMinRadius &&
                radius < settings.viewportOuter * 1.5;

            if (!inRing) {
                state.spinDirection = 0;
                state.edgeBoost = 0;
                if (tooltipState.visible) positionTooltip(ev.clientX, ev.clientY);
                return;
            }

            if (settings.pointerMode === 'sides') {
                const sideWidth = degToRad(110);
                const rightCenter = 0;
                const leftCenter = Math.PI;
                const inRight = angleWithin(angle, rightCenter - sideWidth / 2, rightCenter + sideWidth / 2);
                const inLeft = angleWithin(angle, leftCenter - sideWidth / 2, leftCenter + sideWidth / 2);

                if (inRight) {
                    state.spinDirection = 1;
                    const dist = Math.abs(shortDiff(angle, rightCenter));
                    const normalized = Math.min(1, dist / (sideWidth / 2));
                    state.edgeBoost = Math.max(0, 0.25 * (1 - normalized));
                } else if (inLeft) {
                    state.spinDirection = -1;
                    const dist = Math.abs(shortDiff(angle, leftCenter));
                    const normalized = Math.min(1, dist / (sideWidth / 2));
                    state.edgeBoost = Math.max(0, 0.25 * (1 - normalized));
                } else {
                    state.spinDirection = 0;
                    state.edgeBoost = 0;
                }
            } else {
                const topWidth = degToRad(18);
                const bottomWidth = degToRad(24);
                const topOffset = topWidth / 3;
                const bottomOffset = bottomWidth / 3;

                const topTrigger = {
                    center: settings.windowStart + topOffset,
                    start: settings.windowStart - topWidth / 2,
                    end: settings.windowStart + topWidth / 2
                };

                const bottomTrigger = {
                    center: settings.windowEnd - bottomOffset,
                    start: settings.windowEnd - bottomWidth / 2,
                    end: settings.windowEnd + bottomWidth / 2
                };

                const inTopZone = angleWithin(angle, topTrigger.start, topTrigger.end);
                const inBottomZone = angleWithin(angle, bottomTrigger.start, bottomTrigger.end);

                if (inTopZone) {
                    state.spinDirection = 1;
                    const dist = Math.abs(shortDiff(angle, topTrigger.center));
                    const normalized = Math.min(1, dist / (topWidth / 2));
                    state.edgeBoost = Math.max(0, 0.2 * (1 - normalized));
                } else if (inBottomZone) {
                    state.spinDirection = -1;
                    const dist = Math.abs(shortDiff(angle, bottomTrigger.center));
                    const normalized = Math.min(1, dist / (bottomWidth / 2));
                    state.edgeBoost = Math.max(0, 0.2 * (1 - normalized));
                } else {
                    state.spinDirection = 0;
                    state.edgeBoost = 0;
                }
            }

            if (tooltipState.visible) positionTooltip(ev.clientX, ev.clientY);
        };

        const pointerLeave = () => {
            state.spinDirection = 0;
            state.edgeBoost = 0;
            if (settings.showTooltip) hideTooltip();
        };

        const snapRotation = () => {
            if (!state.segments.length) return;
            const nearest = Math.round(state.rotation / angleStep) * angleStep;
            const diff = nearest - state.rotation;
            if (Math.abs(diff) < settings.idleThreshold) {
                state.rotation = wrapAngle(nearest);
                return;
            }
            state.rotation = wrapAngle(state.rotation + diff * settings.snapSpring);
            state.needsRender = true;
        };

        const debounce = (fn, delay) => {
            let timeoutId;
            return (...args) => {
                if (timeoutId) clearTimeout(timeoutId);
                timeoutId = setTimeout(() => fn.apply(null, args), delay);
            };
        };

        const handleResize = debounce(() => {
            state.needsRender = true;
        }, 100);

        const animate = () => {
            if (state.spinDirection !== 0) {
                const speed = settings.spinSpeedBase + settings.spinSpeedBoost * state.edgeBoost;
                state.rotation = wrapAngle(state.rotation + state.spinDirection * speed);
                state.needsRender = true;
            } else {
                snapRotation();
            }

            if (state.needsRender || state.lastRotation !== state.rotation) {
                try {
                    renderSegments();
                } catch (e) {
                    console.error("CRITICAL: renderSegments crashed", e);
                    state.raf = null; // Stop loop to prevent spam
                    return;
                }
                state.needsRender = false;
            }

            state.raf = requestAnimationFrame(animate);
        };

        const onKeyDown = (ev) => {
            if (!state.segments.length) return;

            if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown') {
                state.rotation = wrapAngle(state.rotation - angleStep);
                state.needsRender = true;
                ev.preventDefault();
            } else if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp') {
                state.rotation = wrapAngle(state.rotation + angleStep);
                state.needsRender = true;
                ev.preventDefault();
            }
        };

        const onFocus = (ev) => {
            if (ev.target === el) {
                const first = state.segments.find((seg) => seg.group.getAttribute('tabindex') === '0');
                if (first) first.group.focus();
            }
        };

        const init = () => {
            if (settings.useClipping) {
                buildClipWindow();
            }
            createSegments();
            renderSegments();

            el.dataset.enhanced = 'true';
            el.addEventListener('pointermove', pointerMove);
            el.addEventListener('pointerleave', pointerLeave);
            el.addEventListener('keydown', onKeyDown);
            el.addEventListener('focus', onFocus);
            window.addEventListener('resize', handleResize);

            // --- Dynamic Student Fetching ---
            async function fetchAndParsePeople() {
                try {
                    const response = await fetch('./students/postdocs_and_students.md');
                    if (!response.ok) throw new Error('Failed to load students file');
                    const text = await response.text();

                    const names = [];
                    const sectionRegex = /(?:^|\n)## Current .*?(?:\n|$)([\s\S]*?)(?:(?:\n## )|$)/g;
                    let sectionMatch;

                    while ((sectionMatch = sectionRegex.exec(text)) !== null) {
                        const sectionContent = sectionMatch[1];
                        const nameRegex = /(?:^|\n)### (?:Dr )?([A-Za-z]+)/g;
                        let nameMatch;
                        while ((nameMatch = nameRegex.exec(sectionContent)) !== null) {
                            names.push(nameMatch[1]);
                        }
                    }

                    if (names.length > 0) {
                        const formattedString = names.join(', ');
                        const researchItem = settings.items.find(i => i.label === 'Research Group');
                        if (researchItem) {
                            researchItem.tooltip = formattedString;
                        }
                    }
                } catch (e) {
                    // Ignore fetch errors
                }
            }

            // --- Initialization ---
            updateCenterText(null);
            setTimeout(() => updateCenterText(null), 100);
            fetchAndParsePeople();
            requestAnimationFrame(animate);

            return {
                setItems(nextItems) {
                    settings.items = nextItems.slice();
                    colors = settings.colorStrategy
                        ? settings.items.map(settings.colorStrategy)
                        : (settings.colors || computeColors(Math.max(settings.items.length, 1)));
                    state.rotation = settings.initialRotation;
                    if (settings.useClipping) {
                        buildClipWindow();
                    }
                    createSegments();
                    state.needsRender = true;
                },
                setArc(startDeg, endDeg) {
                    settings.windowStart = degToRad(startDeg);
                    settings.windowEnd = degToRad(endDeg);
                    if (settings.useClipping) {
                        buildClipWindow();
                    }
                    state.needsRender = true;
                }
            };
        };

        return init();
    };

    // Initialize Papers Timeline
    const papersTimelineEl = document.getElementById('papersTimeline');

    const parseYear = (value) => {
        if (!value) return undefined;
        const known = String(value).trim();
        const yearMatch = known.match(/(\d{4})/);
        if (yearMatch) {
            const year = Number(yearMatch[1]);
            return Number.isFinite(year) ? year : undefined;
        }
        return undefined;
    };

    const buildColorStopsForYear = (year, range) => {
        const [minYear, maxYear] = range;
        if (!Number.isFinite(year) || minYear === maxYear) {
            return [
                { offset: '0%', color: '#5e8bff' },
                { offset: '55%', color: '#3f66d9' },
                { offset: '100%', color: '#24388f' }
            ];
        }
        const ratio = Math.min(Math.max((year - minYear) / (maxYear - minYear), 0), 1);
        const hueOuter = 220 - ratio * 210;
        const hueInner = hueOuter + 14;
        const satOuter = 90;
        const satInner = Math.min(96, satOuter + 6);
        const lightInner = 72 - ratio * 10;
        const lightMid = 58 - ratio * 8;
        const lightOuter = 38 - ratio * 6;
        return [
            { offset: '0%', color: `hsl(${hueInner.toFixed(1)}, ${satInner}%, ${lightInner.toFixed(1)}%)` },
            { offset: '55%', color: `hsl(${(hueOuter - 6).toFixed(1)}, ${satOuter}%, ${lightMid.toFixed(1)}%)` },
            { offset: '100%', color: `hsl(${(hueOuter - 12).toFixed(1)}, ${satOuter}%, ${lightOuter.toFixed(1)}%)` }
        ];
    };

    const loadPapersRecords = async () => {
        const csvAttr = papersTimelineEl ? papersTimelineEl.dataset.csv || '' : '';
        const sources = csvAttr
            ? csvAttr.split(',').map((s) => s.trim()).filter(Boolean)
            : ['assets/data/scopus_alex_sen_gupta_articles_with_abstracts.csv'];

        const fetchCSV = async (path) => {
            const res = await fetch(path, { cache: 'no-store' });
            if (!res.ok) throw new Error(`${path} (${res.status})`);
            const text = await res.text();
            if (!text.trim()) return [];

            if (window.Papa && typeof Papa.parse === 'function') {
                const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
                if (parsed && parsed.data) return parsed.data;
            }

            const lines = text.trim().split(/\r?\n/);
            if (!lines.length) return [];
            const headers = lines.shift().split(',').map((h) => h.trim().toLowerCase());
            return lines.map((line) => {
                const cols = line.split(',');
                const obj = {};
                headers.forEach((h, i) => { obj[h] = (cols[i] || '').trim(); });
                return obj;
            });
        };

        for (const source of sources) {
            try {
                const records = await fetchCSV(source);
                if (records && records.length) return records;
            } catch (err) {
                console.warn(`Could not fetch CSV "${source}":`, err);
            }
        }
        return [];
    };

    const initPapersTimeline = (papers, minYear, maxYear) => {
        const grid = document.getElementById('papersGrid');
        const slider = document.getElementById('yearSlider');
        const yearMin = document.getElementById('yearMin');
        const yearMax = document.getElementById('yearMax');
        const yearCurrent = document.getElementById('yearCurrent');
        const paperCount = document.getElementById('paperCount');
        const yearRange = document.getElementById('yearRange');

        if (!papers || !papers.length) {
            grid.innerHTML = '<div style="padding: 20px; text-align: center; color: rgba(228, 233, 250, 0.6);">No papers available</div>';
            return;
        }

        const papersPerPage = 6;
        slider.min = 0;
        slider.max = Math.max(0, papers.length - papersPerPage);
        slider.value = 0;
        slider.step = 1;

        yearMin.textContent = maxYear;
        yearMax.textContent = minYear;
        yearRange.textContent = `${papers.length} papers (${minYear}–${maxYear})`;

        renderPapers(papers, 0, minYear, maxYear, papersPerPage);

        slider.addEventListener('input', (e) => {
            const startIndex = parseInt(e.target.value);
            renderPapers(papers, startIndex, minYear, maxYear, papersPerPage);
        });
    };

    const renderPapers = (allPapers, startIndex, minYear, maxYear, papersPerPage) => {
        const grid = document.getElementById('papersGrid');
        const paperCount = document.getElementById('paperCount');
        const yearCurrent = document.getElementById('yearCurrent');

        const visible = allPapers.slice(startIndex, startIndex + papersPerPage);

        if (visible.length > 0) {
            const firstYear = visible[0].year || '?';
            const lastYear = visible[visible.length - 1].year || '?';
            if (firstYear === lastYear) {
                yearCurrent.textContent = firstYear;
            } else {
                yearCurrent.textContent = `${lastYear}–${firstYear}`;
            }
        }

        paperCount.textContent = `Showing ${visible.length} of ${allPapers.length}`;
        grid.innerHTML = '';

        visible.forEach(paper => {
            const card = document.createElement('div');
            card.className = 'paper-card';

            const year = document.createElement('div');
            year.className = 'paper-year';
            year.textContent = paper.year || 'n/a';

            const title = document.createElement('div');
            title.className = 'paper-title';
            title.textContent = paper.label;

            card.appendChild(year);
            card.appendChild(title);

            const colorStops = buildColorStopsForYear(paper.year, [minYear, maxYear]);
            card.style.borderLeftColor = colorStops[0].color;

            card.addEventListener('pointerenter', (e) => {
                showTooltip(paper.tooltip || paper.label);
                positionTooltip(e.clientX, e.clientY);
            });

            card.addEventListener('pointermove', (e) => {
                positionTooltip(e.clientX, e.clientY);
            });

            card.addEventListener('pointerleave', () => hideTooltip());

            card.addEventListener('click', () => {
                if (paper.url) {
                    window.open(paper.url, '_blank', 'noopener,noreferrer');
                }
            });

            grid.appendChild(card);
        });

        if (visible.length === 0) {
            grid.innerHTML = '<div style="padding: 20px; text-align: center; color: rgba(228, 233, 250, 0.6);">No papers for this year range</div>';
        }
    };

    (async () => {
        const papersRecords = await loadPapersRecords();
        const normalized = (papersRecords || []).map((record) => {
            const title = record && (record.title || record.Title) ? String(record.title || record.Title).trim() : '';
            const dateField = record.date || record.Date || record.year || record.Year || '';
            const year = parseYear(dateField);
            const doi = record && (record.doi || record.DOI) ? String(record.doi || record.DOI).trim() : '';
            const journal = record && (record.journal || record.Journal) ? String(record.journal || record.Journal).trim() : '';
            const volume = record && (record.volume || record.Volume) ? String(record.volume || record.Volume).trim() : '';
            const issue = record && (record.issue || record.Issue) ? String(record.issue || record.Issue).trim() : '';
            const pages = record && (record.pages || record.Pages) ? String(record.pages || record.Pages).trim() : '';
            return { title, dateField, year, doi, journal, volume, issue, pages };
        });

        const sorted = normalized
            .filter((item) => item.title)
            .sort((a, b) => (b.year || 0) - (a.year || 0));

        const yearValues = sorted.map((item) => item.year).filter((y) => Number.isFinite(y));
        const minYear = yearValues.length ? Math.min(...yearValues) : undefined;
        const maxYear = yearValues.length ? Math.max(...yearValues) : undefined;

        if (typeof statusEl !== 'undefined' && statusEl) {
            statusEl.textContent = `Papers: ${sorted.length} | Years: ${minYear || 'n/a'}–${maxYear || 'n/a'}`;
        }

        const papers = sorted.map((record, idx) => {
            const title = record.title || `Paper ${idx + 1}`;
            const snippet = title.length > 30 ? `${title.slice(0, 27).replace(/[\s\-–—,:;]+$/, '')}…` : title;

            let citation = `${title}`;
            if (record.year) citation += ` (${record.year})`;
            if (record.journal) {
                citation += `. ${record.journal}`;
                if (record.volume) {
                    citation += `, ${record.volume}`;
                    if (record.issue) citation += `(${record.issue})`;
                }
                if (record.pages) citation += `, ${record.pages}`;
                citation += '.';
            }

            return {
                label: title,
                display: snippet,
                tooltip: citation,
                url: record.doi ? `https://doi.org/${record.doi}` : undefined,
                year: record.year
            };
        });

        if (papers.length) {
            initPapersTimeline(papers, minYear || 2000, maxYear || 2024);
        } else {
            const grid = document.getElementById('papersGrid');
            if (grid) grid.innerHTML = '<div style="padding: 20px; text-align: center; color: rgba(228, 233, 250, 0.6);">No papers available</div>';
        }
    })();

    // Initialize Nav Dial
    const navDialEl = document.getElementById('navDial');
    createArcDial(navDialEl, {
        outerRadius: 1275,
        innerRadius: 675,
        viewportInner: 675,
        viewportOuter: 1275,
        iconOrbit: 900,
        initialRotation: degToRad(-22.5),
        spinSpeedBase: degToRad(0.36),
        spinSpeedBoost: degToRad(2.4),
        snapSpring: 0.24,
        pointerMode: 'sides',
        onlyActiveInteractive: false,
        centerLabel: true,
        scaleCenter: true,
        useClipping: false,
        hideSegments: true,
        labelPosition: 'above-icon',
        labelMode: 'svg',
        showTooltip: false,
        label: { maxLines: 2, maxCharsPerLine: 24, lineHeight: 1.1 },
        labelClickable: true,
        labelHit: { thickness: 150 },
        hitArea: { outerOffset: 200 },
        iconSize: 435,
        items: [
            { label: 'Carbonator', tooltip: 'Look into the future: an easy-to-use online climate model', url: 'Carbonator.html', icon: 'assets/graphics/03-carbonator.svg' },
            { label: 'App Playground', tooltip: 'Explore all interactive web apps and simulations', url: 'app_playground.html', icon: 'assets/graphics/02-app-playground.svg' },
            { label: 'Down the AI Rabbit Hole', tooltip: 'My adventures with our intelligent alien neighbours …', url: 'AIrabbithole/index.html', icon: 'assets/graphics/01-ai-rabbit-hole.svg' },
            { label: 'Science in Pictures', tooltip: 'A picture tells a thousand words - scientific schematics …', url: 'schematics/index.html', icon: 'assets/graphics/09-science-in-pictures.svg' },
            { label: 'Research Group', tooltip: 'The future of climate science …', url: 'students/research_group_honeycomb.html', icon: 'assets/graphics/08-research-group.svg' },
            { label: 'Marine Heatwaves', tooltip: 'Latest information on ocean temperature extremes around the world', url: 'https://www.marineheatwaves.org/tracker.html', icon: 'assets/graphics/07-marine-heatwaves.svg' },
            { label: 'Teaching', tooltip: 'My courses at UNSW', url: 'teaching/teaching_portfolio.html', icon: 'assets/graphics/06-teaching.svg' },
            { label: 'Publication Briefs', tooltip: 'Simple summaries of my papers', url: 'publications/publications.html', icon: 'assets/graphics/05-publication-briefs.svg' },
            { label: 'Seminars', tooltip: 'A few of my online talks', url: 'seminars/index.html', icon: 'assets/graphics/04-seminars.svg' }
        ]
    });

    // Photo rotation for About Me section
    (() => {
        const photos = document.querySelectorAll('.about-me-photo img');
        if (!photos.length) return;

        let currentIndex = 0;
        const rotatePhotos = () => {
            photos[currentIndex].classList.remove('active');
            currentIndex = (currentIndex + 1) % photos.length;
            photos[currentIndex].classList.add('active');
        };
        setInterval(rotatePhotos, 5000);
    })();
})();
