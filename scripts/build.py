#!/usr/bin/env python3
import json, os, urllib.request, urllib.error, time
from datetime import datetime, timezone

token = os.environ.get("GH_TOKEN", "")
headers = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "pour-skills-registry",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

def gh_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After", (2 ** attempt) * 10))
                print(f"  Rate limited ({e.code}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

def build_date_windows():
    """Generate quarterly date windows from 2019 up to today, with an open-ended final window.

    Closed windows are fixed in the past and will never exceed the 1000-result cap.
    Only the last (open-ended) window grows over time; when it approaches the cap a
    new quarter will automatically split off on the next run.
    """
    from datetime import date
    quarter_end = {1: (3, 31), 4: (6, 30), 7: (9, 30), 10: (12, 31)}
    today = datetime.now(timezone.utc).date()
    cur_q_month = max(m for m in quarter_end if m <= today.month)
    cur_q_start = date(today.year, cur_q_month, 1)

    windows = []
    d = date(2019, 1, 1)
    while d < cur_q_start:
        end_month, end_day = quarter_end[d.month]
        windows.append(f"{d}..{date(d.year, end_month, end_day)}")
        next_month = d.month + 3
        d = date(d.year + 1, 1, 1) if next_month > 12 else date(d.year, next_month, 1)

    windows.append(f"{cur_q_start}..*")
    return windows

# Broad queries (no path filter) are expanded into date windows.
# Path-specific queries are narrow enough to stay under the 1000-result cap.
BROAD_QUERIES = [
    "filename:SKILL.md",
]

PATH_QUERIES = [
    "filename:SKILL.md path:.claude",
    "filename:SKILL.md path:.agents",
    "filename:SKILL.md path:.windsurf",
    "filename:SKILL.md path:.codeium",
    "filename:SKILL.md path:.augment",
    "filename:SKILL.md path:.continue",
    "filename:SKILL.md path:.cursor",
    "filename:SKILL.md path:.roo",
    "filename:SKILL.md path:.goose",
    "filename:SKILL.md path:.devin",
    "filename:SKILL.md path:.gemini",
    "filename:SKILL.md path:.codex",
    "filename:SKILL.md path:.aider-desk",
    "filename:SKILL.md path:.bob",
    "filename:SKILL.md path:.codebuddy",
    "filename:SKILL.md path:.codemaker",
    "filename:SKILL.md path:.codestudio",
    "filename:SKILL.md path:.commandcode",
    "filename:SKILL.md path:.copilot",
    "filename:SKILL.md path:.cortex",
    "filename:SKILL.md path:.crush",
    "filename:SKILL.md path:.deepagents",
    "filename:SKILL.md path:.factory",
    "filename:SKILL.md path:.firebender",
    "filename:SKILL.md path:.forge",
    "filename:SKILL.md path:.iflow",
    "filename:SKILL.md path:.junie",
    "filename:SKILL.md path:.kilocode",
    "filename:SKILL.md path:.kiro",
    "filename:SKILL.md path:.kode",
    "filename:SKILL.md path:.mcpjam",
    "filename:SKILL.md path:.mux",
    "filename:SKILL.md path:.neovate",
    "filename:SKILL.md path:.openclaw",
    "filename:SKILL.md path:.openhands",
    "filename:SKILL.md path:.pi",
    "filename:SKILL.md path:.pochi",
    "filename:SKILL.md path:.qoder",
    "filename:SKILL.md path:.qwen",
    "filename:SKILL.md path:.rovodev",
    "filename:SKILL.md path:.snowflake",
    "filename:SKILL.md path:.tabnine",
    "filename:SKILL.md path:.trae",
    "filename:SKILL.md path:.vibe",
    "filename:SKILL.md path:.zencoder",
    "filename:SKILL.md path:.adal",
    "filename:SKILL.md path:.codeartsdoer",
    "filename:SKILL.md path:skills",           # openclaw project path
    "filename:SKILL.md path:.github",          # github-native layouts
    "filename:SKILL.md path:prompts",          # vscode copilot extension layout
    "filename:SKILL.md path:.amazonq",
    "filename:SKILL.md path:.cody",
    "filename:SKILL.md path:.sourcegraph",
    "filename:SKILL.md path:.tabby",
]

repos = {}

# Expand broad queries into date-windowed variants, then append path-specific queries.
def build_query_list():
    queries = []
    for base in BROAD_QUERIES:
        for window in build_date_windows():
            queries.append(f"{base} created:{window}")
    queries.extend(PATH_QUERIES)
    return queries

def process_items(items):
    for item in items:
        r = item.get("repository", {})
        full_name = r.get("full_name")
        if not full_name or full_name in repos:
            continue
        repos[full_name] = {
            "repo": full_name,
            "description": r.get("description") or "",
            "stars": r.get("stargazers_count", 0),
            "url": r.get("html_url", ""),
        }

for query in build_query_list():
    print(f"Searching: {query}")
    q = query.replace(" ", "+")
    for page in range(1, 11):
        url = f"https://api.github.com/search/code?q={q}&per_page=100&page={page}"
        try:
            data = gh_get(url)
        except Exception as e:
            print(f"  Page {page} failed: {e}")
            break

        items = data.get("items", [])
        if not items:
            break

        process_items(items)

        if len(items) < 100:
            break

        time.sleep(2)

    time.sleep(3)

result = sorted(repos.values(), key=lambda r: r["stars"], reverse=True)

registry = {
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "count": len(result),
    "repos": result,
}

with open("index.json", "w") as f:
    json.dump(registry, f, indent=2)

print(f"Registry built with {len(result)} repos")
