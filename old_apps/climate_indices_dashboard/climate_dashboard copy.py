import requests
import pandas as pd
import numpy as np
from io import StringIO
from bs4 import BeautifulSoup # For ONI HTML parsing
import json # For JSON parsing
import os
from datetime import datetime

# Variables being downloaded and saved:
# - Oceanic Niño Index (ONI)
# - Nino 3.4 Monthly Anomaly
# - Global Daily SST Anomaly
# - Global Daily 2m Air Temp Anomaly
# - Antarctic Sea Ice Extent
# - Arctic Sea Ice Extent
# - Global Monthly CO2
# - GISTEMP Global Temp Anomaly
# - Pacific Decadal Oscillation (PDO)

# Output directory for CSV files
OUTPUT_DIR = "data"

# --- Configuration for all Datasets ---
DATASETS_CONFIG = [
    {
        'name': "Oceanic Niño Index (ONI)",
        'id': 'oni',
        'filename': 'oni_data.csv',
        'url': "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php",
        'data_type': 'html_oni_cpc',
        'value_column_name': 'ONI_Value',
        'description': 'CPC ONI v5'
    },
    {
        'name': "Nino 3.4 Monthly Anomaly",
        'id': 'nino34',
        'filename': 'nino34_data.csv',
        'url': "https://psl.noaa.gov/data/timeseries/month/data/nino34.long.anom.data",
        'data_type': 'txt_nino34_psl',
        'value_column_name': 'Nino34_Anom',
        'description': 'PSL Monthly'
    },
    {
        'name': "Global Daily SST Anomaly",
        'id': 'sst',
        'filename': 'sst_anomaly_data.csv',
        'url': "https://climatereanalyzer.org/clim/sst_daily/json_2clim/oisst2.1_world2_sst_day.json",
        'data_type': 'json_climatereanalyzer_sst',
        'value_column_name': 'SST_Anomaly',
        'description': 'ClimateReanalyzer OISSTv2.1 Daily'
    },
    {
        'name': "Global Daily 2m Air Temp Anomaly",
        'id': 't2m',
        'filename': 't2m_anomaly_data.csv',
        'url': "https://climatereanalyzer.org/clim/t2_daily/json/era5_world_t2_day.json",
        'data_type': 'json_climatereanalyzer_t2m',
        'value_column_name': 'T2m_Anomaly',
        'description': 'ClimateReanalyzer ERA5 Daily'
    },
    {
        'name': "Antarctic Sea Ice Extent",
        'id': 'antarctic_ice',
        'filename': 'antarctic_seaice_data.csv',
        'url': "https://www.ncei.noaa.gov/access/monitoring/snow-and-ice-extent/sea-ice/S/0/data.csv",
        'data_type': 'csv_ncei_seaice',
        'value_column_name': 'Extent',
        'description': 'NCEI South Daily'
    },
    {
        'name': "Arctic Sea Ice Extent",
        'id': 'arctic_ice',
        'filename': 'arctic_seaice_data.csv',
        'url': "https://www.ncei.noaa.gov/access/monitoring/snow-and-ice-extent/sea-ice/N/0/data.csv",
        'data_type': 'csv_ncei_seaice',
        'value_column_name': 'Extent',
        'description': 'NCEI North Daily'
    },
    {
        'name': "Global Monthly CO2",
        'id': 'co2',
        'filename': 'co2_data.csv',
        'url': "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_gl.txt",
        'data_type': 'txt_co2_gml',
        'value_column_name': 'CO2_ppm',
        'description': 'NOAA GML Monthly Global Mean'
    },
    {
        'name': "GISTEMP Global Temp Anomaly",
        'id': 'gistemp',
        'filename': 'gistemp_data.csv',
        'url': "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv",
        'data_type': 'csv_gistemp_v4',
        'value_column_name': 'Temperature_Anomaly',
        'description': 'NASA GISTEMP v4 Monthly'
    },
    {
        'name': "Pacific Decadal Oscillation (PDO)",
        'id': 'pdo',
        'filename': 'pdo_data.csv',
        'url': "https://psl.noaa.gov/pdo/data/pdo.timeseries.sstens.data",
        'data_type': 'txt_pdo_psl',
        'value_column_name': 'PDO_Index',
        'description': 'PSL Ensemble SST'
    }
]

# --- Generic Fetcher ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'
}

def fetch_raw_data(url, is_binary=False):
    try:
        print(f"  Fetching: {url}")
        response = requests.get(url, headers=HEADERS, timeout=45) # Increased timeout
        response.raise_for_status()

        # Explicitly set encoding for ONI data if it's HTML and not correctly detected
        if "oni_v5.php" in url and (response.encoding is None or 'windows-1252' not in response.encoding.lower()):
            response.encoding = 'windows-1252'

        if is_binary:
            return response.content
        return response.text
    except requests.exceptions.Timeout:
        print(f"  Error: Timeout fetching {url}")
    except requests.exceptions.HTTPError as e:
        print(f"  Error: HTTPError {e.response.status_code} fetching {url}")
    except requests.exceptions.RequestException as e:
        print(f"  Error: RequestException {e} fetching {url}")
    return None

# --- Specific Parsers ---

def parse_html_oni_cpc(raw_html, value_col_name):
    # This is adapted from the previous working ONI parser
    if raw_html is None: return None
    soup = BeautifulSoup(raw_html, 'lxml')
    data_tables = soup.find_all('table', {'border': '1', 'align': 'center'})
    data_table = None
    if data_tables:
        for tbl_candidate in data_tables:
            first_row = tbl_candidate.find('tr')
            if first_row:
                tds = first_row.find_all('td')
                if len(tds) > 1 and "year" in tds[0].get_text(strip=True).lower() and "djf" in tds[1].get_text(strip=True).lower():
                    data_table = tbl_candidate
                    break
        if not data_table and data_tables: data_table = data_tables[0]
    if not data_table: return None

    oni_records = []
    seasons_oni = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    rows = data_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if not cells or len(cells) < len(seasons_oni) + 1: continue
        year_text_tag = cells[0].find('font')
        year_text = year_text_tag.get_text(strip=True) if year_text_tag else cells[0].get_text(strip=True)
        if year_text.isdigit():
            year = int(year_text)
            record = {'Year': year}
            for i, season_header in enumerate(seasons_oni):
                font_tag = cells[i + 1].find('font')
                val_text = font_tag.get_text(strip=True) if font_tag else cells[i+1].get_text(strip=True)
                strong_tag = font_tag.find('strong') if font_tag else None
                if strong_tag: val_text = strong_tag.get_text(strip=True)
                try: record[season_header] = float(val_text) if val_text and val_text != "." else np.nan
                except ValueError: record[season_header] = np.nan
            oni_records.append(record)
    
    if not oni_records: return None
    df_wide = pd.DataFrame(oni_records)
    df_long = pd.melt(df_wide, id_vars=['Year'], value_vars=seasons_oni, var_name='Season', value_name=value_col_name)
    
    season_to_month_map = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}
    df_long['Month'] = df_long['Season'].map(season_to_month_map)
    df_long['Date_str'] = df_long['Year'].astype(str) + '-' + df_long['Month'].astype(str).str.zfill(2) + '-01'
    df_long['Date'] = pd.to_datetime(df_long['Date_str'])
    
    # Sort and drop NaNs explicitly, similar to extract_oni.py
    df_long = df_long.sort_values(by='Date').reset_index(drop=True)
    df_plot = df_long.dropna(subset=[value_col_name]).copy() # Use .copy() for operations
    
    return df_plot.set_index('Date')[[value_col_name]]


def parse_txt_nino34_psl(raw_text, value_col_name):
    if raw_text is None: return None
    lines = raw_text.strip().split('\n')
    data_records = []
    header_line_index = -1
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            header_line_index = i; break
    if header_line_index == -1: return None
    
    data_lines = []
    for line in lines[header_line_index + 1:]:
        if line.strip() and line.strip()[:4].isdigit(): data_lines.append(line.strip())
        else: break # Stop at metadata

    for line in data_lines:
        parts = line.split()
        year = int(parts[0])
        monthly_values = parts[1:]
        for month_idx, value_str in enumerate(monthly_values):
            if month_idx < 12: # Ensure we only take 12 months
                try:
                    value = float(value_str)
                    if value != -99.99: # Missing value indicator
                        data_records.append({'Year': year, 'Month': month_idx + 1, value_col_name: value})
                except ValueError:
                    continue # Skip if value is not a float
    if not data_records: return None
    df = pd.DataFrame(data_records)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2) + '-01')
    return df.set_index('Date')[[value_col_name]].sort_index()


def parse_json_climatereanalyzer_sst(raw_json_text, value_col_name):
    if raw_json_text is None:
        print("  DEBUG: No raw JSON text to parse.")
        return None
    try:
        data = json.loads(raw_json_text)
        if not isinstance(data, list):
            print(f"  DEBUG: JSON root is not a list. Type: {type(data)}")
            return None
    except json.JSONDecodeError as e:
        print(f"  DEBUG: Could not decode JSON. Error: {e}")
        return None
    
    all_records = []
    print(f"  DEBUG: JSON parsed. Root is a list with {len(data)} items (expected years).")

    for i, year_data_item in enumerate(data):
        if not isinstance(year_data_item, dict):
            continue

        year_str = year_data_item.get('name')
        # 'data' is now a direct list of anomaly values or null
        daily_anomaly_values = year_data_item.get('data') 

        if i == 0: # Debug first year item
            print(f"  DEBUG: First year item: name='{year_str}', data type='{type(daily_anomaly_values)}'")
            if isinstance(daily_anomaly_values, list) and len(daily_anomaly_values) > 0:
                first_valid_dp = next((item for item in daily_anomaly_values if item is not None), None)
                print(f"  DEBUG: First non-null anomaly value in first year: {first_valid_dp}")

        if year_str and isinstance(daily_anomaly_values, list) and year_str.isdigit():
            year_int = int(year_str)
            try:
                start_date_of_year = pd.Timestamp(f'{year_int}-01-01')
            except ValueError:
                print(f"  DEBUG: Invalid year for Timestamp: {year_int}. Skipping this year.")
                continue
            
            for day_index, anomaly_value in enumerate(daily_anomaly_values):
                if anomaly_value is None: # Skip null entries
                    continue
                
                try:
                    # Date is calculated by adding day_index to Jan 1st of the year
                    current_date = start_date_of_year + pd.Timedelta(days=day_index)
                    
                    # Ensure the calculated date is still within the expected year
                    # This handles leap years correctly (day_index can go up to 365 for leap years)
                    if current_date.year != year_int:
                        # This might happen if day_index exceeds days in year (e.g. 366 for non-leap)
                        # Or if there's an issue with the data having too many points for a year.
                        # print(f"  DEBUG: Date mismatch for year {year_int}, day_index {day_index}, calculated date {current_date}. Skipping.")
                        continue

                    anomaly_value_float = float(anomaly_value) 
                    all_records.append({'Date': current_date, value_col_name: anomaly_value_float})
                except (TypeError, ValueError) as e:
                    # print(f"  DEBUG: Skipping data point due to conversion error: {anomaly_value}, error: {e}")
                    continue
            
    if not all_records:
        print("  DEBUG: all_records list is empty after parsing all years.")
        return None
    
    print(f"  DEBUG: Extracted {len(all_records)} records in total.")
    df = pd.DataFrame(all_records)
    
    if 'Date' not in df.columns or value_col_name not in df.columns:
        print(f"  DEBUG: DataFrame created but missing essential columns. Columns: {df.columns.tolist()}")
        return None
        
    return df.set_index('Date')[[value_col_name]].sort_index()

def parse_json_climatereanalyzer_t2m(raw_json_text, value_col_name):
    if raw_json_text is None: return None
    try:
        data = json.loads(raw_json_text)
    except json.JSONDecodeError:
        print("  Error: Could not decode JSON for T2M")
        return None

    all_records = []
    for year_data in data:
        year_str = year_data.get('name')
        daily_anomalies = year_data.get('data')  # Key is 'data' not 'anomaly_data'

        if year_str and daily_anomalies and year_str.isdigit():
            year = int(year_str)
            start_date = pd.Timestamp(f'{year}-01-01')
            for i, anomaly_val in enumerate(daily_anomalies):
                if anomaly_val is None:  # Skip null values
                    continue
                current_date = start_date + pd.Timedelta(days=i)
                if current_date.year == year:
                    all_records.append({'Date': current_date, value_col_name: anomaly_val})
    if not all_records: return None
    df = pd.DataFrame(all_records)
    return df.set_index('Date')[[value_col_name]].sort_index()

def parse_csv_nsidc_seaice(raw_csv_text, value_col_name):
    if raw_csv_text is None: return None
    try:
        # Skip first header row, use columns from the second row if present or define
        # The files typically have one header row: "Year, Month, Day, Extent, Missing, Source Data"
        df = pd.read_csv(StringIO(raw_csv_text), skiprows=2, # Changed from 1 to 2
                         names=['Year', 'Month', 'Day', 'Extent', 'Missing', 'Source Data'],
                         na_values=['-9999', -9999.0]) # Handle missing
        df = df.dropna(subset=['Year', 'Month', 'Day', 'Extent']) # Drop rows where essential info is missing
        df['Date'] = pd.to_datetime(df[['Year', 'Month', 'Day']].astype(int))
        return df.set_index('Date')[[value_col_name]].sort_index() # value_col_name is 'Extent'
    except Exception as e:
        print(f"  Error parsing NSIDC CSV: {e}")
        return None

def parse_csv_ncei_seaice(raw_csv_text, value_col_name):
    if raw_csv_text is None: return None
    try:
        # NCEI format has title and metadata rows before header
        # Find the header row (contains "Date,Value,Anomaly,Monthly Mean")
        lines = raw_csv_text.split('\n')
        header_row_idx = 0
        for i, line in enumerate(lines):
            if 'Date,Value' in line or 'Date, Value' in line:
                header_row_idx = i
                break

        # Read CSV starting from header row
        df = pd.read_csv(StringIO(raw_csv_text), skiprows=header_row_idx)

        # Date is in YYYYMM format, convert to datetime
        df['Date'] = pd.to_datetime(df['Date'].astype(str), format='%Y%m')

        # Rename 'Value' to the specified column name
        df.rename(columns={'Value': value_col_name}, inplace=True)

        return df.set_index('Date')[[value_col_name]].sort_index()
    except Exception as e:
        print(f"  Error parsing NCEI Sea Ice CSV: {e}")
        return None

def parse_txt_co2_gml(raw_text, value_col_name):
    if raw_text is None: return None
    comments_removed = "\n".join([line for line in raw_text.split('\n') if not line.strip().startswith('#')])
    try:
        # Columns: year, month, decimal, average, average_unc, trend, trend_unc
        df = pd.read_csv(StringIO(comments_removed), sep='\s+', header=None,
                         names=['year', 'month', 'decimal', 'average', 'average_unc', 'trend', 'trend_unc'])
        df['Date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2) + '-01', format='%Y-%m-%d')
        df.rename(columns={'average': value_col_name}, inplace=True)
        return df.set_index('Date')[[value_col_name]].sort_index()
    except Exception as e:
        print(f"  Error parsing GML CO2: {e}")
        return None

def parse_csv_gistemp_v4(raw_csv_text, value_col_name):
    if raw_csv_text is None: return None
    # Find where the actual data starts, typically after "Year,Jan,..."
    lines = raw_csv_text.split('\n')
    data_start_line = 0
    for i, line in enumerate(lines):
        if line.lower().startswith("year,jan,feb"):
            data_start_line = i
            break
    if data_start_line == 0 and not lines[0].lower().startswith("year,jan,feb"):
        print("  Error: GISTEMP CSV header not found.")
        return None
    
    # Read the data part, handle "***" as NaN
    df_wide = pd.read_csv(StringIO("\n".join(lines[data_start_line:])), na_values=["***"])
    
    # Melt to long format
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    df_long = pd.melt(df_wide, id_vars=['Year'], value_vars=months,
                      var_name='Month_Str', value_name=value_col_name)
    
    month_map = {name: num for num, name in enumerate(months, 1)}
    df_long['Month'] = df_long['Month_Str'].map(month_map)
    df_long = df_long.dropna(subset=[value_col_name, 'Year', 'Month']) # Ensure all parts for date are present
    df_long['Date'] = pd.to_datetime(df_long['Year'].astype(int).astype(str) + '-' + df_long['Month'].astype(int).astype(str).str.zfill(2) + '-01')
    return df_long.set_index('Date')[[value_col_name]].sort_index()


def parse_csv_noaa_globaltemp_monthly(raw_csv_text, value_col_name):
    if raw_csv_text is None: return None
    try:
        # NCEI CSVs usually have a few header lines to skip. The data.csv from the link has 4.
        df = pd.read_csv(StringIO(raw_csv_text), skiprows=4, names=['YearMonth', value_col_name])
        df['YearMonth'] = df['YearMonth'].astype(str)
        df['Date'] = pd.to_datetime(df['YearMonth'].str.slice(0,4) + '-' + df['YearMonth'].str.slice(4,6) + '-01')
        return df.set_index('Date')[[value_col_name]].sort_index()
    except Exception as e:
        print(f"  Error parsing NOAA GlobalTemp CSV: {e}")
        return None

def parse_txt_cpc_index(raw_text, value_col_name): # For NAO, AO, AAO
    if raw_text is None: return None
    lines = raw_text.strip().split('\n')
    data_records = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 13 and parts[0].isdigit(): # Year + 12 months
            year = int(parts[0])
            for month_idx, val_str in enumerate(parts[1:]):
                try:
                    value = float(val_str)
                    if value > -999: # Common missing value indicator
                        data_records.append({'Year': year, 'Month': month_idx + 1, value_col_name: value})
                except ValueError:
                    continue
    if not data_records: return None
    df = pd.DataFrame(data_records)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2) + '-01')
    return df.set_index('Date')[[value_col_name]].sort_index()

def parse_txt_pdo_jisao(raw_text, value_col_name):
    if raw_text is None: return None
    lines = raw_text.strip().split('\n')

    # First line contains year range (e.g., "1870 2025")
    # Data starts from line 1 (index 1)
    # Look for lines that end with "-9999" to know when metadata starts
    data_records = []

    for line in lines[1:]:  # Skip first line (year range)
        parts = line.strip().split()

        # Stop if we hit the metadata marker
        if line.strip() == "-9999" or not parts:
            break

        # Data line should have year + 12 monthly values
        if len(parts) >= 13 and parts[0].isdigit():
            year = int(parts[0])
            for month_idx, val_str in enumerate(parts[1:13]):  # Take first 12 after year
                try:
                    value = float(val_str)
                    # Skip missing values (-9999.000)
                    if value > -9000:
                        data_records.append({'Year': year, 'Month': month_idx + 1, value_col_name: value})
                except ValueError:
                    continue

    if not data_records: return None
    df = pd.DataFrame(data_records)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2) + '-01')
    return df.set_index('Date')[[value_col_name]].sort_index()

# --- Parser Dispatcher ---
PARSER_MAP = {
    'html_oni_cpc': parse_html_oni_cpc,
    'txt_nino34_psl': parse_txt_nino34_psl,
    'json_climatereanalyzer_sst': parse_json_climatereanalyzer_sst,
    'json_climatereanalyzer_t2m': parse_json_climatereanalyzer_t2m,
    'csv_nsidc_seaice': parse_csv_nsidc_seaice,
    'csv_ncei_seaice': parse_csv_ncei_seaice,
    'txt_co2_gml': parse_txt_co2_gml,
    'csv_gistemp_v4': parse_csv_gistemp_v4,
    'csv_noaa_globaltemp_monthly': parse_csv_noaa_globaltemp_monthly,
    'txt_cpc_index': parse_txt_cpc_index,
    'txt_pdo_psl': parse_txt_pdo_jisao,  # Reusing the parser with new name
}

# --- File Saving Function ---
def save_dataset_to_csv(df, filename, dataset_name):
    """
    Saves a DataFrame to CSV file in the output directory.
    Returns True if successful, False otherwise.
    """
    if df is None or df.empty:
        print(f"  Cannot save {dataset_name}: DataFrame is empty or None.")
        return False

    try:
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Full path for the output file
        filepath = os.path.join(OUTPUT_DIR, filename)

        # Save to CSV with date as first column
        df.to_csv(filepath, index=True, date_format='%Y-%m-%d')

        # Get data info
        date_range = f"{df.index.min().date()} to {df.index.max().date()}"
        num_records = len(df)

        print(f"  ✓ Saved {num_records} records to {filepath}")
        print(f"    Date range: {date_range}")
        return True

    except Exception as e:
        print(f"  ✗ Error saving {dataset_name}: {e}")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    print("=" * 80)
    print("CLIMATE INDICES DATA DOWNLOADER")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Track results
    results = {
        'success': [],
        'failed': []
    }

    for config in DATASETS_CONFIG:
        print(f"\n[{config['id'].upper()}] Processing: {config['name']}")
        print(f"  Source: {config['description']}")

        # Fetch data
        raw_data = fetch_raw_data(config['url'])
        if raw_data is None:
            print(f"  ✗ Failed to fetch data")
            results['failed'].append({
                'name': config['name'],
                'filename': config['filename'],
                'reason': 'Download failed'
            })
            continue

        # Parse data
        parser_func = PARSER_MAP.get(config['data_type'])
        if parser_func is None:
            print(f"  ✗ No parser defined for data_type: {config['data_type']}")
            results['failed'].append({
                'name': config['name'],
                'filename': config['filename'],
                'reason': 'No parser available'
            })
            continue

        df_timeseries = parser_func(raw_data, config['value_column_name'])

        # Save data
        if df_timeseries is not None and not df_timeseries.empty:
            if save_dataset_to_csv(df_timeseries, config['filename'], config['name']):
                results['success'].append({
                    'name': config['name'],
                    'filename': config['filename'],
                    'records': len(df_timeseries)
                })
            else:
                results['failed'].append({
                    'name': config['name'],
                    'filename': config['filename'],
                    'reason': 'Save failed'
                })
        else:
            print(f"  ✗ Failed to parse data")
            results['failed'].append({
                'name': config['name'],
                'filename': config['filename'],
                'reason': 'Parsing failed'
            })

    # Print summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    if results['success']:
        print(f"\n✓ Successfully downloaded and saved {len(results['success'])} dataset(s):")
        for item in results['success']:
            print(f"  • {item['name']}")
            print(f"    File: {OUTPUT_DIR}/{item['filename']} ({item['records']:,} records)")

    if results['failed']:
        print(f"\n✗ Failed to download {len(results['failed'])} dataset(s):")
        for item in results['failed']:
            print(f"  • {item['name']}")
            print(f"    File: {item['filename']} - Reason: {item['reason']}")

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

