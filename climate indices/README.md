# Climate Indices Data Downloader

A Python script that downloads 9 major climate indices from official scientific sources (NOAA, NASA, NSIDC) and saves them as CSV files for use in web applications or data analysis.

## Climate Indices Included

The script downloads and saves the following indices:

1. **Oceanic Niño Index (ONI)** - 3-month running mean of SST anomalies; identifies El Niño and La Niña events
2. **Nino 3.4 Monthly Anomaly** - Monthly SST anomalies in the central equatorial Pacific
3. **Global Daily SST Anomaly** - Global sea surface temperature deviation from long-term average
4. **Global Daily 2m Air Temp Anomaly** - Global near-surface air temperature anomaly
5. **Antarctic Sea Ice Extent** - Total area covered by sea ice in the Southern Hemisphere
6. **Arctic Sea Ice Extent** - Total area covered by sea ice in the Northern Hemisphere
7. **Global Monthly CO2** - Global atmospheric carbon dioxide concentration
8. **GISTEMP Global Temp Anomaly** - NASA's global surface temperature anomaly dataset
9. **Pacific Decadal Oscillation (PDO)** - Long-term pattern of Pacific climate variability

## Output Files

All data is saved to the `data/` directory as CSV files:

- `oni_data.csv` - Oceanic Niño Index
- `nino34_data.csv` - Nino 3.4 Anomaly
- `sst_anomaly_data.csv` - Global SST Anomaly
- `t2m_anomaly_data.csv` - Global 2m Air Temperature Anomaly
- `antarctic_seaice_data.csv` - Antarctic Sea Ice Extent
- `arctic_seaice_data.csv` - Arctic Sea Ice Extent
- `co2_data.csv` - Global CO2 Concentration
- `gistemp_data.csv` - GISTEMP Temperature Anomaly
- `pdo_data.csv` - Pacific Decadal Oscillation

Each CSV file has a Date column (YYYY-MM-DD format) and the corresponding data value.

## Setup Instructions

### 1. Create a Virtual Environment

```bash
# Navigate to the project directory
cd "/Users/z3045790/Dropbox/AI code/climate indices"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Run the Data Downloader

```bash
python climate_dashboard.py
```

The script will sequentially download data from each source and save it as CSV files in the `data/` directory.

## What to Expect

- Each index is downloaded in real-time from official sources
- CSV files are saved to the `data/` directory
- Total runtime: 1-2 minutes depending on internet connection
- The script shows progress messages for each dataset
- A summary is displayed at the end showing which files were successfully downloaded

## Example Output

```
================================================================================
CLIMATE INDICES DATA DOWNLOADER
Started at: 2025-12-16 14:30:00
================================================================================

[ONI] Processing: Oceanic Niño Index (ONI)
  Source: CPC ONI v5
  Fetching: http://origin.cpc.ncep.noaa.gov/...
  ✓ Saved 876 records to data/oni_data.csv
    Date range: 1950-01-01 to 2024-12-01

...

================================================================================
DOWNLOAD SUMMARY
================================================================================

✓ Successfully downloaded and saved 9 dataset(s):
  • Oceanic Niño Index (ONI)
    File: data/oni_data.csv (876 records)
  • Nino 3.4 Monthly Anomaly
    File: data/nino34_data.csv (1,860 records)
  ...

Completed at: 2025-12-16 14:32:15
================================================================================
```

## Data Sources

All data comes from official scientific organizations:
- NOAA Climate Prediction Center
- NOAA Physical Sciences Laboratory
- ClimateReanalyzer.org
- NSIDC (National Snow and Ice Data Center)
- NOAA Global Monitoring Laboratory
- NASA GISS (Goddard Institute for Space Studies)
- University of Washington JISAO

## Viewing the Interactive Dashboard

After downloading the data, you can view it in an interactive web dashboard:

```bash
python start_server.py
```

This will:
1. Start a local web server on port 8000
2. Automatically open the dashboard in your browser
3. Display all climate indices with interactive zoom/pan charts

The dashboard features:
- Collapsible sections for each climate index
- Interactive charts with zoom (mouse wheel) and pan (click & drag)
- Combined plots for related indices (ENSO, Sea Ice)
- Educational information about each climate indicator

**URL**: http://localhost:8000/index.html

Press `Ctrl+C` in the terminal to stop the server when done.

## Using the Data

The CSV files in the `data/` directory are ready to use for:

- Web applications and dashboards
- Data visualization tools
- Statistical analysis
- Time series forecasting
- Climate research

Each file has a simple format with Date and value columns, making it easy to import into any platform.

## Alternative Scripts

The directory also contains standalone scripts for individual indices that generate plots instead of saving data:

- `extract_oni.py` - ONI with visualization
- `extract_nino34.py` - Nino 3.4 with visualization
- `download_climatereanalyzer.py` - Global SST with visualization
- `soi.py` - SOI and DMI with visualization

These are optional and not needed if you're using `climate_dashboard.py`.

## Troubleshooting

**Script hangs or times out**
- Check your internet connection
- Some data sources may be temporarily unavailable - try again later

**Missing data in plots**
- This is normal - some datasets may have gaps or be updated less frequently
- The script handles missing data automatically

**Import errors**
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt` again

## Deactivating Virtual Environment

When you're done:

```bash
deactivate
```
