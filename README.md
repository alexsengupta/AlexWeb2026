# Alex Sen Gupta - Personal Academic Website

A modern, interactive portfolio website for climate scientist and physical oceanographer Alex Sen Gupta, featuring an innovative circular navigation dial interface and dynamic content displays.

## Overview

This website showcases research, publications, teaching materials, and interactive climate simulations. The site features a custom-built "arc dial" navigation system with circular menus, a publications timeline, and various embedded applications and visualizations.

## Layout & Structure

### Landing Page (index.html)

The homepage features a distinctive layout with several key components:

- **Top Navigation Bar**: Quick access buttons for Climate Indices and AI News panels
- **Central Navigation Dial**: A circular, rotating menu with 9 main sections (icons rotate around center)
- **Publications Timeline** (right side): Scrollable list of research papers with year-based filtering
- **About Me Section** (bottom left): Biography with rotating photo gallery
- **Page Header** (top right): Name and professional roles

### Main Sections

1. **Carbonator** - Interactive climate simulator
2. **App Playground** - Collection of all web apps and simulations
3. **AI Rabbit Hole** - AI exploration and conversations
4. **Science in Pictures** - Scientific schematics and visualizations
5. **Research Group** - Student and postdoc information
6. **Marine Heatwaves** - Links to marine heatwave tracker
7. **Teaching** - Course materials and teaching portfolio
8. **Publication Briefs** - Simplified paper summaries
9. **Seminars** - Video recordings of talks

### Directory Structure

```
awesome-gates/
├── index.html                      # Main landing page
├── css/
│   └── homepage.css                # Main stylesheet (880 lines)
├── js/
│   └── homepage.js                 # Core functionality (1617 lines)
├── assets/
│   ├── data/                       # CSV data files (publications)
│   ├── graphics/                   # SVG icons for navigation
│   └── images/                     # Photos and imagery
├── AI_RSSfeed/                     # AI news aggregation system
├── AIrabbithole/                   # AI conversation archives
├── climate indices/                # Climate data visualizations
├── publications/                   # Publication summaries and PDFs
├── schematics/                     # Scientific diagrams
├── seminars/                       # Recorded talks
├── simulations/                    # Interactive science simulations
│   ├── coral_lagoon/
│   ├── estuary/
│   ├── flocking/
│   ├── monte_carlo_simulation/
│   ├── predator_prey/
│   ├── schelling_model/
│   ├── syntheticSST/
│   ├── traffic_model/
│   └── waves/
├── students/                       # Research group information
└── teaching/                       # Teaching materials
```

## Technologies Used

### Frontend

- **HTML5** - Semantic markup
- **CSS3** - Custom styling with:
  - CSS Variables for theming
  - Flexbox and Grid layouts
  - Media queries for responsive design (breakpoints: 1400px, 1200px, 1099px, 768px, 480px)
  - Backdrop filters and modern visual effects
- **Vanilla JavaScript** - No framework dependencies
  - Custom arc dial navigation system (SVG-based)
  - Dynamic content loading via Fetch API
  - Markdown parsing for AI news
  - CSV parsing with PapaParse library

### External Libraries (CDN)

- **PapaParse** (v5.4.1) - Robust CSV parsing for publications data

### Backend/Data Processing (Python)

Three Python-based subsystems with separate dependencies:

#### 1. AI RSS Feed System
- `feedparser` (6.0.11) - RSS feed parsing
- `python-dotenv` (1.0.1) - Environment variable management
- `openai` (1.40.1) - OpenAI API integration
- `requests` (2.32.3) - HTTP requests

#### 2. Climate Indices
- `requests` (≥2.31.0) - HTTP requests
- `beautifulsoup4` (≥4.12.0) - Web scraping
- `pandas` (≥2.0.0) - Data manipulation
- `numpy` (≥1.24.0) - Numerical computing
- `lxml` (≥4.9.0) - XML/HTML parsing

#### 3. PDF Summarizer
- `google-generativeai` (≥0.3.0) - Google Gemini API
- `python-dotenv` (≥1.0.0) - Environment configuration

## Key Features

### Custom Arc Dial Navigation

The site's signature feature is a custom-built SVG-based circular navigation system:

- **Rotation Control**: Hover on left/right edges to spin the dial
- **Visual Feedback**: Segments highlight on hover with gradient animations
- **Smart Snapping**: Automatically aligns to nearest menu item
- **Tooltip System**: Context-aware tooltips follow cursor
- **Accessibility**: Keyboard navigation support (Arrow keys, Enter/Space)
- **Responsive**: Adapts layout for tablets and mobile devices

### Publications Timeline

- Dynamically loads from CSV data (Scopus export)
- Color-coded by publication year
- Slider-based navigation through papers
- Clickable cards with DOI links
- Hover tooltips with full citations

### Modal Panels

- **Climate Indices**: Embedded dashboard (iframe)
- **AI News**: Markdown-based news aggregator
  - Latest news with expandable details
  - Podcast episode summaries
  - Archived news with lazy loading

### Photo Gallery

- Automatic rotation through 3 images
- Smooth fade transitions (5-second intervals)

## Installation & Setup

### Basic Setup (Static Site)

1. Clone or download the repository
2. Open `index.html` in a modern web browser
3. No build process required - pure HTML/CSS/JS

### Python Components (Optional)

If you want to use the data processing scripts:

#### AI RSS Feed
```bash
cd AI_RSSfeed/
pip install -r requirements.txt
# Create .env file with OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

#### Climate Indices
```bash
cd "climate indices/"
pip install -r requirements.txt
```

#### PDF Summarizer
```bash
cd publications/pdf-summarizer/
pip install -r requirements.txt
# Create .env file with Google API key
echo "GOOGLE_API_KEY=your_key_here" > .env
```

## Data Files

### Publications Data

Located in `assets/data/scopus_alex_sen_gupta_articles_with_abstracts.csv`

Expected CSV columns:
- `title` or `Title` - Paper title
- `year` or `Year` or `date` or `Date` - Publication year
- `doi` or `DOI` - Digital Object Identifier
- `journal` or `Journal` - Journal name
- `volume`, `issue`, `pages` - Publication details

### Student/Postdoc Data

Located in `students/postdocs_and_students.md`

Markdown format with sections:
```markdown
## Current Postdocs
### Dr FirstName LastName

## Current PhD Students
### FirstName LastName
```

## Browser Compatibility

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Required Features**:
  - CSS Grid and Flexbox
  - SVG 2.0
  - ES6+ JavaScript (async/await, fetch, arrow functions)
  - CSS backdrop-filter (for blur effects)

## Responsive Design

The site adapts across screen sizes:

- **Desktop (>1400px)**: Full layout with all components visible
- **Tablet (1100-1400px)**: Scaled desktop layout
- **Small Tablet (768-1099px)**: Vertical stacking, centered components
- **Mobile (<768px)**: Single column, simplified navigation
- **Small Phone (<480px)**: Compact layout with minimal spacing

## Performance Considerations

- **Asset Loading**: Icons and images loaded on-demand
- **CSV Caching**: Publications data cached with cache-busting parameters
- **Lazy Loading**: Archive content loaded only when expanded
- **Optimized Rendering**: RequestAnimationFrame for smooth animations
- **Debounced Events**: Resize handlers debounced to 100ms

## Customization

### Changing Colors

Edit CSS variables in `css/homepage.css`:

```css
:root {
  color-scheme: dark;
  /* Modify gradient colors, borders, etc. */
}
```

### Adding Navigation Items

Edit the `items` array in `js/homepage.js` (around line 1590):

```javascript
items: [
  {
    label: 'New Section',
    tooltip: 'Description',
    url: 'path/to/page.html',
    icon: 'assets/graphics/icon.svg'
  },
  // ... more items
]
```

### Updating Biography

Edit the text in `index.html` within the `.about-me-bio` div (line 112-122)

## Development Notes

- No build process or transpilation required
- All JavaScript is vanilla ES6+ (no frameworks)
- CSS uses modern features (Grid, Flexbox, custom properties)
- SVG graphics for scalable icons
- Modular structure allows easy section updates

## Credits

- **Developer/Designer**: Custom implementation
- **Icons**: Custom SVG graphics in `assets/graphics/`
- **CSV Parser**: PapaParse library
- **Fonts**: Inter font family (system fonts as fallback)

## License

Personal academic website - all rights reserved

## Contact

Alex Sen Gupta
Climate Scientist | Physical Oceanographer | Educator
UNSW Climate Change Research Centre

---

**Last Updated**: January 2026
**Version**: 1.0
**Total Files**: 341
**Primary Languages**: HTML, CSS, JavaScript, Python
