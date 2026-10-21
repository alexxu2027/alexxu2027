"""Redraw the profile card (card-dark.svg, card-light.svg) with fresh numbers.

Runs daily from .github/workflows/update.yml. Locally:
    GITHUB_TOKEN=$(gh auth token) python scripts/update.py
"""

import json
import os
import urllib.request
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

USER = "alexxu2027"
BIRTHDATE = date(2005, 4, 16)

# Static lines on the card. Edit freely; order is kept.
ABOUT = [
    ("Name", "Alex Xu"),
    ("Location", "New York, NY"),
    ("School", "NYU Stern"),
    ("Major", "Finance & AI, Computing, and Data Science"),
    ("Interests", "music, graphic design, lacrosse,"),
    ("", "chess, poker, Rocket League"),
]

THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "fg": "#c9d1d9", "key": "#ffa657", "dim": "#8b949e", "title": "#58a6ff"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "fg": "#24292f", "key": "#bc4c00", "dim": "#57606a", "title": "#0969da"},
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { totalCommitContributions }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10) { edges { size node { name } } }
      }
    }
  }
}
"""


def fetch_stats():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        user = json.load(resp)["data"]["user"]

    repos = user["repositories"]
    lang_bytes = {}
    for repo in repos["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]
    total = sum(lang_bytes.values()) or 1
    top = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:3]

    return {
        "repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "followers": user["followers"]["totalCount"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "languages": " · ".join(f"{name} {round(100 * size / total)}%" for name, size in top),
    }


def uptime(today):
    days = (today - BIRTHDATE).days
    years = today.year - BIRTHDATE.year
    months = today.month - BIRTHDATE.month
    d = today.day - BIRTHDATE.day
    if d < 0:
        months -= 1
        prev_month_end = date(today.year, today.month, 1).toordinal() - 1
        d += date.fromordinal(prev_month_end).day
    if months < 0:
        years -= 1
        months += 12
    return f"{days:,} days ({years}y {months}m {d}d)"


def render(theme, lines, updated):
    t = THEMES[theme]
    line_h, top, left, key_w = 24, 70, 28, 150
    height = top + sum(line_h // 2 if item is None else line_h for item in lines) + 28
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="{height}" viewBox="0 0 620 {height}">',
        "<style>text{font-family:ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace;font-size:15px}</style>",
        f'<rect x="0.5" y="0.5" width="619" height="{height - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text x="{left}" y="40" fill="{t["title"]}" font-weight="bold">{USER}@github</text>',
    ]
    y = top
    for item in lines:
        if item is None:
            out.append(f'<line x1="{left}" x2="592" y1="{y - 5}" y2="{y - 5}" stroke="{t["border"]}"/>')
            y += line_h // 2
            continue
        key, value = item
        out.append(f'<text x="{left}" y="{y}" fill="{t["key"]}">{escape(key)}</text>')
        out.append(f'<text x="{left + key_w}" y="{y}" fill="{t["fg"]}">{escape(str(value))}</text>')
        y += line_h
    out.append(f'<text x="{left}" y="{height - 18}" fill="{t["dim"]}" font-size="12">updated {updated} by GitHub Actions</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    now = datetime.now(timezone.utc)
    stats = fetch_stats()
    lines = [
        *ABOUT,
        ("Uptime", uptime(now.date())),
        None,
        ("Languages", stats["languages"]),
        ("Public repos", stats["repos"]),
        ("Commits", f'{stats["commits"]:,} in the past year'),
    ]
    root = Path(__file__).resolve().parent.parent
    for theme in THEMES:
        (root / f"card-{theme}.svg").write_text(render(theme, lines, now.strftime("%Y-%m-%d")), encoding="utf-8")


if __name__ == "__main__":
    main()
