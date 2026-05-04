#!/usr/bin/env python3
  import json, os, urllib.request
  from datetime import datetime, timezone

  token = os.environ.get("GH_TOKEN", "")
  headers = {
      "Accept": "application/vnd.github.v3+json",
      "User-Agent": "pour-skills-registry",
  }
  if token:

  def gh_get(url):
      req = urllib.request.Request(url, headers=headers)
      with urllib.request.urlopen(req) as resp:
          return json.loads(resp.read())

  seen = set()
  repos = []

  for page in range(1, 4):  # up to 300 results
      url = f"https://api.github.com/search/code?q=filename:SKILL.md&per_page=100&page={page}"
      try:
          data = gh_get(url)
      except Exception as e:
          print(f"Page {page} failed: {e}")
          break

      items = data.get("items", [])
      if not items:
          break

      for item in items:
          r = item.get("repository", {})
          full_name = r.get("full_name")
          if not full_name or full_name in seen:
              continue
          seen.add(full_name)
          repos.append({
              "repo": full_name,
              "description": r.get("description") or "",
              "stars": r.get("stargazers_count", 0),
              "url": r.get("html_url", ""),
          })

      if len(items) < 100:
          break

  repos.sort(key=lambda r: r["stars"], reverse=True)

  registry = {
      "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
      "count": len(repos),
      "repos": repos,
  }

  with open("index.json", "w") as f:
      json.dump(registry, f, indent=2)

  print(f"Registry built with {len(repos)} repos")
