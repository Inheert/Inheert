#!/usr/bin/env python3
"""Generate the profile README visuals from live GitHub data.

Stdlib only, so the workflow needs no `pip install`. Every card is written
twice (dark and light) into assets/generated/, and the README's ACTIVITY
block is rewritten in place.

    GITHUB_TOKEN=... python3 scripts/generate.py
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("PROFILE_LOGIN", "Inheert")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "generated"
README = ROOT / "README.md"

# Languages that are build plumbing rather than something written by hand.
IGNORED_LANGUAGES = {"Makefile", "CMake", "Batchfile", "Dockerfile", "Shell", "HTML", "CSS"}

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "dark": {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d", "grid": "#21262d",
        "text": "#e6edf3", "muted": "#8b949e", "faint": "#484f58",
        "accent": "#39d0d8", "accent2": "#a371f7", "accent3": "#f0b429", "ok": "#3fb950",
        # Contribution levels 0..4 (top faces of the skyline).
        "levels": ["#1c2128", "#13646c", "#1a9aa4", "#2fd0da", "#8af7fc"],
        "shade_front": 0.78, "shade_side": 0.58,
    },
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de", "grid": "#eaeef2",
        "text": "#1f2328", "muted": "#656d76", "faint": "#afb8c1",
        "accent": "#0a7ea4", "accent2": "#8250df", "accent3": "#bf8700", "ok": "#1a7f37",
        "levels": ["#e4e9ee", "#a5e3ea", "#4cc2cf", "#1494a4", "#0b5f6d"],
        "shade_front": 0.86, "shade_side": 0.7,
    },
}

ROLES = [
    "C & C++ student @ 42 Mulhouse",
    "Go backends, Postgres & Docker",
    "Flutter / Dart mobile apps",
    "Kubernetes tinkerer: K3s, Argo CD",
    "Godot & Garry's Mod gamedev",
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
    user["events"] = _request(f"https://api.github.com/users/{LOGIN}/events/public?per_page=30")
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
        "events": user["events"],
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ------------------------------------------------------------------ helpers

def shade(hex_color: str, factor: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c * factor))) for c in (r, g, b))


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

    # Orbits on the right: three tilted ellipses, an electron on each.
    cx, cy = 770, 115
    orbits = []
    for i, (angle, dur, color) in enumerate([(0, 6, t["accent"]), (60, 8, t["accent2"]), (120, 7, t["accent3"])]):
        path = f"M {cx - 92} {cy} a 92 34 0 1 0 184 0 a 92 34 0 1 0 -184 0"
        orbits.append(
            f'<g transform="rotate({angle} {cx} {cy})">'
            f'<path id="o{i}" d="{path}" fill="none" stroke="{color}" stroke-opacity=".35" stroke-width="1.5"/>'
            f'<circle r="5" fill="{color}" filter="url(#glow)">'
            f'<animateMotion dur="{dur}s" repeatCount="indefinite" begin="-{i * 1.7}s"><mpath href="#o{i}"/></animateMotion>'
            f"</circle></g>"
        )
    nucleus = (f'<circle cx="{cx}" cy="{cy}" r="16" fill="url(#core)">'
               f'<animate attributeName="r" values="14;18;14" dur="3s" repeatCount="indefinite"/></circle>'
               f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" class="core">42</text>')

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
    <text x="56" y="116" class="aka in d1">aka @{LOGIN} · software developer in the making</text>
    <g class="in d2"><text x="{tx - 24}" y="{ty}" class="pr">❯</text>{"".join(roles)}</g>
    {"".join(orbits)}{nucleus}
    """
    return svg(w, h, body, f"{s['name']} — {', '.join(ROLES)}", style)


# ----------------------------------------------------------------- terminal

def terminal(s: dict, t: dict) -> str:
    w, h = 900, 400
    top = [lang for lang, _ in s["langs"][:4]]
    info = [
        ("title", f"{LOGIN.lower()}@github"),
        ("rule", "─" * 26),
        ("Name", s["name"]),
        ("School", "42 Mulhouse · Common Core"),
        ("Uptime", s["uptime"]),
        ("Repos", f"{s['repos']} public · {s['stars']} ★ · {s['followers']} followers"),
        ("Contribs", f"{s['total']} in the last year ({s['active_days']} active days)"),
        ("Streak", f"current {s['current_streak']}d · best {s['best_streak']}d"),
        ("Langs", " · ".join(top)),
        ("Stack", "Go · Flutter · Docker · K3s · Godot"),
        ("Shell", "zsh + a lot of Makefiles"),
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


# ------------------------------------------------------------------ skyline

def skyline(s: dict, t: dict) -> str:
    """The contribution calendar as an oblique-projection city, built tower by tower."""
    w = 900
    weeks = s["weeks"]
    ux, uy = 14.0, 3.6      # one week to the right (and slightly down)
    vx, vy = -6.5, 6.5      # one weekday towards the viewer
    fill = 0.82
    max_h = 92.0
    peak = max((d["contributionCount"] for wk in weeks for d in wk), default=1) or 1

    origin_x = 50 + 7 * -vx
    origin_y = 40 + max_h
    level_index = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

    cells = []
    for wi, wk in enumerate(weeks):
        for d in wk:
            di = dt.date.fromisoformat(d["date"]).isoweekday() % 7  # Sunday = 0, as on GitHub
            cells.append((wi, di, d))
    cells.sort(key=lambda c: (c[0] + c[1], c[1]))

    def pt(px: float, py: float) -> str:
        return f"{px:.1f},{py:.1f}"

    towers = []
    for wi, di, d in cells:
        n = d["contributionCount"]
        lvl = level_index.get(d["contributionLevel"], 0)
        height = 2.0 if n == 0 else 6 + (max_h - 6) * math.sqrt(n / peak)
        ax = origin_x + wi * ux + di * vx
        ay = origin_y + wi * uy + di * vy
        bx, by = ax + ux * fill, ay + uy * fill
        dx, dy = ax + vx * fill, ay + vy * fill
        cx, cy = bx + vx * fill, by + vy * fill
        top_color = t["levels"][lvl]
        top = f'{pt(ax, ay - height)} {pt(bx, by - height)} {pt(cx, cy - height)} {pt(dx, dy - height)}'
        front = f'{pt(dx, dy - height)} {pt(cx, cy - height)} {pt(cx, cy)} {pt(dx, dy)}'
        side = f'{pt(bx, by - height)} {pt(cx, cy - height)} {pt(cx, cy)} {pt(bx, by)}'
        tip = f'{n} contribution{"s" if n != 1 else ""} on {d["date"]}'
        delay = (wi + di) * 0.022
        towers.append(
            f'<g class="t" style="animation-delay:{delay:.2f}s"><title>{tip}</title>'
            f'<polygon points="{front}" fill="{shade(top_color, t["shade_front"])}"/>'
            f'<polygon points="{side}" fill="{shade(top_color, t["shade_side"])}"/>'
            f'<polygon points="{top}" fill="{top_color}"/></g>'
        )

    # Month labels along the front edge.
    labels = []
    last_month = None
    for wi, wk in enumerate(weeks):
        month = dt.date.fromisoformat(wk[0]["date"]).strftime("%b")
        if month != last_month and wi < len(weeks) - 2:
            lx = origin_x + wi * ux + 7 * vx + 4
            ly = origin_y + wi * uy + 7 * vy + 18
            angle = math.degrees(math.atan2(uy, ux))
            labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="mo" transform="rotate({angle:.1f} {lx:.1f} {ly:.1f})">{month}</text>')
        last_month = month

    bd = s["best_day"]
    stats = [
        (f"{s['total']}", "contributions"),
        (f"{s['commits']}", "commits"),
        (f"{s['best_streak']}d", "best streak"),
        (f"{bd['contributionCount']}", f"best day · {dt.date.fromisoformat(bd['date']).strftime('%d %b')}"),
    ]
    stat_svg = "".join(
        f'<g transform="translate({w - 40 - (len(stats) - 1 - i) * 128} 52)" class="st" style="animation-delay:{1.4 + i * 0.15:.2f}s">'
        f'<text class="big" text-anchor="end">{escape(v)}</text><text y="20" class="lbl" text-anchor="end">{escape(k)}</text></g>'
        for i, (v, k) in enumerate(stats)
    )
    height = int(origin_y + len(weeks) * uy + 7 * vy + 44)

    legend = "".join(f'<rect x="{w - 150 + i * 16}" y="{height - 30}" width="12" height="12" rx="2" fill="{c}"/>'
                     for i, c in enumerate(t["levels"]))
    style = f"""
      .t {{ transform-box: fill-box; transform-origin: 50% 100%; animation: grow 1s cubic-bezier(.2,.9,.25,1.15) both; }}
      @keyframes grow {{ from {{ transform: scaleY(0); opacity: 0 }} 30% {{ opacity: 1 }} to {{ transform: scaleY(1) }} }}
      .mo {{ font: 11px {MONO}; fill: {t["muted"]}; }}
      .h  {{ font: 700 16px {SANS}; fill: {t["text"]}; }}
      .sub {{ font: 12px {MONO}; fill: {t["muted"]}; }}
      .big {{ font: 800 26px {SANS}; fill: {t["accent"]}; }}
      .lbl {{ font: 12px {SANS}; fill: {t["muted"]}; }}
      .st {{ animation: show .6s ease-out both; }}
      @keyframes show {{ from {{ opacity: 0; transform: translateY(8px) }} to {{ opacity: 1 }} }}
    """
    body = f"""
    {panel(t, w, height)}
    <text x="24" y="34" class="h">contribution skyline</text>
    <text x="24" y="54" class="sub">last 12 months · one tower per day</text>
    {"".join(towers)}
    {"".join(labels)}
    {stat_svg}
    <text x="{w - 158}" y="{height - 20}" class="lbl" text-anchor="end">less</text>{legend}
    <text x="{w - 64}" y="{height - 20}" class="lbl">more</text>
    """
    return svg(w, height, body, f"{s['total']} contributions in the last year, drawn as a 3D skyline", style)


# ---------------------------------------------------------------- languages

def languages(s: dict, t: dict) -> str:
    w, h = 900, 150
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
        segs.append(f'<rect x="{x:.1f}" y="56" width="{seg:.1f}" height="12" fill="{color}" class="seg" '
                    f'style="animation-delay:{0.1 + i * 0.08:.2f}s"><title>{escape(name)} {pct:.1%}</title></rect>')
        x += seg
        col, row = i % 4, i // 4
        lx, ly = 24 + col * 216, 98 + row * 26
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
    <text x="24" y="34" class="h">languages</text>
    <text x="{w - 24}" y="34" class="sub" text-anchor="end">bytes of code across public repos · build files excluded</text>
    <clipPath id="bar"><rect x="24" y="56" width="{bar_w}" height="12" rx="6"/></clipPath>
    <rect x="24" y="56" width="{bar_w}" height="12" rx="6" fill="{t["grid"]}"/>
    <g clip-path="url(#bar)">{"".join(segs)}</g>
    {"".join(legend)}
    """
    return svg(w, h, body, "Most used languages: " + ", ".join(n for n, _ in langs), style)


# ------------------------------------------------------------------- footer

def footer(s: dict, t: dict) -> str:
    w, h = 900, 90
    waves = []
    for i, (color, dur, amp, op) in enumerate([(t["accent2"], 9, 10, .35), (t["accent"], 6, 14, .5), (t["accent3"], 12, 8, .3)]):
        def wave(phase: float) -> str:
            pts = " ".join(f"{x},{40 + amp * math.sin(x / 70 + phase + i):.1f}" for x in range(0, w + 1, 20))
            return f"M {pts}"
        frames = ";".join(wave(p) for p in (0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi))
        waves.append(f'<path fill="none" stroke="{color}" stroke-width="2" stroke-opacity="{op}" d="{wave(0)}">'
                     f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" values="{frames}"/></path>')
    style = f".f {{ font: 12px {MONO}; fill: {t['muted']}; }}"
    body = (f'{"".join(waves)}<text x="{w / 2}" y="82" text-anchor="middle" class="f">'
            f"generated by scripts/generate.py · last run {s['generated']}</text>")
    return svg(w, h, body, "Decorative footer", style)


# ------------------------------------------------------------------- README

EVENT_TEXT = {
    "PushEvent": ("🔨", lambda e: f"pushed {len(e['payload'].get('commits', [])) or 'some'} commit(s) to"),
    "CreateEvent": ("🌱", lambda e: f"created {e['payload'].get('ref_type', 'something')} in"),
    "PullRequestEvent": ("🔀", lambda e: f"{e['payload'].get('action', 'touched')} a pull request in"),
    "IssuesEvent": ("🐛", lambda e: f"{e['payload'].get('action', 'touched')} an issue in"),
    "WatchEvent": ("⭐", lambda e: "starred"),
    "ForkEvent": ("🍴", lambda e: "forked"),
    "ReleaseEvent": ("🚀", lambda e: "published a release of"),
    "PublicEvent": ("📢", lambda e: "open-sourced"),
}


def activity(s: dict) -> str:
    rows, seen = [], set()
    for e in s["events"]:
        if e["type"] not in EVENT_TEXT:
            continue
        icon, text = EVENT_TEXT[e["type"]]
        repo = e["repo"]["name"]
        line = f"{text(e)} [{repo}](https://github.com/{repo})"
        day = e["created_at"][:10]
        if (line, day) in seen:
            continue
        seen.add((line, day))
        rows.append(f"{icon} {line} <sub>· {day}</sub>")
        if len(rows) == 6:
            break
    if not rows:
        rows = ["😴 nothing public lately, probably deep in a private repo"]
    return "\n".join(f"{i + 1}. {r}" for i, r in enumerate(rows))


def update_readme(s: dict) -> None:
    text = README.read_text()
    new = re.sub(
        r"(<!-- ACTIVITY:START -->).*?(<!-- ACTIVITY:END -->)",
        lambda m: f"{m.group(1)}\n{activity(s)}\n{m.group(2)}",
        text,
        flags=re.S,
    )
    README.write_text(new)


def main() -> None:
    s = summarize(fetch())
    OUT.mkdir(parents=True, exist_ok=True)
    for name, render in [("header", header), ("terminal", terminal), ("skyline", skyline),
                         ("languages", languages), ("footer", footer)]:
        for theme, palette in THEMES.items():
            (OUT / f"{name}-{theme}.svg").write_text(render(s, palette))
    update_readme(s)
    print(f"ok: {s['total']} contributions, {len(s['langs'])} languages, streak {s['current_streak']}/{s['best_streak']}")


if __name__ == "__main__":
    main()
