#!/usr/bin/env python3
"""Generate the profile README visuals from live GitHub data.

Stdlib only, so the workflow needs no `pip install`. Every card is written
twice (dark and light) into assets/generated/, and the workflow commits
them.

    GITHUB_TOKEN=... python3 scripts/generate.py
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import shutil
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("PROFILE_LOGIN", "Inheert")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "generated"

# Languages that are build plumbing rather than something written by hand.
IGNORED_LANGUAGES = {"Makefile", "CMake", "Batchfile", "Dockerfile", "Shell", "HTML", "CSS"}

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "dark": {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d", "grid": "#21262d",
        "text": "#e6edf3", "muted": "#8b949e", "faint": "#484f58",
        "accent": "#39d0d8", "accent2": "#a371f7", "accent3": "#f0b429", "ok": "#3fb950",
        # Contribution levels 0..4, as on the GitHub calendar.
        "levels": ["#1c2128", "#13646c", "#1a9aa4", "#2fd0da", "#8af7fc"],
    },
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de", "grid": "#eaeef2",
        "text": "#1f2328", "muted": "#656d76", "faint": "#afb8c1",
        "accent": "#0a7ea4", "accent2": "#8250df", "accent3": "#bf8700", "ok": "#1a7f37",
        "levels": ["#e4e9ee", "#a5e3ea", "#4cc2cf", "#1494a4", "#0b5f6d"],
    },
}

ROLES = [
    "containers: Docker, Compose",
    "orchestration: Kubernetes, K3s",
    "GitOps & CI/CD: Argo CD, Actions",
    "infra: Nginx, Caddy, Linux, VPS",
    "observability: ELK stack",
    "backend: Go, Python, PostgreSQL",
    "open to internships",
]

# ASCII only: box-drawing glyphs fall back to fonts with other widths.
ASCII_LOGO = [
    r"  ______________ ",
    r" /_  __/ ____/  ",
    r"  / / / /       ",
    r" / / / /___     ",
    r"/_/  \____/     ",
    r"                ",
    r"   inheert.c    ",
]


# --------------------------------------------------------------------- data

def _request(url: str, body: dict | None = None):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token and shutil.which("gh"):
        # Local runs: let an authenticated gh CLI make the call.
        path = url.removeprefix("https://api.github.com/")
        cmd = ["gh", "api", path] + (["--input", "-"] if body is not None else [])
        out = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                             capture_output=True, text=True, check=True)
        return json.loads(out.stdout)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{LOGIN}-profile"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


QUERY = """
query($login: String!) {
  user(login: $login) {
    name createdAt
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions totalPullRequestContributions
      totalIssueContributions totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name pushedAt stargazerCount isFork
        languages(first: 10) { edges { size node { name color } } }
      }
    }
  }
}
"""


def fetch() -> dict:
    res = _request("https://api.github.com/graphql", {"query": QUERY, "variables": {"login": LOGIN}})
    if "errors" in res:
        raise SystemExit(f"GraphQL error: {res['errors']}")
    user = res["data"]["user"]
    return user


def summarize(user: dict) -> dict:
    cc = user["contributionsCollection"]
    weeks = [w["contributionDays"] for w in cc["contributionCalendar"]["weeks"]]
    days = [d for w in weeks for d in w]

    langs: Counter = Counter()
    colors: dict[str, str] = {}
    repos = [r for r in user["repositories"]["nodes"] if not r["isFork"]]
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in IGNORED_LANGUAGES:
                continue
            langs[name] += edge["size"]
            colors[name] = edge["node"]["color"] or "#888888"

    # Streaks: today may still be at 0, which shouldn't break the current one.
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        best = max(best, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            current += 1
        elif i:
            break

    best_day = max(days, key=lambda d: d["contributionCount"])
    created = dt.date.fromisoformat(user["createdAt"][:10])
    today = dt.date.today()
    months = (today.year - created.year) * 12 + today.month - created.month
    # The profile repo itself is pushed every night by the workflow.
    last = next((r for r in repos if r["name"] != LOGIN), None)

    return {
        "name": user["name"] or LOGIN,
        "weeks": weeks,
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "best_streak": best,
        "current_streak": current,
        "best_day": best_day,
        "active_days": sum(1 for d in days if d["contributionCount"]),
        "langs": langs.most_common(),
        "lang_colors": colors,
        "repos": user["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": user["followers"]["totalCount"],
        "uptime": f"{months // 12} years, {months % 12} months",
        "last_repo": last["name"] if last else "-",
        "last_push": last["pushedAt"][:10] if last else "-",
    }


# ------------------------------------------------------------------ helpers

def luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mix(a: str, b: str, amount: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * amount) for x, y in zip(ca, cb))


def svg(width: int, height: int, body: str, title: str, style: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title><style>{style}</style>{body}</svg>\n"
    )


def panel(t: dict, width: int, height: int) -> str:
    return (f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
            f'fill="{t["panel"]}" stroke="{t["border"]}"/>')


# ------------------------------------------------------------------- header

def header(s: dict, t: dict) -> str:
    w, h = 900, 230
    fs, cw = 20, 20 * 0.62  # monospace advance is ~0.6em on every common font
    slot = 3.6
    total = slot * len(ROLES)
    tx, ty = 56, 168

    roles = []
    for i, role in enumerate(ROLES):
        a = i * slot
        # Discrete keyframes: one per typed character, then erased in one go.
        times, widths = [0.0], [0.0]
        for c in range(1, len(role) + 1):
            times.append(a + 0.15 + c * 0.055)
            widths.append(c * cw)
        times.append(a + slot - 0.35)
        widths.append(0.0)
        kt = ";".join(f"{x / total:.4f}" for x in times)
        vals = ";".join(f"{x:.1f}" for x in widths)
        roles.append(
            f'<clipPath id="r{i}"><rect x="{tx}" y="{ty - 22}" height="30" width="0">'
            f'<animate attributeName="width" values="{vals}" keyTimes="{kt}" calcMode="discrete" '
            f'dur="{total}s" repeatCount="indefinite"/></rect></clipPath>'
            f'<text x="{tx}" y="{ty}" clip-path="url(#r{i})" class="role">{escape(role)}</text>'
            f'<rect y="{ty - 18}" width="10" height="22" fill="{t["accent"]}" opacity="0">'
            f'<animate attributeName="x" values="{";".join(f"{tx + x + 2:.1f}" for x in widths)}" '
            f'keyTimes="{kt}" calcMode="discrete" dur="{total}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;0;0" '
            f'keyTimes="0;{a / total:.4f};{(a + slot - 0.35) / total:.4f};1" calcMode="discrete" '
            f'dur="{total}s" repeatCount="indefinite"/></rect>'
        )

    # A small cluster on the right: a control plane, six workers, packets on the links.
    cx, cy = 770, 115
    workers = [(cx + 98 * math.cos(math.radians(a)), cy + 78 * math.sin(math.radians(a)))
               for a in range(-90, 270, 60)]
    links, nodes = [], []
    ring = " ".join(f"{x:.1f},{y:.1f}" for x, y in workers)
    links.append(f'<polygon points="{ring}" fill="none" stroke="{t["faint"]}" stroke-opacity=".5" stroke-dasharray="2 5"/>')
    for i, (x, y) in enumerate(workers):
        color = (t["accent"], t["accent2"], t["accent3"])[i % 3]
        links.append(
            f'<path id="k{i}" d="M {cx} {cy} L {x:.1f} {y:.1f}" stroke="{t["faint"]}" stroke-width="1.5" class="flow"/>'
            f'<circle r="3.5" fill="{color}" filter="url(#glow)">'
            f'<animateMotion dur="{1.6 + i * 0.25:.2f}s" begin="-{i * 0.4:.1f}s" repeatCount="indefinite" '
            f'keyPoints="{"0;1" if i % 2 else "1;0"}" keyTimes="0;1" calcMode="linear"><mpath href="#k{i}"/></animateMotion></circle>'
        )
        pods = "".join(
            f'<rect x="{x - 10 + j * 7:.1f}" y="{y - 3:.1f}" width="5" height="6" rx="1" fill="{color}">'
            f'<animate attributeName="opacity" values=".25;1;.25" dur="{2 + (i + j) % 3 * 0.7:.1f}s" '
            f'begin="{(i * 3 + j) * 0.21:.2f}s" repeatCount="indefinite"/></rect>'
            for j in range(3)
        )
        nodes.append(f'<rect x="{x - 15:.1f}" y="{y - 10:.1f}" width="30" height="20" rx="5" '
                     f'fill="{t["panel"]}" stroke="{color}" stroke-opacity=".8"/>{pods}')
    hexagon = " ".join(f"{cx + 24 * math.cos(math.radians(a)):.1f},{cy + 24 * math.sin(math.radians(a)):.1f}"
                       for a in range(30, 390, 60))
    cluster = (
        "".join(links) + "".join(nodes)
        + f'<polygon points="{hexagon}" fill="url(#core)"><animate attributeName="opacity" values=".85;1;.85" dur="3s" repeatCount="indefinite"/></polygon>'
        f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" class="core">k8s</text>'
    )

    sparks = "".join(
        f'<circle cx="{x}" cy="{y}" r="1.6" fill="{t["accent"]}">'
        f'<animate attributeName="opacity" values="0;.9;0" dur="{d}s" begin="{b}s" repeatCount="indefinite"/></circle>'
        for x, y, d, b in [(420, 40, 3.1, 0), (520, 190, 4.3, 1), (610, 60, 2.7, .4), (470, 120, 3.8, 2),
                           (660, 200, 3.3, 1.5), (380, 200, 4.9, .8), (560, 30, 3.6, 2.4)]
    )

    style = f"""
      .name {{ font: 700 44px {SANS}; fill: {t["text"]}; letter-spacing: -1px; }}
      .aka  {{ font: 400 16px {MONO}; fill: {t["muted"]}; }}
      .role {{ font: 500 {fs}px {MONO}; fill: {t["accent"]}; }}
      .pr   {{ font: 700 {fs}px {MONO}; fill: {t["accent2"]}; }}
      .core {{ font: 800 13px {MONO}; fill: {t["bg"]}; }}
      .in   {{ animation: rise .9s cubic-bezier(.2,.8,.2,1) both; }}
      .d1 {{ animation-delay: .15s }} .d2 {{ animation-delay: .3s }}
      @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px) }} to {{ opacity: 1; transform: none }} }}
      .scan {{ animation: scan 7s linear infinite; }}
      .flow {{ stroke-dasharray: 3 5; animation: dash 1s linear infinite; }}
      @keyframes dash {{ to {{ stroke-dashoffset: -16 }} }}
      @keyframes scan {{ from {{ transform: translateX(-200px) }} to {{ transform: translateX(1100px) }} }}
    """
    body = f"""
    <defs>
      <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
        <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{t["grid"]}" stroke-width="1"/>
      </pattern>
      <linearGradient id="fade" x1="0" x2="1">
        <stop offset="0" stop-color="{t["panel"]}" stop-opacity="1"/>
        <stop offset=".45" stop-color="{t["panel"]}" stop-opacity=".2"/>
        <stop offset="1" stop-color="{t["panel"]}" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="beam" x1="0" x2="1">
        <stop offset="0" stop-color="{t["accent"]}" stop-opacity="0"/>
        <stop offset=".5" stop-color="{t["accent"]}" stop-opacity=".10"/>
        <stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/>
      </linearGradient>
      <radialGradient id="core"><stop offset="0" stop-color="{t["accent3"]}"/><stop offset="1" stop-color="{t["accent2"]}"/></radialGradient>
      <filter id="glow" x="-200%" y="-200%" width="500%" height="500%">
        <feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <clipPath id="card"><rect width="{w}" height="{h}" rx="12"/></clipPath>
    </defs>
    {panel(t, w, h)}
    <g clip-path="url(#card)">
      <rect width="{w}" height="{h}" fill="url(#grid)"/>
      <rect width="{w}" height="{h}" fill="url(#fade)"/>
      <rect class="scan" width="200" height="{h}" fill="url(#beam)"/>
      {sparks}
    </g>
    <text x="54" y="86" class="name in">{escape(s["name"])}</text>
    <text x="56" y="116" class="aka in d1">aka @{LOGIN} · DevOps &amp; infrastructure developer</text>
    <g class="in d2"><text x="{tx - 24}" y="{ty}" class="pr">❯</text>{"".join(roles)}</g>
    {cluster}
    """
    return svg(w, h, body, f"{s['name']} — {', '.join(ROLES)}", style)


# ----------------------------------------------------------------- terminal

def terminal(s: dict, t: dict) -> str:
    w, h = 900, 430
    top = [lang for lang, _ in s["langs"][:4]]
    info = [
        ("title", f"{LOGIN.lower()}@github"),
        ("rule", "─" * 26),
        ("Name", s["name"]),
        ("Role", "DevOps & infrastructure developer"),
        ("School", "42 Mulhouse · Common Core done"),
        ("Uptime", s["uptime"]),
        ("Repos", f"{s['repos']} public · {s['stars']} ★ · {s['followers']} followers"),
        ("Contribs", f"{s['total']} in the last year ({s['active_days']} active days)"),
        ("Streak", f"current {s['current_streak']}d · best {s['best_streak']}d"),
        ("Langs", " · ".join(top)),
        ("Stack", "Docker · K8s · Argo CD · Nginx · Go · Python"),
        ("Status", "open to internships"),
        ("Last push", f"{s['last_repo']} ({s['last_push']})"),
    ]

    cmd = "neofetch --profile"
    cw = 14 * 0.62
    type_end = 0.6 + len(cmd) * 0.06
    lines = []
    for i, row in enumerate(ASCII_LOGO):
        lines.append(f'<text x="40" y="{108 + i * 22}" class="logo l" style="animation-delay:{type_end + 0.05 * i:.2f}s">{escape(row)}</text>')

    x0, y0 = 300, 92
    for i, (key, val) in enumerate(info):
        delay = type_end + 0.25 + i * 0.12
        y = y0 + i * 22
        if key == "title":
            content = f'<tspan class="k">{escape(val.split("@")[0])}</tspan><tspan class="v">@</tspan><tspan class="k">{escape(val.split("@")[1])}</tspan>'
        elif key == "rule":
            content = f'<tspan class="m">{val}</tspan>'
        else:
            content = f'<tspan class="k">{escape(key)}</tspan><tspan class="v">: {escape(val)}</tspan>'
        lines.append(f'<text x="{x0}" y="{y}" class="l" style="animation-delay:{delay:.2f}s">{content}</text>')

    swatches = [t["levels"][0], "#f85149", t["ok"], t["accent3"], "#58a6ff", t["accent2"], t["accent"], t["text"]]
    sw_delay = type_end + 0.3 + len(info) * 0.12
    blocks = "".join(f'<rect x="{x0 + i * 26}" y="{y0 + len(info) * 22 - 6}" width="24" height="14" rx="2" fill="{c}"/>'
                     for i, c in enumerate(swatches))
    lines.append(f'<g class="l" style="animation-delay:{sw_delay:.2f}s">{blocks}</g>')

    end_y = h - 26
    prompt_delay = sw_delay + 0.3

    style = f"""
      text {{ font: 14px {MONO}; fill: {t["text"]}; white-space: pre; }}
      .logo {{ fill: {t["accent"]}; font-weight: 700; font-size: 18px; }}
      .k {{ fill: {t["accent"]}; font-weight: 700; }}
      .v {{ fill: {t["text"]}; }}
      .m {{ fill: {t["faint"]}; }}
      .p {{ fill: {t["ok"]}; font-weight: 700; }}
      .bar {{ font: 12px {SANS}; fill: {t["muted"]}; }}
      .l {{ opacity: 0; animation: show .35s ease-out both; }}
      @keyframes show {{ from {{ opacity: 0; transform: translateX(-6px) }} to {{ opacity: 1; transform: none }} }}
      .caret {{ animation: blink 1s steps(1) infinite; }}
      @keyframes blink {{ 50% {{ opacity: 0 }} }}
    """
    body = f"""
    {panel(t, w, h)}
    <path d="M1 40 H{w - 1}" stroke="{t["border"]}"/>
    <circle cx="24" cy="20" r="6" fill="#ff5f57"/><circle cx="44" cy="20" r="6" fill="#febc2e"/><circle cx="64" cy="20" r="6" fill="#28c840"/>
    <text x="{w / 2}" y="25" text-anchor="middle" class="bar">{LOGIN.lower()}@github: ~</text>
    <text x="24" y="66"><tspan class="p">➜ </tspan><tspan class="k">~ </tspan></text>
    <clipPath id="type"><rect x="64" y="50" height="22" width="0">
      <animate attributeName="width" from="0" to="{len(cmd) * cw + 2:.0f}" begin=".6s" dur="{len(cmd) * 0.06:.2f}s"
               calcMode="discrete" fill="freeze"
               values="{";".join(f"{c * cw:.1f}" for c in range(len(cmd) + 1))}"/>
    </rect></clipPath>
    <text x="64" y="66" clip-path="url(#type)">{cmd}</text>
    {"".join(lines)}
    <g class="l" style="animation-delay:{prompt_delay:.2f}s">
      <text x="24" y="{end_y}"><tspan class="p">➜ </tspan><tspan class="k">~ </tspan></text>
      <rect class="caret" x="64" y="{end_y - 14}" width="9" height="18" fill="{t["text"]}"/>
    </g>
    """
    return svg(w, h, body, f"neofetch-style summary of {LOGIN}'s GitHub profile", style)


# ---------------------------------------------------------------- languages

def languages(s: dict, t: dict) -> str:
    w, h = 900, 112
    langs = s["langs"][:8]
    total = sum(v for _, v in langs) or 1
    bar_w = w - 48
    x = 24.0
    segs, legend = [], []
    for i, (name, size) in enumerate(langs):
        pct = size / total
        seg = max(bar_w * pct, 3)
        color = s["lang_colors"].get(name, "#888")
        if luminance(color) < 0.12 and t is THEMES["dark"]:
            color = mix(color, "#ffffff", 0.45)  # Lua's navy vanishes on a dark panel
        segs.append(f'<rect x="{x:.1f}" y="24" width="{seg:.1f}" height="12" fill="{color}" class="seg" '
                    f'style="animation-delay:{0.1 + i * 0.08:.2f}s"><title>{escape(name)} {pct:.1%}</title></rect>')
        x += seg
        col, row = i % 4, i // 4
        lx, ly = 24 + col * 216, 66 + row * 26
        legend.append(f'<g class="lg" style="animation-delay:{0.5 + i * 0.07:.2f}s">'
                      f'<circle cx="{lx + 6}" cy="{ly - 4}" r="5" fill="{color}"/>'
                      f'<text x="{lx + 18}" y="{ly}"><tspan class="ln">{escape(name)}</tspan>'
                      f'<tspan class="pc" dx="8">{pct:.1%}</tspan></text></g>')
    style = f"""
      .h  {{ font: 700 16px {SANS}; fill: {t["text"]}; }}
      .sub {{ font: 12px {MONO}; fill: {t["muted"]}; }}
      .ln {{ font: 600 14px {SANS}; fill: {t["text"]}; }}
      .pc {{ font: 12px {MONO}; fill: {t["muted"]}; }}
      .seg {{ transform-box: fill-box; transform-origin: 0 50%; animation: grow .7s cubic-bezier(.2,.8,.2,1) both; }}
      @keyframes grow {{ from {{ transform: scaleX(0) }} to {{ transform: scaleX(1) }} }}
      .lg {{ animation: show .5s ease-out both; }}
      @keyframes show {{ from {{ opacity: 0 }} to {{ opacity: 1 }} }}
    """
    body = f"""
    {panel(t, w, h)}
    <clipPath id="bar"><rect x="24" y="24" width="{bar_w}" height="12" rx="6"/></clipPath>
    <rect x="24" y="24" width="{bar_w}" height="12" rx="6" fill="{t["grid"]}"/>
    <g clip-path="url(#bar)">{"".join(segs)}</g>
    {"".join(legend)}
    """
    return svg(w, h, body, "Most used languages: " + ", ".join(n for n, _ in langs), style)


# ----------------------------------------------------------------- sections
# Each README section is a "resource": an animated icon, its kind, a status column.

def icon_container(t: dict) -> str:
    """An isometric shipping container, bobbing on the water."""
    top = "32,10 56,22 32,34 8,22"
    left = "8,22 32,34 32,58 8,46"
    right = "32,34 56,22 56,46 32,58"
    ridges = "".join(f'<path d="M {x} {22 + (x - 8) / 2 + 3:.1f} V {46 + (x - 8) / 2 - 3:.1f}" stroke="{t["panel"]}" stroke-opacity=".5"/>'
                     for x in (13, 18, 23, 28))
    return (f'<g class="bob"><polygon points="{top}" fill="{t["accent"]}"/>'
            f'<polygon points="{left}" fill="{mix(t["accent"], t["bg"], .25)}"/>{ridges}'
            f'<polygon points="{right}" fill="{mix(t["accent"], t["bg"], .5)}"/></g>')


def icon_pipeline(t: dict) -> str:
    """Three stages that light up one after the other, then a check."""
    out = [f'<path d="M 8 34 H 56" stroke="{t["faint"]}" stroke-width="3"/>']
    for i, x in enumerate((8, 32, 56)):
        out.append(f'<circle cx="{x}" cy="34" r="8" fill="{t["panel"]}" stroke="{t["accent"]}" stroke-width="2.5"/>'
                   f'<circle cx="{x}" cy="34" r="5" fill="{t["accent"]}" opacity="0">'
                   f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{.1 + i * .2:.2f};{.15 + i * .2:.2f};.9;1" '
                   f'dur="3s" repeatCount="indefinite"/></circle>')
    out.append(f'<path d="M 50 34 l 4 4 l 8 -9" fill="none" stroke="{t["ok"]}" stroke-width="3" stroke-linecap="round" opacity="0">'
               f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.62;.66;.9;1" dur="3s" repeatCount="indefinite"/></path>')
    return "".join(out)


def icon_pods(t: dict) -> str:
    """A replica set: pods scheduled one by one inside a dashed boundary."""
    out = [f'<rect x="4" y="6" width="56" height="56" rx="10" fill="none" stroke="{t["faint"]}" stroke-dasharray="4 4" class="flow"/>']
    for i, (x, y) in enumerate([(12, 14), (34, 14), (12, 36), (34, 36)]):
        color = (t["accent"], t["accent2"], t["accent3"], t["ok"])[i]
        out.append(f'<rect x="{x}" y="{y}" width="18" height="18" rx="4" fill="{color}" class="pop" '
                   f'style="animation-delay:{i * .35:.2f}s"/>')
    return "".join(out)


def icon_layers(t: dict) -> str:
    """Three slabs falling into place, like image layers."""
    out = []
    for i, color in enumerate((t["accent3"], t["accent2"], t["accent"])):
        y = 40 - i * 13
        out.append(f'<g class="drop" style="animation-delay:{i * .3:.1f}s">'
                   f'<polygon points="32,{y} 58,{y + 10} 32,{y + 20} 6,{y + 10}" fill="{color}"/>'
                   f'<polygon points="6,{y + 10} 32,{y + 20} 32,{y + 24} 6,{y + 14}" fill="{mix(color, t["bg"], .35)}"/>'
                   f'<polygon points="32,{y + 20} 58,{y + 10} 58,{y + 14} 32,{y + 24}" fill="{mix(color, t["bg"], .55)}"/></g>')
    return "".join(out)


def icon_metrics(t: dict) -> str:
    """A live bar chart."""
    out = [f'<path d="M 6 58 H 60" stroke="{t["faint"]}" stroke-width="2"/>']
    for i, vals in enumerate(["30;14;24;30", "18;34;10;18", "38;22;30;38", "12;26;36;12"]):
        hs = [int(v) for v in vals.split(";")]
        ys = ";".join(str(56 - h) for h in hs)
        color = (t["accent"], t["accent2"], t["accent3"], t["ok"])[i]
        out.append(f'<rect x="{9 + i * 13}" y="{56 - hs[0]}" width="9" height="{hs[0]}" rx="2" fill="{color}">'
                   f'<animate attributeName="height" values="{vals}" dur="2.4s" repeatCount="indefinite"/>'
                   f'<animate attributeName="y" values="{ys}" dur="2.4s" repeatCount="indefinite"/></rect>')
    return "".join(out)


def icon_cron(t: dict) -> str:
    """A clock whose hand never stops."""
    ticks = "".join(
        f'<path d="M {32 + 20 * math.cos(math.radians(a)):.1f} {34 + 20 * math.sin(math.radians(a)):.1f} '
        f'L {32 + 24 * math.cos(math.radians(a)):.1f} {34 + 24 * math.sin(math.radians(a)):.1f}" stroke="{t["muted"]}" stroke-width="2"/>'
        for a in range(0, 360, 30)
    )
    return (f'<circle cx="32" cy="34" r="27" fill="none" stroke="{t["accent"]}" stroke-width="3"/>{ticks}'
            f'<path d="M 32 34 V 20" stroke="{t["accent2"]}" stroke-width="3" stroke-linecap="round">'
            f'<animateTransform attributeName="transform" type="rotate" from="0 32 34" to="360 32 34" dur="12s" repeatCount="indefinite"/></path>'
            f'<path d="M 32 34 V 12" stroke="{t["accent"]}" stroke-width="2" stroke-linecap="round">'
            f'<animateTransform attributeName="transform" type="rotate" from="0 32 34" to="360 32 34" dur="2s" repeatCount="indefinite"/></path>'
            f'<circle cx="32" cy="34" r="3.5" fill="{t["accent3"]}"/>')


SECTIONS = [
    # slug, title, kind, subtitle, status, status is "live" (pulsing green dot), icon
    ("about", "about", "Engineer", "who I am and what I like to run", "Running", True, icon_container),
    ("experience", "experience", "Job", "1 completed · sole developer · 2022 – 2023", "Completed", False, icon_pipeline),
    ("projects", "projects", "Deployment", "what I designed, built and shipped", "5/5 Ready", True, icon_pods),
    ("stack", "stack", "ConfigMap", "the tools I reach for, layer by layer", "7 keys", False, icon_layers),
    ("languages", "languages", "Metrics", "bytes of code across my public repos", "Scraped daily", True, icon_metrics),
    ("how", "how this page works", "CronJob", "rebuilt every night by a GitHub Action", "17 3 * * *", False, icon_cron),
]


def section(title: str, kind: str, subtitle: str, status: str, live: bool, icon) -> callable:
    def render(s: dict, t: dict) -> str:
        w, h = 900, 84
        chip_w = len(status) * 13 * 0.62 + 34
        chip_x = w - 8 - chip_w
        dot = t["ok"] if live else t["accent"]
        pulse = (f'<circle cx="{chip_x + 14}" cy="30" r="4" fill="none" stroke="{dot}">'
                 f'<animate attributeName="r" values="4;10" dur="1.6s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values=".8;0" dur="1.6s" repeatCount="indefinite"/></circle>') if live else ""
        style = f"""
          .ti {{ font: 700 24px {SANS}; fill: {t["text"]}; letter-spacing: -.3px; }}
          .kd {{ font: 600 13px {MONO}; fill: {t["accent2"]}; }}
          .sub {{ font: 13px {MONO}; fill: {t["muted"]}; }}
          .st {{ font: 600 13px {MONO}; fill: {t["text"]}; }}
          .flow {{ stroke-dasharray: 4 6; animation: dash 1.2s linear infinite; }}
          @keyframes dash {{ to {{ stroke-dashoffset: -20 }} }}
          .bob {{ animation: bob 3s ease-in-out infinite; }}
          @keyframes bob {{ 50% {{ transform: translateY(-3px) }} }}
          .pop {{ transform-box: fill-box; transform-origin: center; animation: pop 4s cubic-bezier(.3,1.6,.5,1) infinite both; }}
          @keyframes pop {{ 0% {{ transform: scale(0) }} 12%, 85% {{ transform: scale(1) }} 100% {{ transform: scale(0) }} }}
          .drop {{ animation: drop 4s cubic-bezier(.3,1.3,.5,1) infinite both; }}
          @keyframes drop {{ 0% {{ transform: translateY(-14px); opacity: 0 }} 15%, 85% {{ transform: none; opacity: 1 }} 100% {{ opacity: 0 }} }}
        """
        body = f"""
        <g transform="translate(4 4)">{icon(t)}</g>
        <text x="84" y="36"><tspan class="ti">{escape(title)}</tspan><tspan class="kd" dx="14">kind: {kind}</tspan></text>
        <text x="84" y="60" class="sub">{escape(subtitle)}</text>
        <rect x="{chip_x:.1f}" y="17" width="{chip_w:.1f}" height="26" rx="13" fill="{t["panel"]}" stroke="{t["border"]}"/>
        {pulse}<circle cx="{chip_x + 14:.1f}" cy="30" r="4" fill="{dot}"/>
        <text x="{chip_x + 25:.1f}" y="34.5" class="st">{escape(status)}</text>
        <path id="wire" d="M 84 {h - 6} H {w - 8}" stroke="{t["border"]}" stroke-width="1.5" class="flow"/>
        <circle r="3" fill="{t["accent"]}"><animateMotion dur="5s" repeatCount="indefinite"><mpath href="#wire"/></animateMotion></circle>
        """
        return svg(w, h, body, f"{title} (kind: {kind}) — {status}", style)
    return render


# ------------------------------------------------------------------- footer

def footer(s: dict, t: dict) -> str:
    w, h = 900, 70
    waves = []
    for i, (color, dur, amp, op) in enumerate([(t["accent2"], 9, 10, .35), (t["accent"], 6, 14, .5), (t["accent3"], 12, 8, .3)]):
        def wave(phase: float) -> str:
            pts = " ".join(f"{x},{40 + amp * math.sin(x / 70 + phase + i):.1f}" for x in range(0, w + 1, 20))
            return f"M {pts}"
        frames = ";".join(wave(p) for p in (0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi))
        waves.append(f'<path fill="none" stroke="{color}" stroke-width="2" stroke-opacity="{op}" d="{wave(0)}">'
                     f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" values="{frames}"/></path>')
    body = "".join(waves)
    return svg(w, h, body, "Decorative footer")


def main() -> None:
    s = summarize(fetch())
    OUT.mkdir(parents=True, exist_ok=True)
    cards = [("header", header), ("terminal", terminal), ("languages", languages), ("footer", footer)]
    cards += [(f"section-{slug}", section(*rest)) for slug, *rest in SECTIONS]
    for name, render in cards:
        for theme, palette in THEMES.items():
            (OUT / f"{name}-{theme}.svg").write_text(render(s, palette))
    print(f"ok: {s['total']} contributions, {len(s['langs'])} languages, streak {s['current_streak']}/{s['best_streak']}")


if __name__ == "__main__":
    main()
