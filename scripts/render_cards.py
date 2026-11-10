#!/usr/bin/env python3
"""
Renders crafted, unsloped SVG cards for sahil-kumar-ai's GitHub README.
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

ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = ROOT / "cards"
DATA_FILE = ROOT / "data" / "contributions.json"
FONTS_DIR = ROOT / "assets" / "fonts"

STATIC = os.environ.get("STATIC", "0") == "1"
PORTRAIT_PATH = os.environ.get("PORTRAIT_PATH", "")

# Unslop Palette: Deep graphite neutrals, one accent for data.
PALETTE = {
    "bg_canvas": "#0A0A0A",
    "bg_card": "#121212",
    "bg_pill": "#1C1C1C",
    "text_primary": "#F4F4F5",
    "text_secondary": "#A1A1AA",
    "text_muted": "#52525B",
    "border_subtle": "#27272A",
    "accent_main": "#38BDF8", 
    # Heatmap Ramp
    "heat_0": "#1C1C1C",
    "heat_1": "#0C4A6E",
    "heat_2": "#0284C7",
    "heat_3": "#38BDF8",
    "heat_4": "#BAE6FD",
}

PROFILE = {
    "name": "Sahil Kumar",
    "handle": "sahil-kumar-ai",
    "tagline": "Building autonomous AI systems, scalable infrastructure, and human-agent interfaces.",
    "status": "Shipping multi-agent orchestrators",
    "location": "San Francisco / Remote",
    "tiles": [
        {"slug": "portfolio", "title": "Live apps & web", "subtitle": "sahilkumar.ai", "delay": 0.16},
        {"slug": "models", "title": "Open models", "subtitle": "GitHub / HF", "delay": 0.24},
        {"slug": "linkedin", "title": "LinkedIn", "subtitle": "in/sahil-kumar-ai", "delay": 0.32},
    ],
    "repos": [
        {
            "slug": "agentic-core",
            "name": "agentic-core",
            "description": "Deterministic orchestrator for multi-agent LLM systems with DAG state recovery and zero-copy streaming.",
            "language": "Python",
            "stars": "1.4k",
            "forks": "182",
            "sparkline": [12, 18, 15, 26, 32, 29, 41, 38, 52, 48, 61, 68],
            "delay": 0.62,
        },
        {
            "slug": "vision-stream",
            "name": "vision-stream-pipeline",
            "description": "Sub-15ms real-time edge video inference pipeline using TensorRT and async WebRTC frame queues.",
            "language": "Python / C++",
            "stars": "890",
            "forks": "94",
            "sparkline": [8, 14, 19, 17, 25, 31, 28, 35, 42, 39, 49, 55],
            "delay": 0.76,
        },
    ],
}

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
    font_path = ensure_source_font()
    if not font_path or not font_path.exists():
        return ""
    unique_chars = "".join(sorted(set(text_corpus)))
    with tempfile.TemporaryDirectory() as tmpdir:
        out_woff = Path(tmpdir) / "subset.woff"
        cmd = ["pyftsubset", str(font_path), f"--text={unique_chars}", "--flavor=woff", f"--output-file={out_woff}", "--layout-features=kern,liga,calt,tnum"]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"data:font/woff;base64,{base64.b64encode(out_woff.read_bytes()).decode('ascii')}"
        except Exception:
            return ""

def load_or_generate_contributions() -> dict[str, Any]:
    if DATA_FILE.exists():
        return compute_stats(json.loads(DATA_FILE.read_text(encoding="utf-8")))

    today = dt.date.today()
    start_date = today - dt.timedelta(days=364)
    start_date -= dt.timedelta(days=(start_date.weekday() + 1) % 7)
    days = []
    cur = start_date
    idx = 0
    while cur <= today:
        wave = ((idx * 17 + cur.month * 13) % 19)
        count = max(0, wave + (0 if cur.weekday() in (5, 6) else 3) - 6)
        if idx % 11 == 0: count = 0
        days.append({"date": cur.isoformat(), "count": count})
        cur += dt.timedelta(days=1)
        idx += 1
    return compute_stats({"user": "sahil-kumar-ai", "days": days})

def compute_stats(payload: dict[str, Any]) -> dict[str, Any]:
    days = sorted(payload.get("days", []), key=lambda d: d["date"])
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"] > 0)
    
    monthly_map = {}
    for d in days:
        ym = d["date"][:7]
        monthly_map[ym] = monthly_map.get(ym, 0) + d["count"]
    months = [{"ym": ym, "label": dt.date(int(ym.split("-")[0]), int(ym.split("-")[1]), 1).strftime("%b"), "count": cnt} for ym, cnt in sorted(monthly_map.items())[-12:]]
    
    return {"days": days, "total": total, "active_days": active, "months": months}

def shared_style_and_defs(woff_uri: str, base_delay: float = 0.0) -> str:
    font_face = f"@font-face {{ font-family: 'BrandSans'; src: url('{woff_uri}') format('woff'); font-weight: 100 900; font-display: block; }}" if woff_uri else ""
    
    # Apple-style critically damped entry, no looping or bouncing.
    motion_css = """
    .card-enter, .fade-up { opacity: 1 !important; transform: none !important; }
    """ if STATIC else f"""
    @keyframes fadeUp {{ 0% {{ opacity: 0; transform: translateY(8px); }} 100% {{ opacity: 1; transform: translateY(0); }} }}
    .card-enter {{ opacity: 0; animation: fadeUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) {base_delay:.2f}s forwards; }}
    .fade-up {{ opacity: 0; animation: fadeUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) calc({base_delay:.2f}s + var(--d, 0.1s)) forwards; }}
    """

    return f"""
  <style>
    {font_face}
    .root {{ font-family: 'BrandSans', system-ui, sans-serif; -webkit-font-smoothing: antialiased; fill: {PALETTE['text_primary']}; }}
    .display {{ font-size: 24px; font-weight: 600; letter-spacing: -0.02em; }}
    .title {{ font-size: 15px; font-weight: 500; }}
    .body {{ font-size: 14px; font-weight: 400; fill: {PALETTE['text_secondary']}; }}
    .label {{ font-size: 13px; font-weight: 400; fill: {PALETTE['text_muted']}; }}
    .metric {{ font-size: 20px; font-weight: 500; font-variant-numeric: tabular-nums; }}
    {motion_css}
    @media (prefers-reduced-motion: reduce) {{ .card-enter, .fade-up {{ opacity: 1 !important; transform: none !important; animation: none !important; }} }}
  </style>
"""

def card_frame(width: int, height: int, woff_uri: str, base_delay: float, inner_svg: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" class="root" role="img">
  {shared_style_and_defs(woff_uri, base_delay)}
  <rect width="{width}" height="{height}" fill="{PALETTE['bg_canvas']}" />
  <g class="card-enter">
    <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="16" fill="{PALETTE['bg_card']}" stroke="{PALETTE['border_subtle']}" stroke-width="1" />
    {inner_svg}
  </g>
</svg>"""

def render_hero(woff_uri: str) -> str:
    # Removed the spinning emblem. Just clean, quiet initials if no portrait.
    portrait = f'<circle cx="756" cy="72" r="48" fill="{PALETTE["bg_pill"]}" stroke="{PALETTE["border_subtle"]}" /><text x="756" y="78" text-anchor="middle" class="title" fill="{PALETTE["text_muted"]}">SK</text>'
    
    if PORTRAIT_PATH and Path(PORTRAIT_PATH).exists():
        p = Path(PORTRAIT_PATH)
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        portrait = f'<clipPath id="pClip"><circle cx="756" cy="72" r="48" /></clipPath><image href="data:image/png;base64,{b64}" x="708" y="24" width="96" height="96" clip-path="url(#pClip)" />'

    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <text x="32" y="64" class="display">{html.escape(PROFILE['name'])}</text>
      <text x="32" y="90" class="body">{html.escape(PROFILE['tagline'])}</text>
    </g>
    <g class="fade-up" style="--d: 0.10s">
      <rect x="32" y="112" width="8" height="8" rx="4" fill="{PALETTE['text_muted']}" />
      <text x="48" y="121" class="label">{html.escape(PROFILE['status'])}</text>
    </g>
    <g class="fade-up" style="--d: 0.15s">{portrait}</g>
    """
    return card_frame(840, 144, woff_uri, 0.0, inner)

def render_tile(tile: dict[str, Any], woff_uri: str) -> str:
    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <text x="24" y="44" class="title">{html.escape(tile['title'])}</text>
      <text x="24" y="66" class="body">{html.escape(tile['subtitle'])}</text>
      <path d="M 236 40 L 244 32 M 236 32 H 244 V 40" fill="none" stroke="{PALETTE['text_muted']}" stroke-width="1.5" />
    </g>
    """
    return card_frame(272, 96, woff_uri, tile["delay"], inner)

def render_monthly_chart(stats: dict[str, Any], woff_uri: str) -> str:
    months = stats["months"]
    max_val = max((m["count"] for m in months), default=1) or 1
    bars_svg = []
    
    for idx, m in enumerate(months):
        bh = max(4.0, round((m["count"] / max_val) * 80, 1))
        bx = 32 + idx * 38
        by = 132 - bh
        bars_svg.append(f"""
        <g class="fade-up" style="--d: {0.1 + idx * 0.02}s">
          <rect x="{bx}" y="{by}" width="24" height="{bh}" rx="2" fill="{PALETTE['accent_main']}" opacity="0.9" />
          <text x="{bx + 12}" y="156" text-anchor="middle" class="label" font-size="11">{html.escape(m['label'])}</text>
        </g>
        """)

    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <text x="32" y="40" class="title">Contributions</text>
      <text x="540" y="40" class="title">Active days</text>
      <text x="690" y="40" class="title">Annual output</text>
      
      <text x="540" y="72" class="metric">{stats['active_days']}</text>
      <text x="690" y="72" class="metric">{stats['total']:,}</text>
    </g>
    {''.join(bars_svg)}
    """
    return card_frame(840, 184, woff_uri, 0.44, inner)

def render_repo_card(repo: dict[str, Any], woff_uri: str) -> str:
    pts = repo["sparkline"]
    min_p, span = min(pts), max(max(pts) - min(pts), 1)
    coords = " ".join([f"{648 + (i / 11) * 160:.1f},{86 - ((val - min_p) / span) * 44:.1f}" for i, val in enumerate(pts)])

    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <text x="24" y="40" class="title">{html.escape(repo['name'])}</text>
      <text x="24" y="66" class="body">{html.escape(repo['description'])}</text>
      <text x="24" y="104" class="label">{html.escape(repo['language'])}   ·   {html.escape(repo['stars'])} stars</text>
    </g>
    <g class="fade-up" style="--d: 0.15s">
      <text x="648" y="32" class="label">12-week activity</text>
      <polyline fill="none" stroke="{PALETTE['accent_main']}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="{coords}" />
    </g>
    """
    return card_frame(840, 132, woff_uri, repo["delay"], inner)

def render_contribution_graph(stats: dict[str, Any], woff_uri: str) -> str:
    cells_svg = []
    for idx, d in enumerate(stats["days"][-371:]):
        c = d["count"]
        color = PALETTE["heat_0"] if c <= 0 else PALETTE["heat_1"] if c <= 2 else PALETTE["heat_2"] if c <= 5 else PALETTE["heat_3"] if c <= 9 else PALETTE["heat_4"]
        cells_svg.append(f'<rect x="{32 + (idx // 7) * 14}" y="{64 + (idx % 7) * 14}" width="10" height="10" rx="2" fill="{color}" />')

    inner = f"""
    <g class="fade-up" style="--d: 0.05s">
      <text x="32" y="40" class="title">{stats['total']:,} contributions in the last year</text>
    </g>
    <g class="fade-up" style="--d: 0.1s">
      {''.join(cells_svg)}
    </g>
    """
    return card_frame(840, 188, woff_uri, 0.92, inner)

def main() -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    stats = load_or_generate_contributions()
    corpus = json.dumps(PROFILE) + json.dumps(stats) + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789·/"
    woff_uri = build_subset_woff_data_uri(corpus)

    outputs = {
        "hero.svg": render_hero(woff_uri),
        "monthly-chart.svg": render_monthly_chart(stats, woff_uri),
        "contribution-graph.svg": render_contribution_graph(stats, woff_uri),
    }
    for t in PROFILE["tiles"]: outputs[f"tile-{t['slug']}.svg"] = render_tile(t, woff_uri)
    for r in PROFILE["repos"]: outputs[f"repo-{r['slug']}.svg"] = render_repo_card(r, woff_uri)

    for name, svg in outputs.items():
        (CARDS_DIR / name).write_text(svg.strip() + "\n", encoding="utf-8")
        print(f"Rendered cards/{name}")

if __name__ == "__main__":
    main()