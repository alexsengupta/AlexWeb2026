# Marine Heatwave Literature Browser

## Updating the paper databases

### 1. SSH to Katana

```bash
ssh z3045790@katana.restech.unsw.edu.au
cd /home/z3045790/SCOPUS
source venv/bin/activate
```

### 2. Generate CSV files

```bash
python3 scopus_download_with_abstracts_MHW_all.py
python3 scopus_download_with_abstracts_SMHW.py
python3 scopus_download_with_abstracts.py
```

- The first two scripts search Scopus, fetch abstracts and authors, and optionally classify papers into research themes (if `OPENAI_API_KEY` is set).
- Search results are cached locally for 3 days to avoid redundant API calls on re-runs.
- CSV output supports resume: if a script is interrupted, re-running it will skip already-written rows.
- The third script fetches personal publications by author ID.

### 3. Download CSV files to local machine

From the local `MarineHeatwaves/` directory:

```bash
bash download_katana_csv.sh
```

This does two things:
1. Copies all `.csv` files from Katana's `SCOPUS/` folder into the current directory.
2. Moves `scopus_alex_sen_gupta_articles_with_abstracts.csv` into `../assets/data/` (the website's data directory).

### Output files

| File | Description |
|------|-------------|
| `scopus_all_MHW.csv` | All marine heatwave literature |
| `scopus_subsurface_MHW.csv` | Subsurface/benthic/bottom MHW literature |
| `assets/data/scopus_alex_sen_gupta_articles_with_abstracts.csv` | Personal publications |

### HTML browsers

- `all_mhw.html` — Browse all MHW papers (reads `scopus_all_MHW.csv`)
- `subsurface.html` — Browse subsurface MHW papers (reads `scopus_subsurface_MHW.csv`)
