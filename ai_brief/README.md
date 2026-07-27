# Daily AI Brief archive

A growing archive of the daily "AI Brief", pulled from Google Drive and served
as part of the main site. Opened from the **🤖 AI Brief** button in the top nav.

```
Scheduled task "Alex's Daily AI Brief"   (managed in a separate chat)
        │  writes one file per day
        ▼
Google Drive folder
        │  ai-brief-YYYY-MM-DD.html   (raw HTML fragment, text/html)
        ▼
ai_brief/fetch_briefs.py             (cron, ~06:35 Sydney)
        │  downloads changed files, sanitises, writes:
        ├──► ai_brief/briefs/ai-brief-YYYY-MM-DD.html
        └──► ai_brief/index.json      (manifest, newest first)
                 │
                 ▼
index.html  →  loadAIBriefArchive()
        newest brief expanded; earlier days collapsed and fetched on click
```

Only the code is in git. The downloaded briefs and the manifest are generated on
each machine and are gitignored, so `git pull` on the VM never touches them.

---

## One-time setup

The folder is already created and live:

| | |
|---|---|
| Drive folder | **AI Brief Archive** |
| Folder ID | `1xrD3wCdLT6lytymp968KJebSaystqAki` |

### 1. Give the server read access to the folder

Two ways. **Option A is the quick one** and is what we settled on: the briefs
are published on a public website within hours anyway, so keeping the source
folder private buys very little.

#### Option A — API key + link-shared folder (about 2 minutes)

1. In Google Drive, right-click the **AI Brief Archive** folder → **Share** →
   **General access** → change "Restricted" to **Anyone with the link**, role
   **Viewer** → **Done**.
2. Go to <https://console.cloud.google.com/>, create a project (any name, e.g.
   `alex-web-briefs`).
3. **APIs & Services → Library** → search "Google Drive API" → **Enable**.
4. **APIs & Services → Credentials → Create credentials → API key**. Copy it.
5. Optional but sensible: click the new key → **API restrictions** →
   *Restrict key* → tick **Google Drive API**. Leave *Application restrictions*
   set to **None** — an HTTP-referrer restriction breaks server-side use, and an
   IP restriction needs the VM's fixed address.
6. Put the key in `.env` as `AI_BRIEF_API_KEY=...`

What this trades away: anyone who learns the folder URL can read the briefs
before they appear on the site. Nothing else — the key is read-only, restricted
to the Drive API, and can see only files you have explicitly link-shared.

#### Option B — service account (folder stays private)

Use this instead if you would rather the folder were not link-shared.

1. Steps 2 and 3 above (project, enable the Drive API).
2. **IAM & Admin → Service Accounts → Create service account**
   - Name: `ai-brief-reader`
   - Skip the optional role and user-access steps → **Done**.
3. Open it → **Keys** → **Add key → Create new key → JSON**. A file downloads.
   Treat it like a password.
4. Copy the service account's email — Google generates it at this point, and it
   looks like `ai-brief-reader@alex-web-briefs.iam.gserviceaccount.com`. This
   address does not exist until you complete this step; it cannot be supplied
   from outside your project.
5. In Drive: share the folder with that address, role **Viewer**. Untick
   "Notify people" — robots do not read email.
6. Put the JSON at `ai_brief/service_account.json`, `chmod 600` it, and leave
   `AI_BRIEF_API_KEY` empty in `.env`.

> If sharing is blocked: UNSW Workspace accounts often forbid sharing outside
> the university domain. The folder is on a personal Google account, so this
> should not arise — but if it does, use Option A.

The service account needs **Viewer** only. Nothing on the server writes to
Drive.

### 2. Install on the server (and locally)

```bash
cd /path/to/Alex_web/ai_brief

python3 -m venv venv
./venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env: paste your API key into AI_BRIEF_API_KEY
# (the folder ID is already filled in)
```

If you went with Option B instead, put the JSON key in place and lock it down:

```bash
mv ~/Downloads/alex-web-briefs-*.json service_account.json
chmod 600 service_account.json
```

### 3. First run

```bash
./venv/bin/python fetch_briefs.py --check     # credentials + folder access
./venv/bin/python fetch_briefs.py --dry-run   # report only, writes nothing
./venv/bin/python fetch_briefs.py             # for real
```

`--check` is the one to run first. It prints the config it resolved, connects,
and lists the newest few files it can see, without downloading anything. If
something is misconfigured it names the likely cause.

You should see `+ added ai-brief-2026-07-27.html` lines and then
`Done. added=N ...`. Open the site and click **🤖 AI Brief**.

### 4. Schedule it

The brief is generated at 06:00 Sydney time. Fetching at 06:35 gives it time to
land, and the two later runs are cheap insurance for a slow or failed morning
run (the script skips unchanged files, so extra runs cost almost nothing).

```bash
crontab -e
```

```cron
# Daily AI Brief -- pull from Drive and rebuild the archive.
# CRON_TZ matters: Nectar VMs usually run on UTC, and Sydney shifts by an hour
# in daylight saving. This line makes the times below mean Sydney time.
CRON_TZ=Australia/Sydney
35 6  * * * /var/www/Alex_web/ai_brief/run_fetch.sh
5  9  * * * /var/www/Alex_web/ai_brief/run_fetch.sh
5  13 * * * /var/www/Alex_web/ai_brief/run_fetch.sh
```

Check what path to use with `pwd`, and make the wrapper executable once:

```bash
chmod +x /var/www/Alex_web/ai_brief/run_fetch.sh
```

If `CRON_TZ` is unsupported on your VM's cron, use UTC times instead
(06:35 Sydney = 20:35 UTC the previous day during AEST, 19:35 UTC during AEDT)
and accept the one-hour drift across daylight saving, or set the whole VM to
Sydney time with `sudo timedatectl set-timezone Australia/Sydney`.

Logs go to `ai_brief/fetch.log`, trimmed automatically at 2000 lines:

```bash
tail -f /var/www/Alex_web/ai_brief/fetch.log
```

---

## Running it on your Mac as well

Same steps, but macOS has no `flock` (the wrapper notices and carries on) and
cron is discouraged. Either run it by hand when you want fresh briefs locally:

```bash
cd ~/Dropbox/Alex_web/ai_brief && ./venv/bin/python fetch_briefs.py
```

…or add a `launchd` job. The local copy is entirely independent of the VM's —
each machine downloads its own copy from Drive, so they cannot conflict, and
neither is committed to git.

The `venv/`, `.env`, `service_account.json`, `briefs/` and `index.json` are all
gitignored, so the Mac and the VM can hold different credentials and different
numbers of briefs without any interference.

---

## Command reference

| Command | What it does |
|---|---|
| `python fetch_briefs.py` | Normal run: download new/changed briefs, rebuild manifest |
| `python fetch_briefs.py --check` | Test credentials and folder access; download nothing |
| `python fetch_briefs.py --dry-run` | Report what would change; write nothing |
| `python fetch_briefs.py --force` | Re-download every file (use after a format change) |
| `python fetch_briefs.py --rebuild` | Rebuild `index.json` from local files. No network or credentials needed |
| `python fetch_briefs.py --self-test` | Run the sanitiser checks |
| `./run_fetch.sh` | Cron wrapper: venv, logging, no overlapping runs |

---

## How a brief is processed

Each downloaded file is rebuilt from an allowlist of tags and attributes before
it is written to disk. `<script>`, `<iframe>`, `<style>`, inline `on*` handlers
and `javascript:` links are discarded; external links get
`target="_blank" rel="noopener noreferrer"`.

This is not distrust of the generating task so much as ordinary hygiene: the
briefs summarise third-party web pages, they are written by a language model,
and anything that reached the page would run on your site's own origin. The
sanitiser makes the worst case "a mangled paragraph" instead of "arbitrary code
on alexsengupta's site". `--self-test` exercises it.

If a file arrives without the expected `<article class="ai-brief">` wrapper, the
script falls back to the document body, wraps it, and logs a warning rather than
dropping the day.

The date in the **filename** is authoritative — `data-date` in the fragment is
overwritten to match, so a wrong date inside the file cannot reorder the archive.

---

## If something goes wrong

| Symptom | Likely cause |
|---|---|
| `AI_BRIEF_FOLDER_ID is not set` | `.env` missing or in a different directory. Use absolute paths in cron. |
| `No credentials found` | Neither `AI_BRIEF_API_KEY` nor a service-account key file is set. |
| `403 Forbidden` with an API key | The folder is not shared "Anyone with the link", or the key has an HTTP-referrer restriction. |
| `Could not list Drive folder ... 404` | Folder ID wrong, **or** (Option B) the folder was never shared with the service-account email. |
| `Drive folder has 0 file(s) matching` | Files are there but misnamed. They must be exactly `ai-brief-YYYY-MM-DD.html`. |
| Panel says "not available yet" | Cron has not run, or the web server cannot read `ai_brief/index.json`. |
| A day shows "no usable content" | That file is empty or not HTML. Check it in Drive. |
| Briefs vanish after a deploy | Something ran `git clean -xdf`. The briefs are gitignored, so a hard clean deletes them. Re-run the fetch; Drive still has them. |

Nothing here is destructive: every brief lives in Drive, so a wiped `briefs/`
directory is fixed by re-running `fetch_briefs.py`.

---

## The archive Google Doc

There is also a Google Doc (`1MHirxdt5wbDFySjm9JmjjCJcAmOW3DDCautrYyD7D98`,
"AI Brief — Archive") from the publish-to-web option we did not take. Nothing
here reads it. It does not need to be shared with anything, and the morning task
does not need to keep appending to it — a second output path that nothing
consumes will drift out of sync with the folder and cause confusion later. Keep
it only if you want a human-readable backup, and treat the folder as the source
of truth.

## The old RSS briefing

The previous RSS-based digest (`AI_RSSfeed/scanForAInews.py` →
`ai_news_latest.md`) is untouched and still works. It is no longer in the nav
bar, but the code is retained: run `openCard('ai-rss')` in the browser console
to open it.
