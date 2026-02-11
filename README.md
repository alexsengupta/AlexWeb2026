# Alex Sen Gupta - Research Portal

Personal academic website combining research dissemination, interactive simulations,
climate dashboards, and automated AI news aggregation.

---

## Data Update Scripts

These Python scripts need to be run periodically (manually or via cron) to keep
the site's data fresh. Each writes a `last_updated.json` timestamp that the
corresponding web page displays as "Data last downloaded."

| Script | What it updates | Output directory |
|--------|----------------|-----------------|
| `climate indices/climate_dashboard.py` | 9 climate indices (ONI, Nino3.4, SST, T2M, sea ice, CO2, GISTEMP, PDO) from NOAA/PSL/NCAR | `climate indices/data/` |
| `AI_model_growth/update_data.py` | AI model and benchmark CSVs from epoch.ai; METR autonomy data | `AI_model_growth/example_data/` |
| `AI_RSSfeed/scanForAInews.py` | Scans 40+ RSS feeds, generates AI news briefing via OpenAI API | `AI_RSSfeed/ai_news_outputs/` |
| `AI_SLOP/update_posts.py` | Scans `AI_SLOP/markdowns/` for new articles, updates `posts.json` | `AI_SLOP/` |

### Running the scripts

```bash
# Climate data
cd "climate indices" && python climate_dashboard.py

# AI model scaling data
cd AI_model_growth && python update_data.py

# AI news briefing (requires OpenAI API key in .env)
cd AI_RSSfeed && source ai-news-env/bin/activate && python scanForAInews.py

# AI Slop blog posts (run after adding a new .md to AI_SLOP/markdowns/)
cd AI_SLOP && python update_posts.py
```

### Other utility scripts

| Script | Purpose |
|--------|---------|
| `MarineHeatwaves/fetch_map.py` | Downloads MHW tracker map PNGs (pass URL as argument) |
| `MarineHeatwaves/download_katana_csv.sh` | SCPs Scopus CSVs from Katana HPC cluster |
| `publications/pdf-summarizer/pdf_summarizer.py` | Summarises research PDFs via OpenAI API |
| `climate indices/start_server.py` | Local HTTP server on port 8080 for testing |

---

## Site Architecture

### Landing page (`index.html`)

The main entry point. A single-page layout with:

- **Top navigation bar** -- buttons that open slide-in card panels:
  - Climate Indices, AI News, AI Scaling, AI Slop
  - About Me, Dark/Light theme toggle
- **Central button grid** -- links to the main content sections (see below)
- **Publications section** -- loads from `assets/data/scopus_alex_sen_gupta_articles_with_abstracts.csv`, filterable by year slider
- **Particle animation background** with animated gradient

### Content sections

```
index.html (landing page)
│
├─ Top nav cards (slide-in panels)
│  ├─ Climate Indices ──── iframe ──► climate indices/index.html
│  │                                   └─ reads data/*.csv (from climate_dashboard.py)
│  │                                   └─ reads data/last_updated.json
│  │
│  ├─ AI News ──── fetches ──► AI_RSSfeed/ai_news_outputs/ai_news_latest.md
│  │               fetches ──► AI_RSSfeed/ai_news_outputs/last_updated.json
│  │               fetches ──► AI_RSSfeed/ai_news_outputs/archive_index.json
│  │
│  ├─ AI Scaling ──── iframe ──► AI_model_growth/index.html
│  │                              ├─ app.js (D3.js charts)
│  │                              ├─ reads example_data/ai_models/*.csv
│  │                              ├─ reads example_data/benchmark_data/*.csv
│  │                              ├─ reads METR/benchmark_results.yaml
│  │                              └─ reads example_data/last_updated.json
│  │
│  ├─ AI Slop ──── navigates to ──► AI_SLOP/index.html
│  │                                 ├─ reads posts.json (card list)
│  │                                 ├─ fetches markdowns/<slug>.md (post view)
│  │                                 └─ Giscus comments (GitHub Discussions)
│  │
│  └─ About Me ──── inline content + photo carousel
│
├─ Central grid buttons
│  ├─ Vibing for Fun ──────────► vibing.html
│  ├─ Carbonator ──────────────► Carbonator.html
│  ├─ Academic Apps ───────────► app_playground.html
│  │                              └─ links to simulations/*
│  ├─ Down the AI Rabbit Hole ► AIrabbithole/index.html
│  │                              ├─ claude_PhD_conversation.html
│  │                              └─ conceptual_models.html
│  ├─ Science in Pictures ─────► schematics/index.html
│  │                              └─ reads schematics.json
│  ├─ Research Group ──────────► students/research_group_honeycomb.html
│  │                              └─ reads research_group_data.json
│  ├─ Marine Heatwaves ────────► MarineHeatwaves/mhw.html
│  │                              ├─ all_mhw.html (full MHW literature)
│  │                              └─ subsurface.html
│  ├─ Teaching ────────────────► teaching/teaching_portfolio.html
│  ├─ Publication Briefs ──────► publications/publications.html
│  └─ Seminars ────────────────► seminars/index.html
│
└─ Publications section
   └─ reads assets/data/scopus_alex_sen_gupta_articles_with_abstracts.csv
```

### Key data flows

```
Python scripts          JSON/CSV files              Web pages
─────────────          ──────────────              ─────────

climate_dashboard.py ──► data/*.csv ──────────────► climate indices/index.html
                     ──► data/last_updated.json ──┘

update_data.py ────────► example_data/**/*.csv ───► AI_model_growth/index.html
                     ──► example_data/             (via app.js + D3)
                         last_updated.json ───────┘

scanForAInews.py ──────► ai_news_latest.md ───────► index.html (loadAINews)
                     ──► archive_index.json ──────┘
                     ──► last_updated.json ───────┘

update_posts.py ───────► posts.json ──────────────► AI_SLOP/index.html
  (scans markdowns/)     markdowns/*.md ──────────┘
```

### Interactive simulations (`simulations/`)

Accessed via `app_playground.html`. Self-contained HTML/JS apps:

| Directory | Simulation |
|-----------|-----------|
| `estuary/` | 2-layer and 3-layer estuary circulation models |
| `flocking/` | Boids flocking behaviour variants |
| `waves/` | Wave propagation models (w1--w7) |
| `predator_prey/` | Lotka-Volterra predator-prey dynamics |
| `monte_carlo_simulation/` | Monte Carlo sampling demonstrations |
| `coral_lagoon/` | Multi-year coral bleaching model |
| `counterintuitive_correlations/` | Correlation visualisation |
| `traffic_model/` | Motorway traffic simulation |
| `schelling_model/` | Schelling segregation model |
| `seasonality/` | Seasonal cycle explorer |
| `syntheticSST/` | Synthetic sea surface temperature generator |

### Shared assets

```
assets/
├── graphics/    SVG icons for the main navigation grid (01-10)
├── images/      Personal photos (About Me carousel)
└── data/        Publications CSV (Scopus export)
```

---

## Tech stack

- **Frontend:** Vanilla HTML/CSS/JS, Tailwind (publications page), Plotly.js (climate), D3.js (AI scaling), PapaParse (CSV parsing), marked.js (markdown rendering)
- **Comments:** Giscus (GitHub Discussions) on AI Slop blog
- **Python automation:** requests, pandas, BeautifulSoup, feedparser, OpenAI API
- **Hosting:** Static files (no server-side runtime required)
