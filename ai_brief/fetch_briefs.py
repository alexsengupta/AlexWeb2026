#!/usr/bin/env python3
"""
fetch_briefs.py -- pull the daily "AI Brief" HTML fragments from a Google Drive
folder and turn them into a local, growing archive that the website can serve.

What it does, in order:
  1. Authenticates to Google Drive with a service account (read-only scope).
  2. Lists the dedicated Drive folder for files named ai-brief-YYYY-MM-DD.html
  3. Downloads any file that is new or has changed since the last run.
  4. Sanitises each fragment (allowlist of tags/attributes; scripts stripped).
  5. Writes ai_brief/briefs/ai-brief-YYYY-MM-DD.html
  6. Writes ai_brief/index.json -- the manifest the front-end reads, sorted
     newest first.

It is safe to run repeatedly: unchanged files are skipped, and both the brief
files and the manifest are written atomically, so a half-finished run can never
be served to a visitor.

Authentication -- two supported ways, whichever suits:
  API key       Simplest. Works when the Drive folder is shared
                "Anyone with the link can view". No key file, nothing to
                rotate. Set AI_BRIEF_API_KEY.
  Service acct  For a folder that stays private. Set AI_BRIEF_SA_KEY to a
                service-account JSON key and share the folder with the
                service account's email address.
If both are set, the API key is used.

Configuration (environment variables, optionally via ai_brief/.env):
  AI_BRIEF_FOLDER_ID   Google Drive folder ID.                    (required)
  AI_BRIEF_API_KEY     Google Cloud API key, for a link-shared folder.
  AI_BRIEF_SA_KEY      Path to a service-account JSON key, for a private
                       folder. Default: <script dir>/service_account.json
  AI_BRIEF_OUT         Directory for downloaded fragments.
                       Default: <script dir>/briefs
  AI_BRIEF_MANIFEST    Path to the manifest.
                       Default: <script dir>/index.json

Usage:
  python fetch_briefs.py                # normal run
  python fetch_briefs.py --check        # test credentials and folder access
  python fetch_briefs.py --dry-run      # show what would change, write nothing
  python fetch_briefs.py --force        # re-download everything
  python fetch_briefs.py --rebuild      # rebuild manifest from local files only
                                        # (no network, no credentials needed)
  python fetch_briefs.py --self-test    # sanitiser checks, no network
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Filename contract with the generating task.
# ---------------------------------------------------------------------------
FILENAME_RE = re.compile(r"^ai-brief-(\d{4})-(\d{2})-(\d{2})\.html$")

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_dotenv(path: Path) -> tuple[bool, list[str]]:
    """Minimal .env reader: KEY=value lines, # comments, optional quotes.

    Deliberately dependency-free. Existing environment variables win, so you can
    override the file from the command line or a cron entry.

    Returns (file_existed, names_of_keys_left_blank) so --check can tell the
    difference between "no .env" and "a .env with an empty key in it".
    """
    if not path.is_file():
        return False, []

    # Collect first, apply after. Within the file a later non-empty value wins,
    # so appending "AI_BRIEF_API_KEY=..." to a file that already has a blank
    # one does what you'd expect instead of being silently ignored.
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value or key not in values:
            values[key] = value

    blank = [k for k, v in values.items() if k.startswith("AI_BRIEF_") and not v]
    for key, value in values.items():
        os.environ.setdefault(key, value)   # real environment still wins
    return True, blank


class Config:
    def __init__(self) -> None:
        self.env_file = SCRIPT_DIR / ".env"
        self.env_found, self.env_blank = load_dotenv(self.env_file)
        self.folder_id = os.environ.get("AI_BRIEF_FOLDER_ID", "").strip()
        self.api_key = os.environ.get("AI_BRIEF_API_KEY", "").strip()
        self.sa_key = Path(
            os.environ.get("AI_BRIEF_SA_KEY", str(SCRIPT_DIR / "service_account.json"))
        ).expanduser()
        self.out_dir = Path(
            os.environ.get("AI_BRIEF_OUT", str(SCRIPT_DIR / "briefs"))
        ).expanduser()
        self.manifest = Path(
            os.environ.get("AI_BRIEF_MANIFEST", str(SCRIPT_DIR / "index.json"))
        ).expanduser()


# ---------------------------------------------------------------------------
# Sanitiser
# ---------------------------------------------------------------------------
# The fragments are machine-generated by a language model from third-party news
# sources. They are almost certainly benign, but "almost certainly" is not a
# security model: anything injected here would run on the site's own origin.
# So we rebuild each fragment from an allowlist and throw away everything else.

ALLOWED_TAGS = {
    "article", "section", "div", "h2", "h3", "h4", "h5", "p", "ol", "ul", "li",
    "a", "em", "strong", "b", "i", "u", "br", "hr", "blockquote", "span",
    "small", "code", "pre", "time", "figure", "figcaption", "sup", "sub",
}
VOID_TAGS = {"br", "hr"}

# Attributes allowed on any tag, plus per-tag extras.
ALLOWED_ATTRS_GLOBAL = {"class", "id", "title", "lang", "dir"}
ALLOWED_ATTRS_BY_TAG = {
    "a": {"href"},
    "article": {"data-date"},
    "time": {"datetime"},
}
# Anything inside these is dropped wholesale, not just unwrapped.
DROP_CONTENT_TAGS = {
    "script", "style", "iframe", "object", "embed", "noscript", "template",
    "form", "input", "button", "select", "textarea", "svg", "math",
}
SAFE_URL_RE = re.compile(r"^(https?:|mailto:|#|/|\./)", re.IGNORECASE)


class BriefSanitiser(HTMLParser):
    """Rebuild an ai-brief fragment from an allowlist of tags and attributes.

    Capture starts at <article class="ai-brief"> when present. If the generator
    ever emits a whole HTML document instead of a fragment, we fall back to
    capturing the <body> and wrapping it, so a format slip degrades rather than
    breaking the page.
    """

    def __init__(self, capture_root: str = "article") -> None:
        super().__init__(convert_charrefs=True)
        self.capture_root = capture_root
        self.parts: list[str] = []
        self.capturing = False
        self._root_depth = 0        # nesting depth of the capture-root tag
        self._drop_depth = 0        # >0 while inside a dropped element
        self._open: list[str] = []  # stack of emitted tags, for tidy closing
        self.dropped_tags: set[str] = set()

    # -- helpers ------------------------------------------------------------
    def _is_root(self, tag: str, attrs: dict[str, str]) -> bool:
        if self.capture_root == "article":
            return tag == "article" and "ai-brief" in (attrs.get("class") or "")
        return tag == self.capture_root

    def _clean_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = ALLOWED_ATTRS_GLOBAL | ALLOWED_ATTRS_BY_TAG.get(tag, set())
        out = []
        external = False
        for name, value in attrs:
            name = (name or "").lower()
            if name.startswith("on"):        # inline event handlers
                continue
            if name not in allowed:
                continue
            value = value or ""
            if name == "href":
                if not SAFE_URL_RE.match(value.strip()):
                    continue             # javascript:, data:, etc.
                external = value.strip().lower().startswith("http")
            out.append(f'{name}="{html.escape(value, quote=True)}"')
        if tag == "a" and external:
            # Open news links in a new tab, and deny the target page access to
            # window.opener.
            out.append('target="_blank"')
            out.append('rel="noopener noreferrer"')
        return (" " + " ".join(out)) if out else ""

    # -- HTMLParser interface ----------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrd = {(k or "").lower(): (v or "") for k, v in attrs}

        if self._drop_depth:
            if tag in DROP_CONTENT_TAGS and tag not in VOID_TAGS:
                self._drop_depth += 1
            return

        if tag in DROP_CONTENT_TAGS:
            self.dropped_tags.add(tag)
            if tag not in VOID_TAGS:
                self._drop_depth = 1
            return

        if not self.capturing:
            if self._is_root(tag, attrd):
                self.capturing = True
                self._root_depth = 1
                self.parts.append(f"<article{self._clean_attrs('article', attrs)}>")
                self._open.append("article")
            return

        if tag == self.capture_root or (self.capture_root == "article" and tag == "article"):
            self._root_depth += 1

        if tag not in ALLOWED_TAGS:
            self.dropped_tags.add(tag)
            return  # unwrap: keep the text, discard the tag

        if tag in VOID_TAGS:
            self.parts.append(f"<{tag}>")
        else:
            self.parts.append(f"<{tag}{self._clean_attrs(tag, attrs)}>")
            self._open.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._drop_depth:
            if tag in DROP_CONTENT_TAGS:
                self._drop_depth -= 1
            return
        if not self.capturing:
            return

        is_root_tag = tag == "article" if self.capture_root == "article" else tag == self.capture_root
        if is_root_tag:
            self._root_depth -= 1
            if self._root_depth <= 0:
                while self._open:
                    self.parts.append(f"</{self._open.pop()}>")
                self.capturing = False
                return

        if tag in VOID_TAGS or tag not in ALLOWED_TAGS:
            return
        if tag in self._open:
            # Close everything opened after it too, so stray markup can't leak
            # an unbalanced tag into the page.
            while self._open:
                closing = self._open.pop()
                self.parts.append(f"</{closing}>")
                if closing == tag:
                    break

    def handle_data(self, data):
        if self.capturing and not self._drop_depth:
            self.parts.append(html.escape(data, quote=False))

    def handle_entityref(self, name):   # only reached if convert_charrefs off
        if self.capturing and not self._drop_depth:
            self.parts.append(f"&{name};")

    def result(self) -> str:
        while self._open:
            self.parts.append(f"</{self._open.pop()}>")
        return "".join(self.parts).strip()


def sanitise_fragment(raw: str, date_str: str) -> tuple[str, list[str]]:
    """Return (clean_html, warnings). Always returns a single <article> root."""
    warnings: list[str] = []

    parser = BriefSanitiser(capture_root="article")
    parser.feed(raw)
    cleaned = parser.result()

    if not cleaned:
        # No <article class="ai-brief"> found. Try the <body>, then the raw text.
        warnings.append("no <article class=\"ai-brief\"> found; fell back to <body>")
        fallback = BriefSanitiser(capture_root="body")
        fallback.feed(raw)
        inner = fallback.result()
        if inner.startswith("<article"):
            inner = re.sub(r"^<article[^>]*>", "", inner)
            inner = re.sub(r"</article>$", "", inner)
        if not inner.strip():
            warnings.append("no usable HTML content in file")
            return "", warnings
        cleaned = f'<article class="ai-brief" data-date="{html.escape(date_str)}">{inner}</article>'

    if parser.dropped_tags:
        warnings.append("removed disallowed tags: " + ", ".join(sorted(parser.dropped_tags)))

    # Guarantee data-date matches the filename, which is the authoritative date.
    if 'data-date=' not in cleaned.split(">", 1)[0]:
        cleaned = cleaned.replace("<article", f'<article data-date="{html.escape(date_str)}"', 1)
    else:
        cleaned = re.sub(
            r'(<article[^>]*?)data-date="[^"]*"',
            rf'\1data-date="{html.escape(date_str)}"',
            cleaned,
            count=1,
        )
    return cleaned, warnings


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(fragment: str) -> str:
    return html.unescape(TAG_RE.sub(" ", fragment))


def extract_title(fragment: str, date_str: str) -> str:
    m = re.search(r"<h2[^>]*>(.*?)</h2>", fragment, re.DOTALL | re.IGNORECASE)
    if m:
        title = " ".join(strip_tags(m.group(1)).split())
        if title:
            return title
    return f"AI Brief — {pretty_date(date_str)}"


def extract_sources(fragment: str) -> str:
    m = re.search(
        r'<p[^>]*class="[^"]*\bsources\b[^"]*"[^>]*>(.*?)</p>',
        fragment, re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    text = " ".join(strip_tags(m.group(1)).split())
    return re.sub(r"^Sources:\s*", "", text, flags=re.IGNORECASE)


def count_items(fragment: str) -> int:
    return len(re.findall(r"<li\b", fragment, re.IGNORECASE))


def pretty_date(date_str: str) -> str:
    try:
        d = dt.date.fromisoformat(date_str)
    except ValueError:
        return date_str
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------
def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o644)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Drive access
# ---------------------------------------------------------------------------
def build_drive_service(cfg: Config):
    """Return an authenticated Drive client, plus a label for logging.

    Prefers an API key (link-shared folder) and falls back to a service-account
    key file (private folder).
    """
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        # Give the exact command for THIS interpreter. A generic "pip install"
        # hint sends people to the system pip, which installs somewhere the
        # venv running this script will never look.
        die(
            f"Missing Google API libraries ({exc}).\n"
            "Install them into the interpreter running this script:\n"
            f"  {sys.executable} -m pip install -r {SCRIPT_DIR / 'requirements.txt'}"
        )

    if cfg.api_key:
        return build("drive", "v3", developerKey=cfg.api_key, cache_discovery=False), "API key"

    if cfg.sa_key.is_file():
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            str(cfg.sa_key), scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False), (
            f"service account ({cfg.sa_key.name})"
        )

    die(
        "No credentials found. Set one of:\n"
        "  AI_BRIEF_API_KEY  -- a Google Cloud API key, with the Drive folder\n"
        "                       shared 'Anyone with the link can view'\n"
        f"  AI_BRIEF_SA_KEY   -- path to a service-account JSON key (looked for\n"
        f"                       {cfg.sa_key}, which does not exist)\n"
        "See ai_brief/README.md."
    )


def list_all_files(service, folder_id: str) -> list[dict]:
    """Everything visible in the folder, whatever it is called."""
    files, page_token = [], None
    query = f"'{folder_id}' in parents and trashed = false"
    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, md5Checksum, modifiedTime, size)",
                pageSize=200,
                orderBy="name",
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def list_brief_files(service, folder_id: str) -> list[dict]:
    """Only the files whose names match the agreed contract."""
    return [f for f in list_all_files(service, folder_id) if FILENAME_RE.match(f["name"])]


def download_file(service, meta: dict) -> str:
    import io
    from googleapiclient.http import MediaIoBaseDownload

    if meta.get("mimeType") == GOOGLE_DOC_MIME:
        # The task was meant to save raw HTML; if it saved a Google Doc instead,
        # export it rather than failing outright.
        request = service.files().export_media(fileId=meta["id"], mimeType="text/html")
    else:
        request = service.files().get_media(fileId=meta["id"], supportsAllDrives=True)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def read_manifest(path: Path) -> dict:
    if not path.is_file():
        return {"briefs": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"briefs": []}


def entry_for(date_str: str, path: Path, fragment: str, source: dict | None) -> dict:
    return {
        "date": date_str,
        "file": path.name,
        "label": pretty_date(date_str),
        "title": extract_title(fragment, date_str),
        "sources": extract_sources(fragment),
        "items": count_items(fragment),
        "bytes": len(fragment.encode("utf-8")),
        "md5": (source or {}).get("md5Checksum", ""),
        "driveModified": (source or {}).get("modifiedTime", ""),
        "sha256": hashlib.sha256(fragment.encode("utf-8")).hexdigest()[:16],
    }


def write_manifest(cfg: Config, entries: list[dict], dry_run: bool) -> None:
    entries.sort(key=lambda e: e["date"], reverse=True)
    manifest = {
        "generated": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(entries),
        "latest": entries[0]["date"] if entries else None,
        "dir": cfg.out_dir.name,
        "briefs": entries,
    }
    if dry_run:
        log(f"[dry-run] would write manifest with {len(entries)} entries")
        return
    atomic_write(cfg.manifest, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{stamp}  {msg}", flush=True)


def die(msg: str, code: int = 1):
    log("ERROR: " + msg)
    sys.exit(code)


def access_hint(cfg: Config) -> str:
    """Point at the most likely cause of a Drive access failure."""
    if cfg.api_key:
        return (
            "Most likely one of:\n"
            "  - the folder is not shared 'Anyone with the link can view'\n"
            "    (an API key can only see publicly shared files)\n"
            "  - the folder ID is wrong\n"
            "  - the Drive API is not enabled on the project that owns the key\n"
            "  - the key has an HTTP-referrer restriction; server-side use needs\n"
            "    either no restriction or an IP restriction"
        )
    return (
        "Most likely one of:\n"
        "  - the folder was never shared with the service-account email\n"
        "  - the folder ID is wrong\n"
        "  - the Drive API is not enabled on the project that owns the key"
    )


def check(cfg: Config) -> int:
    """Verify configuration and folder access. Downloads nothing."""
    ok = True
    log("Configuration:")
    if cfg.env_found:
        note = f" (blank: {', '.join(cfg.env_blank)})" if cfg.env_blank else ""
        log(f"  .env       : {cfg.env_file}{note}")
    else:
        log(f"  .env       : NOT FOUND at {cfg.env_file}")
        log("               copy .env.example to .env and fill it in")
    log(f"  folder ID  : {cfg.folder_id or '(not set)'}")
    log(f"  auth       : {'API key (…' + cfg.api_key[-6:] + ')' if cfg.api_key else ('service account: ' + str(cfg.sa_key)) }")
    log(f"  output dir : {cfg.out_dir}")
    log(f"  manifest   : {cfg.manifest}")

    if not cfg.folder_id:
        log("  ! AI_BRIEF_FOLDER_ID is not set")
        return 1
    if not cfg.api_key and not cfg.sa_key.is_file():
        log(f"  ! no API key set and no service-account key at {cfg.sa_key}")
        if "AI_BRIEF_API_KEY" in cfg.env_blank:
            log("    AI_BRIEF_API_KEY exists in .env but has no value after the '='.")
            log("    Paste the key there — and check you edited .env, not .env.example.")
        elif cfg.env_found:
            log("    .env has no AI_BRIEF_API_KEY line at all. Add:")
            log("      AI_BRIEF_API_KEY=AIza...")
        return 1

    service, how = build_drive_service(cfg)
    log(f"Connecting with {how}…")

    # Probe the folder itself first. This matters: files.list with a
    # "'<id>' in parents" query does NOT fail when the caller cannot see the
    # folder -- it just returns nothing, which looks identical to an empty
    # folder. files.get does fail, so it tells us which of the two it is.
    try:
        meta = service.files().get(
            fileId=cfg.folder_id, fields="id,name,mimeType", supportsAllDrives=True
        ).execute()
    except Exception as exc:  # noqa: BLE001
        log(f"  ! cannot read the folder itself: {exc}")
        for line in access_hint(cfg).splitlines():
            log("    " + line)
        return 1

    log(f"  folder: {meta.get('name')!r}")
    if meta.get("mimeType") != "application/vnd.google-apps.folder":
        log(f"  ! that ID is not a folder -- it is a {meta.get('mimeType')}")
        log("    AI_BRIEF_FOLDER_ID must be the folder that holds the daily files,")
        log("    not a document. Open the folder in Drive and copy the last part of")
        log("    the URL: https://drive.google.com/drive/folders/<THIS>")
        return 1

    try:
        everything = list_all_files(service, cfg.folder_id)
    except Exception as exc:  # noqa: BLE001
        log(f"  ! could not list the folder: {exc}")
        for line in access_hint(cfg).splitlines():
            log("    " + line)
        return 1

    remote = [f for f in everything if FILENAME_RE.match(f["name"])]
    log(f"  folder is readable: {len(everything)} item(s) visible, "
        f"{len(remote)} matching ai-brief-YYYY-MM-DD.html")

    for meta in sorted(remote, key=lambda m: m["name"], reverse=True)[:5]:
        log(f"    ✓ {meta['name']}  ({meta.get('size', '?')} bytes, "
            f"modified {meta.get('modifiedTime', '?')})")
    if len(remote) > 5:
        log(f"    … and {len(remote) - 5} more")

    # Show what did NOT match, which is what you actually need when the count
    # is zero: wrong name, wrong extension, or a Google Doc instead of HTML.
    others = [f for f in everything if not FILENAME_RE.match(f["name"])]
    if others:
        log(f"  {len(others)} item(s) in the folder do NOT match the expected name:")
        for meta in others[:10]:
            kind = meta.get("mimeType", "?").replace("application/vnd.google-apps.", "google-")
            log(f"    ✗ {meta['name']!r}  [{kind}]")
        if len(others) > 10:
            log(f"    … and {len(others) - 10} more")
        log("    Expected form: ai-brief-2026-07-27.html  (lower case, no spaces,")
        log("    four-digit year, zero-padded month and day, .html extension)")
        ok = False

    if not everything:
        log("  ! the folder is readable but genuinely empty.")
        log("    Nothing has been saved into it yet. The generating task needs to")
        log("    write ai-brief-YYYY-MM-DD.html files here.")
        ok = False
    elif not remote:
        log("  ! nothing in the folder matches the agreed filename contract (see above).")
        ok = False

    if not os.access(cfg.out_dir.parent, os.W_OK):
        log(f"  ! cannot write to {cfg.out_dir.parent}")
        ok = False

    log("Check " + ("passed. Run without --check to download." if ok else "found problems (above)."))
    return 0 if ok else 1


def rebuild_from_local(cfg: Config, dry_run: bool) -> int:
    """Rebuild the manifest from whatever is already on disk. No network."""
    entries = []
    for path in sorted(cfg.out_dir.glob("ai-brief-*.html")):
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        fragment = path.read_text(encoding="utf-8")
        entries.append(entry_for(date_str, path, fragment, None))
    write_manifest(cfg, entries, dry_run)
    log(f"Rebuilt manifest from {len(entries)} local file(s).")
    return 0


def run(cfg: Config, args) -> int:
    if not cfg.folder_id:
        die(
            "AI_BRIEF_FOLDER_ID is not set.\n"
            "Put it in ai_brief/.env (see .env.example) or export it before running."
        )

    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    previous = {e["date"]: e for e in read_manifest(cfg.manifest).get("briefs", [])}

    service, how = build_drive_service(cfg)
    log(f"Authenticating with {how}")
    try:
        remote = list_brief_files(service, cfg.folder_id)
    except Exception as exc:  # noqa: BLE001 -- surface the API error verbatim
        die(f"Could not list Drive folder {cfg.folder_id}: {exc}\n" + access_hint(cfg))
        return 1

    log(f"Drive folder has {len(remote)} file(s) matching ai-brief-YYYY-MM-DD.html")
    if not remote:
        log("Nothing to do. (Has the folder been shared with the service account?)")

    entries: dict[str, dict] = dict(previous)
    added = updated = skipped = failed = 0

    for meta in remote:
        m = FILENAME_RE.match(meta["name"])
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        target = cfg.out_dir / meta["name"]
        prior = previous.get(date_str)

        unchanged = (
            prior
            and target.is_file()
            and prior.get("md5")
            and prior.get("md5") == meta.get("md5Checksum")
        )
        if unchanged and not args.force:
            skipped += 1
            continue

        try:
            raw = download_file(service, meta)
        except Exception as exc:  # noqa: BLE001
            log(f"  ! {meta['name']}: download failed ({exc})")
            failed += 1
            continue

        fragment, warnings = sanitise_fragment(raw, date_str)
        if not fragment:
            log(f"  ! {meta['name']}: no usable content after sanitising; skipped")
            failed += 1
            continue
        for w in warnings:
            log(f"  ~ {meta['name']}: {w}")

        if args.dry_run:
            log(f"  [dry-run] would write {target.name} ({len(fragment)} chars)")
        else:
            atomic_write(target, fragment + "\n")

        entries[date_str] = entry_for(date_str, target, fragment, meta)
        if prior:
            updated += 1
            log(f"  ^ updated {meta['name']}")
        else:
            added += 1
            log(f"  + added   {meta['name']}")

    # Drop manifest entries whose local file has vanished.
    for date_str in list(entries):
        if not (cfg.out_dir / entries[date_str]["file"]).is_file() and not args.dry_run:
            log(f"  - local file missing, dropping {entries[date_str]['file']} from manifest")
            del entries[date_str]

    write_manifest(cfg, list(entries.values()), args.dry_run)
    log(
        f"Done. added={added} updated={updated} unchanged={skipped} "
        f"failed={failed} total={len(entries)}"
    )
    return 1 if failed and not (added or updated) else 0


def self_test() -> int:
    """Sanitiser checks. No network, no credentials."""
    cases = []

    good = """
    <article class="ai-brief" data-date="2026-07-24">
      <h2>AI Brief &mdash; Thursday, 24 July 2026</h2>
      <p class="subtitle">AI and its implications for education</p>
      <ol><li><a href="https://example.com/a">Headline</a><p>Why it matters.</p></li>
          <li><a href="https://example.com/b">Second</a><p>More.</p></li></ol>
      <p class="sources">Sources: Nature, EDUCAUSE</p>
    </article>"""
    out, _ = sanitise_fragment(good, "2026-07-24")
    cases.append(("keeps headings", "<h2>" in out))
    cases.append(("keeps list items", count_items(out) == 2))
    cases.append(("adds noopener", 'rel="noopener noreferrer"' in out))
    cases.append(("title extracted", "Thursday" in extract_title(out, "2026-07-24")))
    cases.append(("sources extracted", extract_sources(out) == "Nature, EDUCAUSE"))

    nasty = """<article class="ai-brief" data-date="2026-07-25">
      <h2>Test</h2><script>alert('xss')</script>
      <p onclick="steal()">Text <a href="javascript:evil()">bad link</a></p>
      <iframe src="https://evil.example"></iframe>
      <img src=x onerror=alert(1)>
      <p>Tail</p></article>"""
    out2, warns = sanitise_fragment(nasty, "2026-07-25")
    cases.append(("script removed", "alert" not in out2 and "<script" not in out2))
    cases.append(("handler removed", "onclick" not in out2))
    cases.append(("js: href removed", "javascript:" not in out2))
    cases.append(("iframe removed", "<iframe" not in out2))
    cases.append(("img removed", "onerror" not in out2))
    cases.append(("kept surrounding text", "Tail" in out2 and "Text" in out2))
    cases.append(("warned", any("removed disallowed" in w for w in warns)))

    doc = """<!doctype html><html><head><title>x</title><style>p{}</style></head>
      <body><h2>Whole document</h2><p>Body text</p></body></html>"""
    out3, warns3 = sanitise_fragment(doc, "2026-07-26")
    cases.append(("whole-doc fallback", out3.startswith("<article") and "Body text" in out3))
    cases.append(("fallback warns", any("fell back" in w for w in warns3)))
    cases.append(("style dropped", "p{}" not in out3))

    out4, _ = sanitise_fragment('<article class="ai-brief" data-date="1999-01-01"><p>x</p></article>', "2026-07-27")
    cases.append(("date forced from filename", 'data-date="2026-07-27"' in out4))

    cases.append(("pretty date", pretty_date("2026-07-24") == "Friday, 24 July 2026"))

    failures = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{len(cases) - len(failures)}/{len(cases)} checks passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="test credentials and folder access, download nothing")
    ap.add_argument("--dry-run", action="store_true", help="report changes without writing")
    ap.add_argument("--force", action="store_true", help="re-download every file")
    ap.add_argument("--rebuild", action="store_true", help="rebuild manifest from local files only")
    ap.add_argument("--self-test", action="store_true", help="run sanitiser checks and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    cfg = Config()
    if args.check:
        return check(cfg)
    if args.rebuild:
        return rebuild_from_local(cfg, args.dry_run)
    return run(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
