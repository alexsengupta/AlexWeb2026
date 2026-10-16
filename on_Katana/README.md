# SCOPUS — Marine Heatwave Literature Pipeline (Katana)

Lives in `/home/z3045790/SCOPUS/` on Katana. Pulls publication metadata from the
Elsevier Scopus API, optionally tags each paper with research themes via OpenAI,
and writes CSVs that the website (`Alex_web/MarineHeatwaves/`) reads.

## What it produces

| Script | Output CSV | Used by |
|---|---|---|
| `scopus_download_with_abstracts_MHW_all.py` | `scopus_all_MHW.csv` | `MarineHeatwaves/all_mhw.html` |
| `scopus_download_with_abstracts_SMHW.py` | `scopus_subsurface_MHW.csv` | `MarineHeatwaves/subsurface.html` |
| `scopus_download_with_abstracts_PolarMHW.py` | `scopus_polar_MHW.csv` | `MarineHeatwaves/polar.html` |
| `scopus_download_with_abstracts.py` | `scopus_alex_sen_gupta_articles_with_abstracts.csv` | personal publications page (moved into `Alex_web/assets/data/` by the local pull script) |

Each MHW script:
1. Pages through the Scopus Search API with a TITLE-ABS-KEY query.
2. Calls the Abstract Retrieval API for each hit to get abstract + author list.
3. If `OPENAI_API_KEY` is set, sends title + abstract to `gpt-4o-mini` to classify
   the paper against 15 predefined MHW themes; result stored in a `themes` column.
4. Writes CSV with resume support — interrupted runs pick up from existing `eid`s.

## API keys

Both keys live in `~/.scopus_env` (not in git, `chmod 600`):

```bash
ELSEVIER_API_KEY=...   # required, from https://dev.elsevier.com/
OPENAI_API_KEY=...     # optional; without it, `themes` column is blank
```

See `scopus_env.template` for the format.

## Running manually

```bash
cd ~/SCOPUS
source venv/bin/activate
set -a; source ~/.scopus_env; set +a
python3 scopus_download_with_abstracts_MHW_all.py
python3 scopus_download_with_abstracts_SMHW.py
python3 scopus_download_with_abstracts_PolarMHW.py
python3 scopus_download_with_abstracts.py
```

A full run of the broad MHW script can take a couple of hours because each paper
needs its own abstract call. The other three are much quicker.

## Scheduled (monthly) run via a self-resubmitting PBS job

`run_monthly_update.sh` is the wrapper. It loads the env file, runs all four
scripts using the venv's Python, and logs to `logs/cron_YYYYMMDD_HHMMSS.log`
(the name is historical; there is no cron).

`scopus_monthly.pbs` runs the wrapper on a compute node. Each run first queues
the next one for 03:00 on the 1st of the following month (`qsub -a`), then runs
the update, so a failed update cannot break the chain. PBS output goes to
`logs/<jobid>.OU`.

Start (or restart) the chain once:

```bash
qsub ~/SCOPUS/scopus_monthly.pbs     # runs now and queues next month
qstat -u z3045790                    # expect one job in state W
qstat -f $(qselect -u z3045790 -N scopus_monthly -s W) | grep Execution_Time
```

> **Why not cron?** Login-node crontabs live on the node's local disk and are
> wiped when the node is reimaged. That silently stopped this pipeline from
> July to October 2026. PBS keeps deferred jobs in its server database. Never
> run cron and the PBS chain together: two simultaneous runs would write the
> same CSVs. Compute nodes can reach the Scopus API (tested October 2026).

The Nectar VM runs `MarineHeatwaves/check_scopus_pipeline.py` daily and emails
if the last run is >35 days old, a script failed, no next run is queued, or the
website copy differs from Katana's.

## Cache files (regenerated automatically — do not delete unless you want a full re-fetch)

| File | Purpose |
|---|---|
| `scopus_all_MHW_search_cache.json` | Raw Scopus search results (≤3 days old reused) |
| `scopus_subsurface_MHW_search_cache.json` | Same, for subsurface query |
| `scopus_polar_MHW_search_cache.json` | Same, for polar query |
| `theme_cache.json` | OpenAI theme classifications keyed on title prefix |
| `theme_cache_polar.json` | Same, polar pipeline |

> **Known bug.** Theme caches are keyed on the first 100 characters of the
> title (`title[:100]`). Two papers sharing a long title prefix will collide and
> inherit each other's themes. Worth re-keying on `eid` or `doi`.

## Getting the CSVs onto the website

The Nectar VM pulls them automatically: `MarineHeatwaves/download_katana_csv.sh`
runs from the VM's crontab at 03:00 UTC on the 1st (about 11 h after the Katana
run), `scp`s `*.csv` from `~/SCOPUS/` into `MarineHeatwaves/`, and moves
`scopus_alex_sen_gupta_articles_with_abstracts.csv` into `assets/data/`. Logs
go to `MarineHeatwaves/cron.log` on the VM. Run it by hand after a manual
Katana run to publish immediately.

## Folders

- `old/` — superseded scripts (`scopus_download.py` and older copies). Archive only.
- `venv/` — Python virtualenv for this pipeline. Recreate from `requirements.txt`
  if it's ever lost: `python3 -m venv venv && venv/bin/pip install -r requirements.txt`.
- `logs/` — run logs (`cron_*.log`, auto-pruned after 180 days) and PBS output (`*.OU`).
