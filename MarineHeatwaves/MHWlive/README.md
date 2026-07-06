# MHW Live

A self-updating global marine-heatwave map for the website.

`update_mhw_map.py` downloads the newest NOAA Coral Reef Watch daily map data,
renders a polished Robinson-projection PNG (title, date, legend, and a
60°S–60°N area inset all baked into the image), and writes:

- `latest.png` — the map shown on the page
- `meta.js` / `meta.json` — the data date and coverage stats

`index.html` displays `latest.png` and refreshes itself daily. A **MHW Live**
button on `../mhw.html` links here.

## Where to run it

Run the Python script on a machine that can reach NOAA and can write into this
folder — e.g. your Nectar web host. The map then updates with no chat session
or external service involved.

## One-time setup

```bash
pip3 install numpy netCDF4 matplotlib cartopy scipy
python3 update_mhw_map.py        # test run; should print "OK  data_date=..."
```

`cartopy` needs the system libraries GEOS and PROJ. On Ubuntu/Debian (typical
Nectar image):

```bash
sudo apt-get install -y libgeos-dev libproj-dev proj-data proj-bin
```

If `cartopy` is awkward to install, `conda install -c conda-forge cartopy`
pulls everything in one step.

## Daily cron job

```bash
crontab -e
# run every day at 09:30 (server local time); adjust the path:
30 9 * * * cd /path/to/site/MarineHeatwaves/MHWlive && /usr/bin/python3 update_mhw_map.py >> /tmp/mhwlive.log 2>&1
```

NOAA publishes with a 1–2 day lag, so the script automatically walks back from
today and uses the newest file that exists.

## Two-server setup (generate here, show on the conference site)

The map is a single self-contained PNG, so the conference site needs no code:

- **Embed the image:** `<img src="https://<this-host>/MarineHeatwaves/MHWlive/latest.png">`
- **Or embed the whole page:** `<iframe src="https://<this-host>/MarineHeatwaves/MHWlive/" style="width:100%;height:640px;border:0"></iframe>`

To make sure the conference site shows the fresh image each day rather than a
cached copy, serve `latest.png` with a short cache header (e.g.
`Cache-Control: max-age=3600`) or append a daily query string on the embed.

## Tweaks

- Pacific-centred map: set `CENTRAL_LON = 180` near the top of the script.
- Colours / labels: edit `OCEAN`, `CAT`, `LAND`, `INK`.
- Image size: change `max_width` (default 2400 px of source detail).

## Credit

Data: NOAA Coral Reef Watch Daily Global 5 km Satellite Marine Heatwave product
(v1.0.1). Categories follow Hobday et al. (2016, 2018).
