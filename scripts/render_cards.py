#!/usr/bin/env python3
"""
Renders the animated SVG card stack for sahil-kumar-ai's GitHub README.
Usage:
  python scripts/render_cards.py             # Animated production cards
  STATIC=1 python scripts/render_cards.py    # Final frame for screenshots
  PORTRAIT_PATH=assets/avatar.png python scripts/render_cards.py
"""

from __future__ import annotations

import base64
import datetime as dt
import html
import json
import mimetypes
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration & Brand Tokens (sahil-kumar-ai)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = ROOT / "cards"
DATA_FILE = ROOT / "data" / "contributions.json"
FONTS_DIR = ROOT / "assets" / "fonts"

STATIC = os.environ.get("STATIC", "0") == "1"
PORTRAIT_PATH = os.environ.get("PORTRAIT_PATH", "")

PALETTE = {
    "bg_canvas": "#0B0F17",
    "bg_card": "#111827",
    "bg_card_alt": "#0D1320",
    "bg_pill": "#1E293B",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "accent_cyan": "#38BDF8",
    "accent_indigo": "#818CF8",
    "accent_emerald": "#34D399",
    "border_subtle": "#1E293B",
    # Brand contribution heatmap ramp (Level 0 -> Level 4)
    "heat_0": "#161F30",
    "heat_1": "#0C4A6E",
    "heat_2": "#0284C7",
    "heat_3": "#38BDF8",
    "heat_4": "#818CF8",
}

PROFILE = {
    "name": "Sahil Kumar",
    "handle": "@sahil-kumar-ai",
    "tagline": "Building autonomous AI systems, scalable infrastructure, and human-agent interfaces.",
    "status": "Shipping multi-agent orchestrators & edge inference pipelines",
    "location": "San Francisco / Remote",
    "tiles": [
        {
            "slug": "portfolio",
            "title": "Live Apps & Web",
            "subtitle": "sahilkumar.ai",
            "badge": "PORTFOLIO",
            "accent": "#38BDF8",
            "icon": "globe",
            "delay": 0.16,
        },
        {
            "slug": "models",
            "title": "Open Models & Systems",
            "subtitle": "Hugging Face / GitHub",
            "badge": "RESEARCH",
            "accent": "#818CF8",
            "icon": "cpu",
            "delay": 0.24,
        },
        {
            "slug": "linkedin",
            "title": "Connect on LinkedIn",
            "subtitle": "in/sahil-kumar-ai",
            "badge": "NETWORK",
            "accent": "#34D399",
            "icon": "link",
            "delay": 0.32,
        },
    ],
    "repos": [
        {
            "slug": "agentic-core",
            "name": "sahil-kumar-ai/agentic-core",
            "short_name": "agentic-core",
            "description": "Deterministic orchestrator for multi-agent LLM systems with DAG state recovery, tool sandboxing, and zero-copy streaming telemetry.",
            "language": "Python",
            "lang_color": "#38BDF8",
            "stars": "1.4k",
            "forks": "182",
            "topics": ["multi-agent", "llm-orchestration", "deterministic-dag", "python"],
            "sparkline": [12, 18, 15, 26, 32, 29, 41, 38, 52, 48, 61, 68],
            "delay": 0.62,
        },
        {
            "slug": "vision-stream-pipeline",
            "name": "sahil-kumar-ai/vision-stream-pipeline",
            "short_name": "vision-stream-pipeline",
            "description": "Sub-15ms real-time edge video inference pipeline using TensorRT, async WebRTC frame queues, and adaptive spatial batching.",
            "language": "Python / C++",
            "lang_color": "#818CF8",
            "stars": "890",
            "forks": "94",
            "topics": ["edge-ai", "computer-vision", "tensorrt", "webrtc"],
            "sparkline": [8, 14, 19, 17, 25, 31, 28, 35, 42, 39, 49, 55],
            "delay": 0.76,
        },
    ],
}


# ---------------------------------------------------------------------------
# Font Subsetting (pyftsubset -> base64 WOFF data URI)
# ---------------------------------------------------------------------------
FONT_URLS = {
    "Inter-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf",
}


def ensure_source_font() -> Path | None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    candidates = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
    if candidates:
        return candidates[0]
    target = FONTS_DIR / "Inter-Variable.ttf"
    try:
        urllib.request.urlretrieve(FONT_URLS["Inter-Regular.ttf"], target)
        return target
    except Exception:
        return None


def build_subset_woff_data_uri(text_corpus: str) -> str:
    """Subsets the font to only used glyphs via pyftsubset and returns a base64 WOFF URI."""
    font_path = ensure_source_font()
    if not font_path or not font_path.exists():
        return ""

    unique_chars = "".join(sorted(set(text_corpus)))
    with tempfile.TemporaryDirectory() as tmpdir:
        out_woff = Path(tmpdir) / "subset.woff"
        cmd = [
            "pyftsubset",
            str(font_path),
            f"--text={unique_chars}",
            "--flavor=woff",
            f"--output-file={out_woff}",
            "--layout-features=kern,liga,calt,tnum",
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            raw = out_woff.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
            return f"data:font/woff;base64,{b64}"
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Contribution Data Loader & Fallback Generator
# ---------------------------------------------------------------------------
def load_or_generate_contributions() -> dict[str, Any]:
    if DATA_FILE.exists():
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return compute_stats(raw)

    # Deterministic realistic fallback if data/contributions.json hasn't been fetched yet
    today = dt.date.today()
    start_date = today - dt.timedelta(days=364)
    start_date -= dt.timedelta(days=(start_date.weekday() + 1) % 7)  # Align to Sunday

    days = []
    cur = start_date
    idx = 0
    while cur <= today:
        wave = ((idx * 17 + cur.month * 13) % 19)
        weekday_boost = 0 if cur.weekday() in (5, 6) else 3
        count = max(0, wave + weekday_boost - 6)
        if idx % 11 == 0:
            count = 0
        days.append({"date": cur.isoformat(), "count": count})
        cur += dt.timedelta(days=1)
        idx += 1

    return compute_stats({"user": "sahil-kumar-ai", "days": days})


def compute_stats(payload: dict[str, Any]) -> dict[str, Any]:
    days = sorted(payload.get("days", []), key=lambda d: d["date"])
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)

    # Busiest day
    busiest = max(days, key=lambda d: d["count"]) if days else {"date": "N/A", "count": 0}
    try:
        busiest_dt = dt.date.fromisoformat(busiest["date"])
        busiest_label = busiest_dt.strftime("%b %d")
    except Exception:
        busiest_label = busiest["date"]

    # Current & Longest streak
    cur_streak = 0
    longest_streak = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0
    for d in reversed(days):
        if d["count"] > 0:
            cur_streak += 1
        else:
            break

    # Monthly aggregation (last 12 months)
    monthly_map: dict[str, int] = {}
    for d in days:
        ym = d["date"][:7]
        monthly_map[ym] = monthly_map.get(ym, 0) + d["count"]
    months_sorted = sorted(monthly_map.items())[-12:]
    months = []
    for ym, cnt in months_sorted:
        y, m = ym.split("-")
        label = dt.date(int(y), int(m), 1).strftime("%b")
        months.append({"ym": ym, "label": label, "count": cnt})

    return {
        "days": days,
        "total": total,
        "active_days": active_days,
        "total_days": len(days),
        "current_streak": cur_streak,
        "longest_streak": longest_streak,
        "busiest_count": busiest["count"],
        "busiest_label": busiest_label,
        "months": months,
    }


# ---------------------------------------------------------------------------
# Shared SVG Defs, CSS Keyframes & Reduced-Motion Support
# ---------------------------------------------------------------------------
def shared_style_and_defs(woff_uri: str, base_delay: float = 0.0) -> str:
    font_face = ""
    if woff_uri:
        font_face = f"""
        @font-face {{
          font-family: 'BrandSans';
          src: url('{woff_uri}') format('woff');
          font-weight: 100 900;
          font-style: normal;
          font-display: block;
        }}
        """

    if STATIC:
        motion_css = """
        .card-enter, .fade-up, .bar-grow, .pulse-dot {
          opacity: 1 !important;
          transform: none !important;
          animation: none !important;
        }
        """
    else:
        motion_css = f"""
        @keyframes cardReveal {{
          0% {{ opacity: 0; transform: translateY(10px); }}
          100% {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes fadeUp {{
          0% {{ opacity: 0; transform: translateY(6px); }}
          100% {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes pulseGlow {{
          0%, 100% {{ opacity: 0.95; transform: scale(1); }}
          50% {{ opacity: 0.45; transform: scale(0.92); }}
        }}
        .card-enter {{
          opacity: 0;
          animation: cardReveal 0.65s cubic-bezier(0.22, 1, 0.36, 1) {base_delay:.2f}s forwards;
        }}
        .fade-up {{
          opacity: 0;
          animation: fadeUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) calc({base_delay:.2f}s + var(--d, 0.12s)) forwards;
        }}
        .pulse-dot {{
          transform-box: fill-box;
          transform-origin: center;
          animation: pulseGlow 2.8s ease-in-out infinite;
        }}
        """

    return f"""
  <defs>
    <linearGradient id="cardSurface" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{PALETTE['bg_card']}" />
      <stop offset="100%" stop-color="{PALETTE['bg_card_alt']}" />
    </linearGradient>
    <linearGradient id="brandBorder" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{PALETTE['accent_cyan']}" stop-opacity="0.55" />
      <stop offset="45%" stop-color="#FFFFFF" stop-opacity="0.12" />
      <stop offset="100%" stop-color="{PALETTE['accent_indigo']}" stop-opacity="0.55" />
    </linearGradient>
    <linearGradient id="brandAccent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{PALETTE['accent_cyan']}" />
      <stop offset="100%" stop-color="{PALETTE['accent_indigo']}" />
    </linearGradient>
    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{PALETTE['accent_cyan']}" />
      <stop offset="100%" stop-color="{PALETTE['accent_indigo']}" stop-opacity="0.35" />
    </linearGradient>
    <radialGradient id="ambientGlow" cx="85%" cy="15%" r="65%">
      <stop offset="0%" stop-color="{PALETTE['accent_cyan']}" stop-opacity="0.14" />
      <stop offset="50%" stop-color="{PALETTE['accent_indigo']}" stop-opacity="0.06" />
      <stop offset="100%" stop-color="{PALETTE['bg_canvas']}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <style>
    {font_face}
    .root {{
      font-family: 'BrandSans', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .display {{
      font-size: 30px;
      font-weight: 700;
      letter-spacing: -0.025em;
      fill: {PALETTE['text_primary']};
    }}
    .title {{
      font-size: 17px;
      font-weight: 600;
      letter-spacing: -0.015em;
      fill: {PALETTE['text_primary']};
    }}
    .body {{
      font-size: 14px;
      font-weight: 400;
      letter-spacing: 0em;
      fill: {PALETTE['text_secondary']};
    }}
    .label {{
      font-size: 10.5px;
      font-weight: 600;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      fill: {PALETTE['text_muted']};
    }}
    .metric {{
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums;
      fill: {PALETTE['text_primary']};
    }}
    {motion_css}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-delay: 0s !important;
        animation-iteration-count: 1 !important;
        transition: none !important;
      }}
      .card-enter, .fade-up {{
        opacity: 1 !important;
        transform: none !important;
      }}
    }}
  </style>
"""


def card_frame(width: int, height: int, woff_uri: str, base_delay: float, inner_svg: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" class="root" role="img">
  {shared_style_and_defs(woff_uri, base_delay)}
  <rect width="{width}" height="{height}" rx="18" fill="{PALETTE['bg_canvas']}" />
  <g class="card-enter">
    <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="17" fill="url(#cardSurface)" stroke="url(#brandBorder)" stroke-width="1.2" />
    <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="17" fill="url(#ambientGlow)" />
    <line x1="24" y1="1.2" x2="{width - 24}" y2="1.2" stroke="#FFFFFF" stroke-opacity="0.16" stroke-width="1" />
    {inner_svg}
  </g>
</svg>
"""


# ---------------------------------------------------------------------------
# 1. Hero Card (cards/hero.svg)
# ---------------------------------------------------------------------------
def build_portrait_fragment(x: int, y: int, size: int = 88) -> str:
    cx = x + size // 2
    cy = y + size // 2
    r = size // 2
    if PORTRAIT_PATH and Path(PORTRAIT_PATH).exists():
        p = Path(PORTRAIT_PATH)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"""
        <defs>
          <clipPath id="portraitClip">
            <circle cx="{cx}" cy="{cy}" r="{r - 3}" />
          </clipPath>
        </defs>
        <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#brandAccent)" stroke-width="2" />
        <image href="data:{mime};base64,{b64}" x="{x + 3}" y="{y + 3}" width="{size - 6}" height="{size - 6}" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)" />
        """

    # Default geometric AI orbital emblem when PORTRAIT_PATH is omitted
    smil_spin = ""
    if not STATIC:
        smil_spin = f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="24s" repeatCount="indefinite" />'
    return f"""
    <g class="fade-up" style="--d: 0.18s">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="{PALETTE['bg_pill']}" stroke="url(#brandBorder)" stroke-width="1.5" />
      <g>
        <circle cx="{cx}" cy="{cy}" r="{r - 12}" fill="none" stroke="url(#brandAccent)" stroke-width="1.2" stroke-dasharray="6 6" opacity="0.75" />
        {smil_spin}
      </g>
      <circle cx="{cx}" cy="{cy}" r="18" fill="url(#brandAccent)" opacity="0.2" />
      <text x="{cx}" y="{cy + 6}" text-anchor="middle" class="title" fill="{PALETTE['text_primary']}">SK</text>
    </g>
    """


def render_hero(woff_uri: str) -> str:
    w, h = 840, 176
    portrait = build_portrait_fragment(716, 44, 88)
    inner = f"""
    <g class="fade-up" style="--d: 0.06s">
      <rect x="32" y="28" width="204" height="24" rx="12" fill="{PALETTE['bg_pill']}" stroke="{PALETTE['border_subtle']}" />
      <circle cx="46" cy="40" r="4" fill="{PALETTE['accent_emerald']}" class="pulse-dot" />
      <text x="58" y="44" class="label" fill="{PALETTE['text_secondary']}">{html.escape(PROFILE['handle'])} · AI SYSTEMS</text>
    </g>
    <g class="fade-up" style="--d: 0.12s">
      <text x="32" y="92" class="display">{html.escape(PROFILE['name'])}</text>
      <text x="32" y="120" class="body">{html.escape(PROFILE['tagline'])}</text>
    </g>
    <g class="fade-up" style="--d: 0.18s">
      <text x="32" y="148" class="label" fill="{PALETTE['accent_cyan']}">● {html.escape(PROFILE['status'])}</text>
    </g>
    {portrait}
    """
    return card_frame(w, h, woff_uri, 0.0, inner)


# ---------------------------------------------------------------------------
# 2. Three Linked Tiles in a Row (cards/tile-*.svg)
# ---------------------------------------------------------------------------
def icon_svg(name: str, color: str) -> str:
    if name == "globe":
        return f"""
        <circle cx="20" cy="20" r="9" fill="none" stroke="{color}" stroke-width="1.7"/>
        <ellipse cx="20" cy="20" rx="4.2" ry="9" fill="none" stroke="{color}" stroke-width="1.5"/>
        <line x1="11" y1="20" x2="29" y2="20" stroke="{color}" stroke-width="1.5"/>
        """
    if name == "cpu":
        return f"""
        <rect x="13" y="13" width="14" height="14" rx="3" fill="none" stroke="{color}" stroke-width="1.7"/>
        <rect x="17" y="17" width="6" height="6" rx="1" fill="{color}" opacity="0.8"/>
        <line x1="17" y1="9" x2="17" y2="13" stroke="{color}" stroke-width="1.5"/>
        <line x1="23" y1="9" x2="23" y2="13" stroke="{color}" stroke-width="1.5"/>
        <line x1="17" y1="27" x2="17" y2="31" stroke="{color}" stroke-width="1.5"/>
        <line x1="23" y1="27" x2="23" y2="31" stroke="{color}" stroke-width="1.5"/>
        """
    return f"""
    <path d="M16 24 L24 16 M18 16 H24 V22" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="11" y="11" width="18" height="18" rx="5" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.65"/>
    """


def render_tile(tile: dict[str, Any], woff_uri: str) -> str:
    w, h = 272, 118
    accent = tile["accent"]
    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <rect x="20" y="18" width="40" height="40" rx="10" fill="{PALETTE['bg_pill']}" stroke="{PALETTE['border_subtle']}" />
      <g transform="translate(20, 18)">
        {icon_svg(tile['icon'], accent)}
      </g>
      <text x="72" y="34" class="label" fill="{accent}">{html.escape(tile['badge'])}</text>
      <text x="242" y="36" text-anchor="end" class="body" fill="{PALETTE['text_muted']}">↗</text>
    </g>
    <g class="fade-up" style="--d: 0.10s">
      <text x="20" y="80" class="title">{html.escape(tile['title'])}</text>
      <text x="20" y="100" class="body" font-size="12.5">{html.escape(tile['subtitle'])}</text>
    </g>
    """
    return card_frame(w, h, woff_uri, tile["delay"], inner)


# ---------------------------------------------------------------------------
# 3. Monthly Contributions + Streak, Active Days & Busiest Day (cards/monthly-chart.svg)
# ---------------------------------------------------------------------------
def render_monthly_chart(stats: dict[str, Any], woff_uri: str) -> str:
    w, h = 840, 230
    months = stats["months"]
    max_val = max((m["count"] for m in months), default=1) or 1

    chart_x = 32
    chart_y = 78
    chart_w = 470
    chart_h = 112
    n = max(len(months), 1)
    slot_w = chart_w / n
    bar_w = min(24.0, slot_w * 0.58)

    bars_svg = []
    for idx, m in enumerate(months):
        ratio = m["count"] / max_val
        bh = max(6.0, round(ratio * chart_h, 1))
        bx = round(chart_x + idx * slot_w + (slot_w - bar_w) / 2, 1)
        by = round(chart_y + chart_h - bh, 1)
        baseline = chart_y + chart_h
        delay_s = round(0.50 + idx * 0.035, 2)

        if STATIC:
            anim = ""
            y_attr = by
            h_attr = bh
        else:
            y_attr = baseline
            h_attr = 0
            anim = f"""
            <animate attributeName="y" from="{baseline}" to="{by}" dur="0.55s" begin="{delay_s}s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1" />
            <animate attributeName="height" from="0" to="{bh}" dur="0.55s" begin="{delay_s}s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1" />
            """

        bars_svg.append(f"""
        <g>
          <rect x="{bx}" y="{chart_y}" width="{bar_w:.1f}" height="{chart_h}" rx="5" fill="{PALETTE['bg_pill']}" opacity="0.45" />
          <rect x="{bx}" y="{y_attr}" width="{bar_w:.1f}" height="{h_attr}" rx="5" fill="url(#barGrad)">
            {anim}
          </rect>
          <text x="{bx + bar_w / 2:.1f}" y="{baseline + 18}" text-anchor="middle" class="label" font-size="9.5">{html.escape(m['label'])}</text>
        </g>
        """)

    # Right-side KPI Bento Stack (Streak, Active Days, Busiest Day)
    kpis = [
        ("CURRENT / MAX STREAK", f"{stats['current_streak']}d", f"Longest {stats['longest_streak']}d", PALETTE["accent_cyan"], 532, 62),
        ("ACTIVE DAYS (1Y)", f"{stats['active_days']}", f"of {stats['total_days']} tracked days", PALETTE["accent_indigo"], 680, 62),
        ("BUSIEST DAY", f"{stats['busiest_count']} commits", f"Peak on {stats['busiest_label']}", PALETTE["accent_emerald"], 532, 140),
        ("ANNUAL OUTPUT", f"{stats['total']:,}", "Total contributions", PALETTE["text_primary"], 680, 140),
    ]
    kpi_svg = []
    for label, val, sub, color, kx, ky in kpis:
        kpi_svg.append(f"""
        <g class="fade-up" style="--d: 0.16s">
          <rect x="{kx}" y="{ky}" width="136" height="68" rx="12" fill="{PALETTE['bg_pill']}" fill-opacity="0.6" stroke="{PALETTE['border_subtle']}" />
          <text x="{kx + 14}" y="{ky + 20}" class="label" font-size="9">{html.escape(label)}</text>
          <text x="{kx + 14}" y="{ky + 44}" class="metric" font-size="19" fill="{color}">{html.escape(val)}</text>
          <text x="{kx + 14}" y="{ky + 59}" class="body" font-size="10.5">{html.escape(sub)}</text>
        </g>
        """)

    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <text x="32" y="36" class="label" fill="{PALETTE['accent_cyan']}">TELEMETRY · MONTHLY VELOCITY</text>
      <text x="32" y="58" class="title">Contributions per Month &amp; Consistency</text>
    </g>
    {''.join(bars_svg)}
    {''.join(kpi_svg)}
    """
    return card_frame(w, h, woff_uri, 0.44, inner)


# ---------------------------------------------------------------------------
# 4. Featured Repository Cards (cards/repo-*.svg)
# ---------------------------------------------------------------------------
def render_repo_card(repo: dict[str, Any], woff_uri: str) -> str:
    w, h = 840, 148
    # Build sparkline path
    pts = repo["sparkline"]
    sx, sy, sw, sh = 648, 42, 160, 44
    max_p = max(pts) or 1
    min_p = min(pts)
    span = max(max_p - min_p, 1)
    coords = []
    for i, val in enumerate(pts):
        px = sx + (i / (len(pts) - 1)) * sw
        py = sy + sh - ((val - min_p) / span) * sh
        coords.append(f"{px:.1f},{py:.1f}")
    poly = " ".join(coords)

    # Topic pills
    px_cursor = 32
    pills = []
    for t in repo["topics"]:
        pw = len(t) * 6.8 + 20
        pills.append(f"""
        <rect x="{px_cursor:.1f}" y="104" width="{pw:.1f}" height="22" rx="11" fill="{PALETTE['bg_pill']}" stroke="{PALETTE['border_subtle']}" />
        <text x="{px_cursor + pw / 2:.1f}" y="118.5" text-anchor="middle" class="label" font-size="9.5" fill="{PALETTE['text_secondary']}">{html.escape(t)}</text>
        """)
        px_cursor += pw + 8

    inner = f"""
    <g class="fade-up" style="--d: 0.06s">
      <circle cx="40" cy="34" r="5" fill="{repo['lang_color']}" />
      <text x="52" y="38" class="label" fill="{repo['lang_color']}">{html.escape(repo['language'])}</text>
      <text x="150" y="38" class="label">★ {html.escape(repo['stars'])}   ⑂ {html.escape(repo['forks'])}</text>
      <text x="32" y="64" class="title" font-size="19">{html.escape(repo['name'])}</text>
      <text x="32" y="88" class="body" font-size="13.5">{html.escape(repo['description'])}</text>
    </g>
    <g class="fade-up" style="--d: 0.12s">
      {''.join(pills)}
    </g>
    <g class="fade-up" style="--d: 0.16s">
      <text x="{sx + sw}" y="32" text-anchor="end" class="label" font-size="9.5">COMMIT PULSE (12W)</text>
      <polyline fill="none" stroke="url(#brandAccent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" points="{poly}" />
    </g>
    """
    return card_frame(w, h, woff_uri, repo["delay"], inner)


# ---------------------------------------------------------------------------
# 5. Brand-Coloured Contribution Graph (cards/contribution-graph.svg)
# ---------------------------------------------------------------------------
def heat_color(count: int) -> str:
    if count <= 0:
        return PALETTE["heat_0"]
    if count <= 2:
        return PALETTE["heat_1"]
    if count <= 5:
        return PALETTE["heat_2"]
    if count <= 9:
        return PALETTE["heat_3"]
    return PALETTE["heat_4"]


def render_contribution_graph(stats: dict[str, Any], woff_uri: str) -> str:
    w, h = 840, 188
    days = stats["days"][-371:]  # Up to 53 columns x 7 rows
    cell = 11
    gap = 3
    step = cell + gap
    grid_x = 36
    grid_y = 66

    cells_svg = []
    for idx, d in enumerate(days):
        col = idx // 7
        row = idx % 7
        cx = grid_x + col * step
        cy = grid_y + row * step
        color = heat_color(d["count"])
        cells_svg.append(
            f'<rect x="{cx}" y="{cy}" width="{cell}" height="{cell}" rx="2.8" fill="{color}" />'
        )

    # Legend on top-right
    legend_levels = [
        PALETTE["heat_0"],
        PALETTE["heat_1"],
        PALETTE["heat_2"],
        PALETTE["heat_3"],
        PALETTE["heat_4"],
    ]
    legend_rects = []
    lx0 = 716
    for i, c in enumerate(legend_levels):
        legend_rects.append(
            f'<rect x="{lx0 + i * 15}" y="30" width="11" height="11" rx="2.5" fill="{c}" />'
        )

    inner = f"""
    <g class="fade-up" style="--d: 0.06s">
      <text x="36" y="36" class="label" fill="{PALETTE['accent_cyan']}">CONTRIBUTION MATRIX · {stats['total']:,} COMMITS IN LAST YEAR</text>
      <text x="706" y="39" text-anchor="end" class="label" font-size="9.5">LESS</text>
      {''.join(legend_rects)}
      <text x="802" y="39" text-anchor="end" class="label" font-size="9.5">MORE</text>
    </g>
    <g class="fade-up" style="--d: 0.14s">
      {''.join(cells_svg)}
    </g>
    """
    return card_frame(w, h, woff_uri, 0.92, inner)


# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    stats = load_or_generate_contributions()

    # Collect all text used across cards for minimal WOFF subsetting
    corpus = json.dumps(PROFILE) + json.dumps(stats) + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789·↗★⑂●/&,-:()"
    woff_uri = build_subset_woff_data_uri(corpus)

    outputs = {
        "hero.svg": render_hero(woff_uri),
        "monthly-chart.svg": render_monthly_chart(stats, woff_uri),
        "contribution-graph.svg": render_contribution_graph(stats, woff_uri),
    }
    for tile in PROFILE["tiles"]:
        outputs[f"tile-{tile['slug']}.svg"] = render_tile(tile, woff_uri)
    for repo in PROFILE["repos"]:
        outputs[f"repo-{repo['slug']}.svg"] = render_repo_card(repo, woff_uri)

    for filename, svg_content in outputs.items():
        (CARDS_DIR / filename).write_text(svg_content.strip() + "\n", encoding="utf-8")
        print(f"Rendered cards/{filename} (STATIC={int(STATIC)})")


if __name__ == "__main__":
    main()