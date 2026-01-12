#!/usr/bin/env python3
"""
AI News & Podcast Scanner v2
============================
Improved version with:
- Better keyword matching (regex-based, case-insensitive)
- Stronger model prompting to retain AI-related podcasts
- Separate podcast-only model call to avoid drowning in news items
"""

import os
import re
import time
import hashlib
import subprocess
import email.utils
from datetime import datetime, timedelta

import feedparser
from dotenv import load_dotenv
from openai import OpenAI

# ----------------- CONFIG -----------------

# News RSS feeds
NEWS_FEEDS = {
    "Science": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
    "Nature": "https://www.nature.com/nature.rss",
    "Nature Machine Intelligence": "https://www.nature.com/natmachintell.rss",
    # "Anthropic": "https://www.anthropic.com/news/rss.xml",  # Feed no longer exists - removed
    "Center for AI Safety Newsletter": "https://newsletter.safe.ai/feed",  # Updated to Substack feed
    "Future of Life Institute": "https://futureoflife.org/feed/",
    "AI Now Institute": "https://ainowinstitute.org/category/news/feed",  # Updated URL
    "OpenAI": "https://openai.com/blog/rss.xml",
    # "DeepMind": "https://deepmind.google/feed/basic.xml",  # Feed no longer exists - removed
    # "Brookings – AI & Emerging Tech": "https://www.brookings.edu/series/artificial-intelligence/feed/",  # Feed no longer exists - removed
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    "The Conversation – Technology": "https://theconversation.com/us/technology/articles.atom",
    "The Conversation – Education": "https://theconversation.com/us/education/articles.atom",
}

# Podcast RSS feeds – broad, big-picture shows.
PODCAST_FEEDS = {
    "The Daily": "https://feeds.simplecast.com/54nAGcIl",
    "Lex Fridman Podcast": "https://lexfridman.com/feed/podcast/",
    "Making Sense with Sam Harris": "https://wakingup.libsyn.com/rss",
    "The Ezra Klein Show": "https://feeds.simplecast.com/kEKXbjuJ",  # Updated to working Simplecast feed
    "Eye on A.I.": "https://aneyeonai.libsyn.com/rss",  # Updated to working Libsyn feed
    "The Last Invention": "https://feeds.megaphone.fm/thelastinvention",  # Working feed (tested)
    "The Diary Of A CEO": "https://rss2.flightcast.com/xmsftuzjjykcmqwolaqn6mdn",
    # "The Good Fight": "https://feeds.megaphone.fm/thegoodfight",  # Feed no longer exists - removed
    "MIT Technology Review Narrated": "https://feeds.megaphone.fm/inmachineswetrust",  # Rebranded, working feed
    # "In Machines We Trust AI": "https://feeds.megaphone.fm/inmachineswetrustai",  # Feed no longer exists - removed
    "Google DeepMind: The Podcast": "https://feeds.simplecast.com/JT6pbPkg",
}

OUTPUT_DIR = "ai_news_outputs"
USAGE_LOG_FILE = "ai_usage_log.csv"

# Max total items in final briefing (news + podcasts together)
MAX_ITEMS_TOTAL = 12

# Max number of candidate items we ever send to the model
MAX_CANDIDATES_FOR_MODEL = 120

# Max characters of summary per item passed into the model
MAX_SUMMARY_CHARS = 800

# --- MODEL & PRICING ---

MODEL_NAME = "gpt-4o-mini"  # Changed from gpt-5-mini which doesn't exist

# Pricing for gpt-4o-mini (USD per 1M tokens)
MODEL_PRICING = {
    "gpt-4o-mini": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
    },
    "gpt-4o": {
        "input_per_million": 2.50,
        "output_per_million": 10.00,
    },
}

# ----------------- IMPROVED AI KEYWORD DETECTION -----------------

# Regex patterns for AI relevance (case-insensitive, word-boundary aware)
AI_PATTERNS = [
    r'\bai\b',                      # "AI" as a word (not "said", "wait", etc.)
    r'\ba\.i\.\b',                # "A.I."
    r'\bartificial intelligence\b',
    r'\bagi\b',                     # Artificial General Intelligence
    r'\bmachine[-\s]?learning\b',  # machine learning / machine-learning
    r'\bdeep[-\s]?learning\b',
    r'\bneural networks?\b',        # neural network(s)
    r'\blarge language models?\b',  # LLM / LLMs
    r'\bllms?\b',
    r'\bgpt[-\s]?\d+(?:\.\d+)?\b',  # GPT-4, GPT 5, GPT-5.1, etc.
    r'\bchat\s*gpt\b',
    r'\bclaude\b',                  # Anthropic's Claude
    r'\bgemini\b',                  # Google's Gemini (context-dependent but worth catching)
    r'\bopenai\b',
    r'\banthropic\b',
    r'\bdeepmi?nd\b',               # DeepMind
    r'\balignment\b',               # AI alignment
    r'\bai safety\b',
    r'\b(ai\s*risk|ai\s*risks)\b',
    r'\bai polic(?:y|ies)\b',       # policy, policies
    r'\bai govern(?:ance|ment)\b',  # governance, government
    r'\bai regulation\b',
    r'\bai ethics\b',
    r'\bgenerative\s*ai\b',
    r'\bfoundation model(s)?\b',
    r'\btransformer\s*(model|architecture)?\b',
    r'\breinforcement learning\b',
    r'\bautonomous\s+(weapon|system|agent)s?\b',
]

# Compile patterns for efficiency
_AI_REGEX = re.compile('|'.join(AI_PATTERNS), re.IGNORECASE)


def is_ai_related_text(text: str) -> bool:
    """
    Check if text is AI-related using regex patterns.

    Strips HTML and URLs/domains before matching to avoid false positives
    caused by domains like "mgln.ai" appearing in titles or summaries.
    """
    if not text:
        return False

    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)

    # Remove URLs and bare domains (http(s) links, www., and tokens like example.ai)
    clean = re.sub(r'https?://\S+|www\.\S+|\b\S+\.\w{2,}\b', ' ', clean)

    # Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()

    return bool(_AI_REGEX.search(clean))


# ----------------- SETUP -----------------

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------- UTILITIES -----------------

def get_entry_summary(entry):
    """
    Try to get a short textual summary/description from the RSS entry.
    """
    for attr in ["summary", "description"]:
        if getattr(entry, attr, None):
            return getattr(entry, attr)
    return getattr(entry, "title", "")


def notify_mac(message: str):
    """
    Show a macOS notification (no-op if osascript is unavailable).
    """
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{message}" with title "AI Feeds"'
            ],
            check=False,
        )
    except Exception:
        pass


def log_usage(model_name: str, usage, cost_usd: float):
    """
    Append usage info to a CSV file: timestamp, model, tokens, cost.
    """
    timestamp = datetime.now().isoformat(timespec="seconds")

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    file_exists = os.path.exists(USAGE_LOG_FILE)

    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write(
                "timestamp,model,prompt_tokens,completion_tokens,total_tokens,cost_usd\n"
            )
        f.write(
            f"{timestamp},{model_name},{prompt_tokens},{completion_tokens},"
            f"{total_tokens},{cost_usd:.6f}\n"
        )


def compute_cost(model_name: str, usage):
    """
    Compute rough cost in USD from token usage and MODEL_PRICING.
    """
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0

    pricing = MODEL_PRICING.get(model_name)
    if not pricing:
        return 0.0

    input_rate = pricing["input_per_million"] / 1_000_000.0
    output_rate = pricing["output_per_million"] / 1_000_000.0

    return prompt_tokens * input_rate + completion_tokens * output_rate


def parse_entry_date(entry):
    """
    Try to parse a feed entry's published/updated date.
    Returns a naive datetime (local time) or None if not parseable.
    """
    for attr in ["published_parsed", "updated_parsed"]:
        parsed = getattr(entry, attr, None)
        if parsed is not None:
            try:
                return datetime.fromtimestamp(time.mktime(parsed))
            except Exception:
                pass

    for attr in ["published", "updated", "pubDate"]:
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = email.utils.parsedate_to_datetime(val)
                if dt.tzinfo is not None:
                    dt = dt.astimezone().replace(tzinfo=None)
                return dt
            except Exception:
                pass

    return None


def make_uid(feed_url, entry, dt):
    """
    Create a reasonably stable ID per entry.
    """
    candidates = []
    if getattr(entry, "id", None):
        candidates.append(str(entry.id))
    if getattr(entry, "link", None):
        candidates.append(str(entry.link))
    if getattr(entry, "title", None):
        candidates.append(str(entry.title))
    if dt is not None:
        candidates.append(dt.isoformat())

    base = "|".join(candidates) if candidates else f"{feed_url}|{time.time()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def get_entry_link(entry):
    """
    Try to get a usable URL for an entry.
    """
    link = getattr(entry, "link", None)
    if link:
        return link

    links = getattr(entry, "links", None)
    if links:
        for l in links:
            if isinstance(l, dict):
                href = l.get("href")
                if href:
                    return href

    enclosures = getattr(entry, "enclosures", None)
    if enclosures:
        for enc in enclosures:
            if isinstance(enc, dict):
                href = enc.get("href")
                if href:
                    return href

    entry_id = getattr(entry, "id", None)
    if isinstance(entry_id, str) and entry_id.startswith("http"):
        return entry_id

    return None


# ----------------- FETCH FEEDS (LAST 7 DAYS) -----------------

def collect_items_last_week():
    """
    Fetch items from news & podcast feeds published in the last 7 days.

    Returns:
      news_items: all news items (model will filter for AI relevance)
      podcast_items: AI-keyword-matched podcast episodes
      podcast_debug: all podcast episodes for debugging
      feed_stats: per-feed statistics
    """
    seven_days_ago = datetime.now() - timedelta(days=7)

    news_items = []
    podcast_items = []
    podcast_debug = []
    seen_uids = set()

    # Track per-feed statistics
    feed_stats = {}

    def process_feed(feed_name, feed_url, item_type):
        nonlocal news_items, podcast_items, seen_uids, podcast_debug, feed_stats
        if not feed_url:
            return

        # Initialize stats for this feed
        feed_stats[feed_name] = {
            'type': item_type,
            'total_7days': 0,
            'ai_matched': 0,
            'error': None,
            'last_item_date': None
        }

        print(f"  Downloading {feed_name}...", end=" ", flush=True)

        try:
            # Add timeout to prevent hanging on slow feeds
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)  # 30 second timeout

            parsed = feedparser.parse(feed_url)

            # Restore original timeout
            socket.setdefaulttimeout(original_timeout)

            print("✓")
        except Exception as e:
            print(f"✗ (Error: {e})")
            feed_stats[feed_name]['error'] = str(e)
            # Restore timeout even on error
            try:
                socket.setdefaulttimeout(original_timeout)
            except:
                pass
            return

        feed_title = getattr(parsed.feed, "title", feed_name) or feed_name

        # Track the most recent item date (even if outside 7-day window)
        all_entries = getattr(parsed, "entries", [])
        if all_entries:
            for entry in all_entries:
                entry_date = parse_entry_date(entry)
                if entry_date is not None:
                    if feed_stats[feed_name]['last_item_date'] is None or entry_date > feed_stats[feed_name]['last_item_date']:
                        feed_stats[feed_name]['last_item_date'] = entry_date
                    break  # Assuming entries are sorted newest first

        for entry in all_entries:
            entry_date = parse_entry_date(entry)
            if entry_date is None:
                continue

            if entry_date < seven_days_ago:
                continue

            link = get_entry_link(entry) or ""
            title = (getattr(entry, "title", "") or "").strip()
            if not title:
                continue

            summary = (get_entry_summary(entry) or "").strip()

            uid = make_uid(feed_url, entry, entry_date)
            if uid in seen_uids:
                continue
            seen_uids.add(uid)

            # Count this item for the feed
            feed_stats[feed_name]['total_7days'] += 1

            item_data = {
                "uid": uid,
                "source": feed_title,
                "title": title,
                "summary": summary,
                "link": link,
                "item_type": item_type,
                "date": entry_date.isoformat(),
            }

            # Check for AI keywords in both news and podcasts
            combined_text = f"{title}\n{summary}"
            ai_match = is_ai_related_text(combined_text)

            if item_type == "podcast":
                # Debug list: all podcasts (for manual review)
                podcast_debug.append({
                    **item_data,
                    "ai_keyword_match": ai_match,
                })

                # Only include podcast episodes that matched AI keywords for the model
                if ai_match:
                    podcast_items.append(item_data)
                    feed_stats[feed_name]['ai_matched'] += 1
            else:
                # Only include news items that matched AI keywords for the model
                # (These items were pre-filtered by the keyword detector; the model
                #  should order and summarize ALL supplied items.)
                if ai_match:
                    news_items.append(item_data)
                    feed_stats[feed_name]['ai_matched'] += 1

    print("Fetching news feeds...")
    for name, url in NEWS_FEEDS.items():
        print(f"  {name}")
        process_feed(name, url, "news")

    print("Fetching podcast feeds...")
    for name, url in PODCAST_FEEDS.items():
        print(f"  {name}")
        process_feed(name, url, "podcast")

    # Sort newest first
    news_items.sort(key=lambda x: x["date"], reverse=True)
    podcast_items.sort(key=lambda x: x["date"], reverse=True)
    podcast_debug.sort(key=lambda x: x["date"], reverse=True)

    print(f"\nFound {len(news_items)} news items, {len(podcast_items)} podcast episodes "
          f"(to be filtered by model)")

    return news_items, podcast_items, podcast_debug, feed_stats


# ----------------- LLM CALLS -----------------

def determine_priority(item):
    """
    Assign a priority tag (HIGH, MEDIUM, LOW) to guide ordering.
    HIGH = societal impact, AGI/ASI, alignment, governance, policy, education, research, climate
    LOW  = primarily technical items (benchmarks, parameters, infra, model internals)
    MEDIUM = items in-between
    """
    text = ((item.get('title') or '') + ' ' + (item.get('summary') or '')).lower()

    HIGH_PATTERNS = [
        r'\bagi\b', r'\basi\b', r'\balignment\b', r'\bai safety\b',
        r'\bgovern(?:ance|ment)\b', r'\bpolicy\b', r'\bregulat', r'\bethic',
        r'\bsociet', r'\beducation\b', r'\bresearch\b', r'\bimpact\b', r'\bclimat'
    ]

    TECHNICAL_PATTERNS = [
        r'\bgpt\b', r'\bllm(s)?\b', r'\bmodel(s)?\b', r'\bparameters?\b',
        r'\bbenchmark(s)?\b', r'\bcompute\b', r'\binfrastructure\b', r'\blatency\b',
        r'\boptimis', r'\bperformance\b', r'\bagent(s)?\b', r'\bcodex\b',
        r'\bdeep[-\s]?learning\b', r'\bneural networks?\b'
    ]

    for pat in HIGH_PATTERNS:
        if re.search(pat, text):
            return "HIGH"

    for pat in TECHNICAL_PATTERNS:
        if re.search(pat, text):
            return "LOW"

    return "MEDIUM"


def build_items_text(items):
    """
    Construct plain-text blocks describing each item for the model.
    Each block contains a Priority field to guide the LLM's ordering.
    """
    blocks = []
    for i, item in enumerate(items, start=1):
        truncated_summary = (item["summary"] or "").replace("\n", " ")
        if len(truncated_summary) > MAX_SUMMARY_CHARS:
            truncated_summary = truncated_summary[:MAX_SUMMARY_CHARS] + "..."

        priority = determine_priority(item)

        block = [
            f"Item {i}:",
            f"Priority: {priority}",
            f"Type: {item['item_type']}",
            f"Source: {item['source']}",
            f"Title: {item['title']}",
            f"Date: {item['date']}",
            f"Summary: {truncated_summary}",
            f"Link: {item['link']}",
        ]
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)


def call_model_for_news(news_items):
    """
    Call model to filter and summarize AI-related NEWS items.
    """
    if not news_items:
        return "No news items to process.", None
        
    items_text = build_items_text(news_items)

    system_prompt = """
You are an AI research analyst producing a structured news briefing.
Output ONLY the markdown format described below, with NO extra commentary.

IMPORTANT: The list of NEWS ITEMS provided has already been pre-filtered for AI relevance by keyword matching. YOU MUST INCLUDE and SUMMARIZE ALL the items supplied. Do NOT exclude any items.

ORDERING RULES (use the provided Priority field):
1. Sort items by Priority: HIGH first, then MEDIUM, then LOW.
2. Within each Priority group, order by strategic importance:
   a. AGI / ASI / alignment / existential risk topics
   b. Societal impact, policy, governance, ethics
   c. Research & education impacts
   d. Broad impacts (climate, economics, public health)
   e. Technical developments, tools, benchmarks

TASK:
- For each supplied item, provide a one-line summary (~25 words) and a detailed summary (~150 words.
- Ensure the output list follows the exact ordering rules above; the first item should be N1, second N2, etc.
- Provide a brief list of keywords for each item.

OUTPUT FORMAT:
# AI & AGI News Briefing

## N1. <Title>
- **Source:** <Source>
- **URL:** <Link>
- **One-line summary:** <~25 words>
- **Detailed summary:** <~150 words>
- **Keywords:** keyword1; keyword2; keyword3

[Continue for ALL supplied items...]

If no items are provided, write: "No strongly AI-related news items found."
""".strip()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"NEWS ITEMS:\n\n{items_text}"},
        ],
    )

    return response.choices[0].message.content, response.usage


def call_model_for_podcasts(podcast_items):
    """
    Call model to summarize AI-related PODCAST episodes.
    These have already been pre-filtered by keywords, so we're more inclusive.
    """
    if not podcast_items:
        return "# AI & AGI Podcast Episodes\n\nNo AI-related podcast episodes found.", None

    items_text = build_items_text(podcast_items)

    system_prompt = """
You are an AI research analyst summarizing podcast episodes about AI.
Output ONLY the markdown format below, NO extra commentary.

The episodes provided are pre-filtered for AI relevance. YOU MUST INCLUDE and SUMMARIZE ALL supplied episodes.

ORDERING RULES (use the Priority field):
1. Sort episodes by Priority: HIGH (societal/AGI/education/research impact) first, then MEDIUM, then LOW (technical discussions).
2. Within priority, prefer episodes that examine societal impacts, policy, or AGI discussions.

OUTPUT FORMAT:
# AI & AGI Podcast Episodes

## P1. <Show> – <Episode Title>
- **Show:** <Show name>
- **Episode:** <Title>
- **Date:** <Date>
- **Summary:** <~150 words, accessible to general audience>
- **URL:** <Link>

[Continue for ALL supplied episodes...]

If no episodes are supplied, write: "No AI-related podcast episodes found."
""".strip()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"PODCAST EPISODES:\n\n{items_text}"},
        ],
    )

    return response.choices[0].message.content, response.usage


# ----------------- STATISTICS OUTPUT -----------------

def print_feed_statistics(feed_stats):
    """
    Print per-feed statistics to console in a formatted table.
    """
    print("\n" + "=" * 80)
    print("PER-FEED STATISTICS (Last 7 Days)")
    print("=" * 80)

    # Separate news and podcast feeds
    news_feeds = {k: v for k, v in feed_stats.items() if v['type'] == 'news'}
    podcast_feeds = {k: v for k, v in feed_stats.items() if v['type'] == 'podcast'}

    def print_section(title, feeds):
        print(f"\n{title}")
        print("-" * 100)
        print(f"{'Feed Name':<35} {'Total':<8} {'AI Kw':<8} {'Last Item':<20} {'Status'}")
        print("-" * 100)

        for name, stats in sorted(feeds.items()):
            total = stats['total_7days']
            matched = stats['ai_matched']
            error = stats.get('error')
            last_date = stats.get('last_item_date')

            # Format last item date
            if last_date:
                if isinstance(last_date, datetime):
                    days_ago = (datetime.now() - last_date).days
                    if days_ago == 0:
                        last_date_str = "Today"
                    elif days_ago == 1:
                        last_date_str = "Yesterday"
                    elif days_ago < 7:
                        last_date_str = f"{days_ago}d ago"
                    else:
                        last_date_str = last_date.strftime("%Y-%m-%d")
                else:
                    last_date_str = str(last_date)[:10]
            else:
                last_date_str = "Unknown"

            if error:
                status = f"ERROR: {str(error)[:20]}"
            elif total == 0 and not last_date:
                status = "⚠️ NO ITEMS"
            elif total == 0:
                status = "No new (7d)"
            elif matched == 0:
                status = "No AI matches"
            else:
                status = "✓"

            # Truncate long feed names
            display_name = name[:33] + ".." if len(name) > 35 else name
            print(f"{display_name:<35} {total:<8} {matched:<8} {last_date_str:<20} {status}")

        # Summary
        total_items = sum(s['total_7days'] for s in feeds.values())
        total_matched = sum(s['ai_matched'] for s in feeds.values())
        zero_feeds = sum(1 for s in feeds.values() if s['total_7days'] == 0 and not s.get('error'))
        error_feeds = sum(1 for s in feeds.values() if s.get('error'))

        print("-" * 80)
        print(f"{'TOTAL:':<40} {total_items:<10} {total_matched:<12}")
        if zero_feeds > 0:
            print(f"\n⚠️  {zero_feeds} feed(s) with no items in last 7 days")
        if error_feeds > 0:
            print(f"❌ {error_feeds} feed(s) with errors")

    print_section("📰 NEWS FEEDS", news_feeds)
    print_section("🎙️  PODCAST FEEDS", podcast_feeds)
    print("=" * 80 + "\n")


def write_feed_statistics_file(feed_stats, timestamp_str):
    """
    Write detailed feed statistics to a markdown file.
    """
    stats_path = os.path.join(OUTPUT_DIR, f"feed_stats_{timestamp_str}.md")

    lines = []
    lines.append("# RSS Feed Statistics Report\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("**Period:** Last 7 days\n")

    # Summary
    news_feeds = {k: v for k, v in feed_stats.items() if v['type'] == 'news'}
    podcast_feeds = {k: v for k, v in feed_stats.items() if v['type'] == 'podcast'}

    total_news = sum(s['total_7days'] for s in news_feeds.values())
    total_podcasts = sum(s['total_7days'] for s in podcast_feeds.values())
    matched_news = sum(s['ai_matched'] for s in news_feeds.values())
    matched_podcasts = sum(s['ai_matched'] for s in podcast_feeds.values())

    lines.append("\n## Summary\n")
    lines.append(f"- **News Feeds:** {len(news_feeds)} configured, {total_news} items found, {matched_news} with AI keywords (all sent to model)\n")
    lines.append(f"- **Podcast Feeds:** {len(podcast_feeds)} configured, {total_podcasts} items found, {matched_podcasts} with AI keywords (only these sent to model)\n")

    def write_section(title, feeds):
        lines.append(f"\n## {title}\n")
        lines.append("| Feed Name | Total Items (7d) | AI Keywords | Last Item Date | Status |")
        lines.append("|-----------|------------------|-------------|----------------|--------|")

        for name, stats in sorted(feeds.items()):
            total = stats['total_7days']
            matched = stats['ai_matched']
            error = stats.get('error')
            last_date = stats.get('last_item_date')

            # Format last item date
            if last_date:
                if isinstance(last_date, datetime):
                    last_date_str = last_date.strftime("%Y-%m-%d %H:%M")
                else:
                    last_date_str = str(last_date)
            else:
                last_date_str = "Unknown"

            if error:
                status = f"ERROR: {error}"
            elif total == 0 and not last_date:
                status = "⚠️ No items"
            elif total == 0:
                status = "No new items (7d)"
            elif matched == 0:
                status = "No AI matches"
            else:
                status = "✓ Active"

            lines.append(f"| {name} | {total} | {matched} | {last_date_str} | {status} |")

        # Find feeds with issues
        zero_feeds = [name for name, s in feeds.items() if s['total_7days'] == 0 and not s.get('error')]
        error_feeds = [name for name, s in feeds.items() if s.get('error')]

        if zero_feeds:
            lines.append(f"\n**⚠️ Feeds with no items:** {', '.join(zero_feeds)}\n")
        if error_feeds:
            lines.append(f"\n**❌ Feeds with errors:** {', '.join(error_feeds)}\n")

    write_section("News Feeds", news_feeds)
    write_section("Podcast Feeds", podcast_feeds)

    with open(stats_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote feed statistics to {stats_path}")


# ----------------- DEBUG FILES -----------------

def write_news_debug_file(news_items, timestamp_str):
    """
    Write debug file listing all news items seen.
    """
    if not news_items:
        return

    debug_path = os.path.join(OUTPUT_DIR, f"news_last7days_{timestamp_str}.md")
    lines = []
    lines.append("# News articles seen in the last 7 days\n")
    lines.append(
        "_This file lists **all** news articles fetched from your feeds in the last 7 days, "
        "before model-level filtering. All items are sent to the model for AI-relevance assessment._\n"
    )
    lines.append(f"\n**Total items:** {len(news_items)}\n")

    # Group by source for easier review
    by_source = {}
    for item in news_items:
        source = item['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(item)

    for source in sorted(by_source.keys()):
        items = by_source[source]
        lines.append(f"\n## {source} ({len(items)} items)\n")

        for i, article in enumerate(items, start=1):
            lines.append(f"### {i}. {article['title']}")
            lines.append(f"- **Date:** {article['date']}")
            lines.append(f"- **URL:** {article['link']}")

            # Check if it contains AI keywords (informational only - all items go to model anyway)
            combined_text = f"{article['title']}\n{article['summary']}"
            has_ai_keywords = is_ai_related_text(combined_text)
            lines.append(f"- **Contains AI keywords:** {'yes' if has_ai_keywords else 'no'}")

            if article["summary"]:
                short_summary = article["summary"].replace("\n", " ")
                if len(short_summary) > 400:
                    short_summary = short_summary[:400] + "..."
                lines.append(f"- **Summary excerpt:** {short_summary}")
            lines.append("")

    with open(debug_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote news debug file with {len(news_items)} articles")


def write_podcast_debug_file(podcast_debug, timestamp_str):
    """
    Write debug file listing all podcast episodes seen.
    """
    if not podcast_debug:
        return

    debug_path = os.path.join(OUTPUT_DIR, f"podcasts_last7days_{timestamp_str}.md")
    lines = []
    lines.append("# Podcast episodes seen in the last 7 days\n")
    lines.append(
        "_This file lists **all** podcast episodes fetched from your feeds in the last 7 days, "
        "before model-level curation. It is for debugging and manual review._\n"
    )

    for i, ep in enumerate(podcast_debug, start=1):
        lines.append(f"## P{i}. {ep['source']} – {ep['title']}")
        lines.append(f"- **Date:** {ep['date']}")
        lines.append(f"- **URL:** {ep['link']}")
        lines.append(f"- **AI keyword match:** {'yes' if ep['ai_keyword_match'] else 'no'}")
        if ep["summary"]:
            short_summary = ep["summary"].replace("\n", " ")
            if len(short_summary) > 400:
                short_summary = short_summary[:400] + "..."
            lines.append(f"- **Summary excerpt:** {short_summary}")
        lines.append("")

    with open(debug_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote podcast debug file with {len(podcast_debug)} episodes")


# ----------------- ARCHIVE INDEX -----------------

def generate_archive_index():
    """
    Generate an index of all archived AI news markdown files.
    Excludes the latest file since it's already shown as ai_news_latest.md.
    """
    import json
    import glob

    # Find all timestamped ai_news files
    pattern = os.path.join(OUTPUT_DIR, "ai_news_[0-9]*-[0-9]*.md")
    all_files = glob.glob(pattern)

    if not all_files:
        # No archives yet
        index_path = os.path.join(OUTPUT_DIR, "archive_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"archives": []}, f, indent=2)
        return

    # Sort by filename (which sorts by timestamp due to YYYYMMDD-HHMM format)
    all_files.sort(reverse=True)  # Newest first

    # Exclude the newest file (it's the same as ai_news_latest.md)
    archive_files = all_files[1:] if len(all_files) > 1 else []

    archives = []
    for filepath in archive_files:
        filename = os.path.basename(filepath)

        # Extract timestamp from filename: ai_news_20251222-2008.md
        try:
            timestamp_part = filename.replace("ai_news_", "").replace(".md", "")
            # Parse YYYYMMDD-HHMM format
            date_str, time_str = timestamp_part.split("-")
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            hour = time_str[:2]
            minute = time_str[2:4]

            # Create ISO datetime string
            iso_date = f"{year}-{month}-{day}T{hour}:{minute}"
            # Create display date (DD/MM/YYYY HH:MM)
            display_date = f"{day}/{month}/{year} {hour}:{minute}"

            archives.append({
                "filename": filename,
                "timestamp": timestamp_part,
                "date": iso_date,
                "display_date": display_date
            })
        except Exception as e:
            print(f"Warning: Could not parse timestamp from {filename}: {e}")
            continue

    # Write the index
    index_path = os.path.join(OUTPUT_DIR, "archive_index.json")
    index_data = {
        "archives": archives,
        "generated": datetime.now().isoformat(),
        "latest_file": os.path.basename(all_files[0]) if all_files else None
    }

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    print(f"Generated archive index with {len(archives)} archived files")


# ----------------- MAIN -----------------

def main():
    news_items, podcast_items, podcast_debug, feed_stats = collect_items_last_week()

    # Print feed statistics
    print_feed_statistics(feed_stats)

    if not news_items and not podcast_items:
        print("No items from the last 7 days.")
        notify_mac("No items from the last 7 days in RSS/podcast feeds.")
        return

    total_cost = 0.0
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Process news
    print(f"\nProcessing {len(news_items)} news items with model...")
    news_markdown, news_usage = call_model_for_news(news_items)
    if news_usage:
        total_cost += compute_cost(MODEL_NAME, news_usage)
        total_usage["prompt_tokens"] += news_usage.prompt_tokens or 0
        total_usage["completion_tokens"] += news_usage.completion_tokens or 0
        total_usage["total_tokens"] += news_usage.total_tokens or 0

    # Process podcasts (separate call to avoid them being drowned out)
    print("Processing podcast episodes with model...")
    podcast_markdown, podcast_usage = call_model_for_podcasts(podcast_items)
    if podcast_usage:
        total_cost += compute_cost(MODEL_NAME, podcast_usage)
        total_usage["prompt_tokens"] += podcast_usage.prompt_tokens or 0
        total_usage["completion_tokens"] += podcast_usage.completion_tokens or 0
        total_usage["total_tokens"] += podcast_usage.total_tokens or 0

    # Combine outputs
    combined_markdown = f"{news_markdown}\n\n{podcast_markdown}"

    # Log usage
    class UsageWrapper:
        def __init__(self, d):
            self.prompt_tokens = d["prompt_tokens"]
            self.completion_tokens = d["completion_tokens"]
            self.total_tokens = d["total_tokens"]
    
    log_usage(MODEL_NAME, UsageWrapper(total_usage), total_cost)

    # Save files
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_path = os.path.join(OUTPUT_DIR, f"ai_news_{timestamp}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(combined_markdown)
        f.write(
            f"\n\n---\n"
            f"_Generated: {datetime.now().isoformat(timespec='minutes')}_\n"
            f"_Tokens: {total_usage['prompt_tokens']} prompt + {total_usage['completion_tokens']} completion_\n"
            f"_Cost: ~${total_cost:.4f}_\n"
        )

    # Also update "latest" file
    latest_path = os.path.join(OUTPUT_DIR, "ai_news_latest.md")
    import shutil
    shutil.copyfile(output_path, latest_path)

    # Write debug and statistics files
    write_news_debug_file(news_items, timestamp)
    write_podcast_debug_file(podcast_debug, timestamp)
    write_feed_statistics_file(feed_stats, timestamp)

    # Generate archive index for web display
    generate_archive_index()

    print(f"\nUsage: prompt={total_usage['prompt_tokens']}, "
          f"completion={total_usage['completion_tokens']}, "
          f"cost=${total_cost:.4f}")
    print(f"Wrote briefing to {output_path}")
    notify_mac(f"AI briefing updated (cost ${total_cost:.4f})")


if __name__ == "__main__":
    main()
