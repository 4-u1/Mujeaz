"""Generates the README illustrations in docs/assets/.

Run:  python3 docs/assets/build_svgs.py [path/to/shield.png]
All SVGs are self-contained (no external fonts or images) so they render on GitHub.
"""
import base64
import pathlib
import sys

OUT = pathlib.Path(__file__).parent

EN = "Inter, 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
AR = "'SF Arabic', 'Geeza Pro', 'Noto Kufi Arabic', 'Noto Sans Arabic', 'Segoe UI', Tahoma, 'DejaVu Sans', sans-serif"
MONO = "'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"

C = {
    "bg0": "#040C1A", "bg1": "#0A1D38", "card": "#0D1E36", "card2": "#0F2441", "line": "#1E3A5F",
    "text": "#E8EEF8", "muted": "#8EA4C2", "dim": "#5E7698",
    "cyan": "#22D3EE", "emerald": "#10B981", "gold": "#E2B861", "gold2": "#B8862F",
    "violet": "#A78BFA", "blue": "#60A5FA", "amber": "#F59E0B", "rose": "#FB7185",
}


def defs_common():
    return f"""
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{C['bg0']}"/><stop offset="1" stop-color="{C['bg1']}"/>
  </linearGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#F7DC9B"/><stop offset="0.55" stop-color="{C['gold']}"/><stop offset="1" stop-color="{C['gold2']}"/>
  </linearGradient>
  <linearGradient id="brand" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{C['cyan']}"/><stop offset="1" stop-color="{C['emerald']}"/>
  </linearGradient>
  <pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse">
    <path d="M36 0H0V36" fill="none" stroke="{C['cyan']}" stroke-opacity="0.06" stroke-width="1"/>
  </pattern>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
    <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000" flood-opacity="0.35"/>
  </filter>"""


def frame(w, h, body, extra_defs=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<defs>{defs_common()}{extra_defs}
</defs>
<rect width="{w}" height="{h}" rx="28" fill="url(#bg)"/>
<rect width="{w}" height="{h}" rx="28" fill="url(#grid)"/>
<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="27.5" fill="none" stroke="{C['line']}" stroke-opacity="0.8"/>
{body}
</svg>
"""


def title(x, y, en, ar, w):
    return f"""
<text x="{x}" y="{y}" font-family="{EN}" font-size="15" font-weight="700" letter-spacing="3" fill="{C['cyan']}">{en}</text>
<text x="{w - x}" y="{y}" text-anchor="start" direction="rtl" font-family="{AR}" font-size="18" font-weight="700" fill="{C['gold']}">{ar}</text>"""


# --------------------------------------------------------------------------- hero
def hero(shield_b64):
    w, h = 900, 520
    pills = [("Prevent", "منع"), ("Approve", "موافقة"), ("Monitor", "مراقبة"), ("Recover", "استرداد"), ("Learn", "تعلّم")]
    pill_w, gap, y0 = 148, 26, 412
    total = len(pills) * pill_w + (len(pills) - 1) * gap
    x = (w - total) / 2
    pill_svg = ""
    for i, (en, ar) in enumerate(pills):
        color = [C["cyan"], C["emerald"], C["blue"], C["gold"], C["violet"]][i]
        pill_svg += f"""
  <g>
    <rect x="{x}" y="{y0}" width="{pill_w}" height="66" rx="16" fill="{C['card']}" stroke="{color}" stroke-opacity="0.55"/>
    <circle cx="{x+20}" cy="{y0+33}" r="5" fill="{color}"><animate attributeName="opacity" values="1;0.3;1" dur="2.4s" begin="{i*0.35}s" repeatCount="indefinite"/></circle>
    <text x="{x+34}" y="{y0+30}" font-family="{EN}" font-size="18" font-weight="700" fill="{C['text']}">{en}</text>
    <text x="{x+34}" y="{y0+53}" font-family="{AR}" font-size="15" fill="{C['muted']}">{ar}</text>
  </g>"""
        if i < len(pills) - 1:
            ax = x + pill_w + 4
            pill_svg += f"""<path d="M{ax} {y0+33} h{gap-10}" stroke="{C['dim']}" stroke-width="2"/><path d="M{ax+gap-12} {y0+28} l6 5 -6 5" fill="none" stroke="{C['dim']}" stroke-width="2"/>"""
        x += pill_w + gap

    extra = f"""
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{C['cyan']}" stop-opacity="0.38"/><stop offset="1" stop-color="{C['cyan']}" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="shieldClip"><circle cx="705" cy="205" r="112"/></clipPath>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{C['cyan']}" stop-opacity="0"/><stop offset="0.5" stop-color="{C['cyan']}" stop-opacity="0.35"/><stop offset="1" stop-color="{C['cyan']}" stop-opacity="0"/>
  </linearGradient>"""

    body = f"""
<circle cx="705" cy="205" r="210" fill="url(#halo)"/>
<circle cx="705" cy="205" r="150" fill="none" stroke="{C['cyan']}" stroke-opacity="0.25" stroke-dasharray="4 10" stroke-width="2">
  <animateTransform attributeName="transform" type="rotate" from="0 705 205" to="360 705 205" dur="40s" repeatCount="indefinite"/>
</circle>
<circle cx="705" cy="205" r="128" fill="none" stroke="url(#brand)" stroke-opacity="0.7" stroke-width="2"/>
<image x="593" y="93" width="224" height="224" clip-path="url(#shieldClip)" href="data:image/png;base64,{shield_b64}" xlink:href="data:image/png;base64,{shield_b64}"/>
<rect x="593" y="93" width="224" height="40" fill="url(#scan)" clip-path="url(#shieldClip)">
  <animate attributeName="y" values="93;277;93" dur="5s" repeatCount="indefinite"/>
</rect>

<rect x="56" y="58" width="300" height="30" rx="15" fill="{C['cyan']}" fill-opacity="0.1" stroke="{C['cyan']}" stroke-opacity="0.4"/>
<text x="72" y="78" font-family="{EN}" font-size="13" font-weight="700" letter-spacing="2" fill="{C['cyan']}">AI · SAUDI HEALTHCARE · NPHIES-READY</text>

<text x="56" y="205" font-family="{AR}" font-size="104" font-weight="800" fill="url(#gold)" filter="url(#glow)">مُجاز</text>
<text x="60" y="262" font-family="{EN}" font-size="40" font-weight="800" letter-spacing="12" fill="{C['text']}">MUJEAZ</text>
<text x="60" y="300" font-family="{EN}" font-size="19" fill="{C['muted']}">Revenue Assurance &amp; Prior-Authorization</text>
<text x="60" y="326" font-family="{EN}" font-size="19" fill="{C['muted']}">Command Center</text>
<text x="60" y="368" text-anchor="end" direction="rtl" font-family="{AR}" font-size="21" font-weight="700" fill="{C['emerald']}">نمنع الرفض. نحمي الإيراد. نستعيد المفقود.</text>
{pill_svg}
"""
    return frame(w, h, body, extra)


# --------------------------------------------------------------------------- agents
def agents():
    w, h = 900, 860
    items = [
        ("A1", "Clinical Understanding", "وكيل الفهم السريري", ["Free-text notes → structured facts", "every fact linked to its source"], C["cyan"]),
        ("A2", "Evidence Hunter", "وكيل صيد الأدلة", ["Searches the whole patient record", "for proof each requirement is met"], C["emerald"]),
        ("A3", "Policy Reasoning", "وكيل تحليل السياسات", ["RAG over payer policy text +", "deterministic, testable rules"], C["violet"]),
        ("A4", "NPHIES / FHIR Conformance", "وكيل التوافق مع نفيس", ["Builds the FHIR R4 Claim", "(use: preauthorization) &amp; checks it"], C["blue"]),
        ("A5", "Revenue Risk", "وكيل مخاطر الإيراد", ["Readiness Score, denial risk,", "revenue at risk, priority"], C["amber"]),
        ("A6", "Recovery", "وكيل الاسترداد", ["Root cause → evidence map →", "bilingual appeal for review"], C["rose"]),
    ]
    cw, ch, gx, gy, x0, y0 = 390, 180, 40, 40, 40, 120
    body = title(40, 60, "SIX SPECIALISED AGENTS", "ستة وكلاء متخصصون", w)
    body += f"""<text x="40" y="94" font-family="{EN}" font-size="22" font-weight="700" fill="{C['text']}">One traceable pipeline — from clinical order to recovered revenue</text>"""
    pos = []
    for i, (aid, en, ar, lines, col) in enumerate(items):
        r, c = divmod(i, 2)
        x = x0 + c * (cw + gx)
        y = y0 + r * (ch + gy)
        pos.append((x, y))
        core = ""
        if aid == "A2":
            core = f"""<rect x="{x+cw-96}" y="{y+18}" width="78" height="24" rx="12" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-opacity="0.6"/>
<text x="{x+cw-57}" y="{y+35}" text-anchor="middle" font-family="{EN}" font-size="12" font-weight="800" letter-spacing="1.5" fill="{col}">CORE</text>"""
        body += f"""
<g filter="url(#shadow)">
  <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="20" fill="{C['card']}" stroke="{col}" stroke-opacity="0.45"/>
  <rect x="{x}" y="{y}" width="6" height="{ch}" rx="3" fill="{col}"/>
</g>
<circle cx="{x+46}" cy="{y+48}" r="26" fill="{col}" fill-opacity="0.14" stroke="{col}" stroke-width="2"/>
<text x="{x+46}" y="{y+55}" text-anchor="middle" font-family="{MONO}" font-size="18" font-weight="800" fill="{col}">{aid}</text>
<text x="{x+86}" y="{y+45}" font-family="{EN}" font-size="20" font-weight="800" fill="{C['text']}">{en}</text>
<text x="{x+86}" y="{y+70}" font-family="{AR}" font-size="16" fill="{C['gold']}">{ar}</text>
<text x="{x+26}" y="{y+120}" font-family="{EN}" font-size="16" fill="{C['muted']}">{lines[0]}</text>
<text x="{x+26}" y="{y+144}" font-family="{EN}" font-size="16" fill="{C['muted']}">{lines[1]}</text>
{core}"""
    # connectors: row-wise snake A1→A2, A2→A3 (down-left), A3→A4, A4→A5, A5→A6
    def arrow_h(y, x1, x2):
        return f"""<path d="M{x1} {y} H{x2-8}" stroke="{C['dim']}" stroke-width="2.5"/><path d="M{x2-12} {y-6} l8 6 -8 6" fill="none" stroke="{C['dim']}" stroke-width="2.5"/>"""
    for r in range(3):
        yy = y0 + r * (ch + gy) + ch / 2
        body += arrow_h(yy, x0 + cw + 4, x0 + cw + gx + 2)
    for r in range(2):
        ya = y0 + r * (ch + gy) + ch
        xa, xb = x0 + cw + gx + cw / 2, x0 + cw / 2
        body += f"""<path d="M{xa} {ya+4} V{ya+gy/2} H{xb} V{ya+gy-6}" fill="none" stroke="{C['dim']}" stroke-width="2.5" stroke-dasharray="6 6"/>
<path d="M{xb-6} {ya+gy-10} l6 8 6 -8" fill="none" stroke="{C['dim']}" stroke-width="2.5"/>"""
    yb = y0 + 3 * (ch + gy) - 6
    body += f"""
<rect x="40" y="{yb}" width="820" height="72" rx="18" fill="{C['gold']}" fill-opacity="0.08" stroke="{C['gold']}" stroke-opacity="0.5"/>
<text x="64" y="{yb+31}" font-family="{EN}" font-size="17" font-weight="800" fill="{C['gold']}">HUMAN-IN-THE-LOOP</text>
<text x="64" y="{yb+55}" font-family="{EN}" font-size="15" fill="{C['muted']}">Nothing is submitted or appealed without an authorised reviewer.</text>
<text x="836" y="{yb+31}" text-anchor="end" font-family="{EN}" font-size="17" font-weight="800" fill="{C['emerald']}">NO EVIDENCE, NO CLAIM</text>
<text x="836" y="{yb+55}" text-anchor="end" font-family="{AR}" font-size="16" fill="{C['muted']}">لا دليل = لا ادعاء</text>"""
    return frame(w, h, body)


# --------------------------------------------------------------------------- readiness
def readiness():
    w, h = 900, 560
    comps = [("Clinical Evidence", "30%", 98), ("Policy Match", "25%", 96), ("Documentation", "15%", 97),
             ("Coding Integrity", "15%", 100), ("Required Attachments", "10%", 99), ("Administrative", "5%", 100)]
    score = round(sum(v * float(wt[:-1]) / 100 for _, wt, v in comps))
    import math
    cx, cy, r = 190, 300, 120
    circ = 2 * math.pi * r
    arc = circ * score / 100
    body = title(40, 60, "MUJEAZ READINESS SCORE", "مؤشر جاهزية مُجاز", w)
    body += f"""<text x="40" y="94" font-family="{EN}" font-size="22" font-weight="700" fill="{C['text']}">Measures how ready a request is — not whether it will be approved</text>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C['line']}" stroke-width="22"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#brand)" stroke-width="22" stroke-linecap="round"
  stroke-dasharray="{arc:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})" filter="url(#glow)">
  <animate attributeName="stroke-dasharray" from="0 {circ:.1f}" to="{arc:.1f} {circ:.1f}" dur="1.6s" fill="freeze"/>
</circle>
<text x="{cx}" y="{cy+18}" text-anchor="middle" font-family="{EN}" font-size="76" font-weight="800" fill="{C['text']}">{score}</text>
<text x="{cx}" y="{cy+50}" text-anchor="middle" font-family="{EN}" font-size="18" fill="{C['muted']}">/ 100</text>
<rect x="{cx-92}" y="{cy+r+30}" width="184" height="36" rx="18" fill="{C['emerald']}" fill-opacity="0.15" stroke="{C['emerald']}"/>
<text x="{cx}" y="{cy+r+54}" text-anchor="middle" font-family="{EN}" font-size="16" font-weight="800" fill="{C['emerald']}">DECISION READY</text>
"""
    bx, by, bw = 400, 140, 440
    for i, (name, wt, v) in enumerate(comps):
        y = by + i * 54
        body += f"""
<text x="{bx}" y="{y}" font-family="{EN}" font-size="17" font-weight="700" fill="{C['text']}">{name}</text>
<text x="{bx+bw-60}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="14" fill="{C['dim']}">w {wt}</text>
<text x="{bx+bw}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="17" font-weight="800" fill="{C['cyan']}">{v}</text>
<rect x="{bx}" y="{y+12}" width="{bw}" height="10" rx="5" fill="{C['line']}"/>
<rect x="{bx}" y="{y+12}" width="{bw*v/100:.1f}" height="10" rx="5" fill="url(#brand)">
  <animate attributeName="width" from="0" to="{bw*v/100:.1f}" dur="1.2s" begin="{0.15*i:.2f}s" fill="freeze"/>
</rect>"""
    body += f"""
<rect x="{bx}" y="470" width="{bw}" height="58" rx="14" fill="{C['rose']}" fill-opacity="0.08" stroke="{C['rose']}" stroke-opacity="0.45"/>
<text x="{bx+18}" y="494" font-family="{EN}" font-size="15" font-weight="800" fill="{C['rose']}">HARD GATES</text>
<text x="{bx+18}" y="516" font-family="{EN}" font-size="14" fill="{C['muted']}">Failed mandatory rule → max 60 · Invalid coding → max 50</text>"""
    return frame(w, h, body)


# --------------------------------------------------------------------------- before / after
def twin():
    w, h = 900, 600
    body = title(40, 60, "EVIDENCE HUNTER IN ACTION", "صيد الأدلة قبل الإرسال", w)
    body += f"""<text x="40" y="94" font-family="{EN}" font-size="22" font-weight="700" fill="{C['text']}">MRI Lumbar Spine · AUTH-2026-4922 · demo case</text>"""

    def card(x, col, tag, ready, risk, atrisk, ev_status, ev_line1, ev_line2):
        return f"""
<g filter="url(#shadow)"><rect x="{x}" y="128" width="360" height="430" rx="22" fill="{C['card']}" stroke="{col}" stroke-opacity="0.55"/></g>
<rect x="{x+24}" y="150" width="{len(tag)*11+28}" height="30" rx="15" fill="{col}" fill-opacity="0.14" stroke="{col}" stroke-opacity="0.6"/>
<text x="{x+38}" y="171" font-family="{EN}" font-size="14" font-weight="800" letter-spacing="2" fill="{col}">{tag}</text>
<text x="{x+24}" y="232" font-family="{EN}" font-size="15" fill="{C['muted']}">Readiness Score</text>
<text x="{x+336}" y="236" text-anchor="end" font-family="{EN}" font-size="40" font-weight="800" fill="{col}">{ready}</text>
<line x1="{x+24}" y1="256" x2="{x+336}" y2="256" stroke="{C['line']}"/>
<text x="{x+24}" y="292" font-family="{EN}" font-size="15" fill="{C['muted']}">Denial risk</text>
<text x="{x+336}" y="294" text-anchor="end" font-family="{EN}" font-size="28" font-weight="800" fill="{C['text']}">{risk}</text>
<text x="{x+24}" y="336" font-family="{EN}" font-size="15" fill="{C['muted']}">Revenue at risk</text>
<text x="{x+336}" y="338" text-anchor="end" font-family="{EN}" font-size="28" font-weight="800" fill="{C['text']}">{atrisk}</text>
<line x1="{x+24}" y1="362" x2="{x+336}" y2="362" stroke="{C['line']}"/>
<text x="{x+24}" y="396" font-family="{EN}" font-size="15" fill="{C['muted']}">Conservative therapy (6 weeks)</text>
<rect x="{x+24}" y="412" width="{len(ev_status)*12+26}" height="30" rx="8" fill="{col}" fill-opacity="0.15"/>
<text x="{x+37}" y="433" font-family="{MONO}" font-size="15" font-weight="800" fill="{col}">{ev_status}</text>
<text x="{x+24}" y="476" font-family="{EN}" font-size="15" fill="{C['text']}">{ev_line1}</text>
<text x="{x+24}" y="502" font-family="{MONO}" font-size="13" fill="{C['dim']}">{ev_line2}</text>"""

    body += card(40, C["rose"], "BEFORE", "74", "78%", "2,184 SAR", "MISSING", "Not explicit in the current request", "source: —")
    body += card(500, C["emerald"], "AFTER", "98", "5%", "140 SAR", "FOUND", "6 physiotherapy sessions + NSAID", "Encounter #1820 · 2026-06-11 · 97%")
    body += f"""
<circle cx="450" cy="340" r="34" fill="{C['bg0']}" stroke="url(#brand)" stroke-width="3"/>
<text x="450" y="348" text-anchor="middle" font-family="{MONO}" font-size="20" font-weight="800" fill="{C['emerald']}">A2</text>
<path d="M404 340 H418" stroke="{C['emerald']}" stroke-width="3"/><path d="M484 340 H496" stroke="{C['emerald']}" stroke-width="3"/>
<path d="M490 333 l8 7 -8 7" fill="none" stroke="{C['emerald']}" stroke-width="3"/>
<text x="450" y="586" text-anchor="middle" font-family="{EN}" font-size="13" fill="{C['dim']}">Illustrative demo data · service value 2,800 SAR · risk heuristic per PRD §8</text>"""
    return frame(w, h, body)


# --------------------------------------------------------------------------- architecture
def architecture():
    w, h = 900, 700
    body = title(40, 60, "ARCHITECTURE", "المعمارية", w)
    body += f"""<text x="40" y="94" font-family="{EN}" font-size="22" font-weight="700" fill="{C['text']}">Prototype today → production target</text>"""

    def box(x, y, bw, bh, col, head, lines, dashed=False):
        dash = ' stroke-dasharray="7 6"' if dashed else ""
        s = f"""<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="16" fill="{C['card']}" stroke="{col}" stroke-opacity="0.6"{dash}/>
<text x="{x+20}" y="{y+32}" font-family="{EN}" font-size="17" font-weight="800" fill="{col}">{head}</text>"""
        for i, ln in enumerate(lines):
            s += f"""<text x="{x+20}" y="{y+58+i*23}" font-family="{EN}" font-size="15" fill="{C['muted']}">{ln}</text>"""
        return s

    def down(x, y1, y2):
        return f"""<path d="M{x} {y1} V{y2-8}" stroke="{C['dim']}" stroke-width="2.5"/><path d="M{x-6} {y2-12} l6 8 6 -8" fill="none" stroke="{C['dim']}" stroke-width="2.5"/>"""

    lx, rx, bw = 40, 470, 390
    body += f"""<text x="{lx}" y="140" font-family="{EN}" font-size="14" font-weight="800" letter-spacing="2" fill="{C['emerald']}">● PROTOTYPE — IN THIS REPO</text>
<text x="{rx}" y="140" font-family="{EN}" font-size="14" font-weight="800" letter-spacing="2" fill="{C['gold']}">◌ PRODUCTION TARGET — PRD §9</text>"""
    body += box(lx, 158, bw, 112, C["cyan"], "Web app", ["React 19 · Vite · Tailwind v4", "Arabic RTL-first · 6 workspaces"])
    body += down(lx + bw / 2, 272, 302)
    body += box(lx, 302, bw, 136, C["blue"], "Express API", ["/api/ai/analyze-order", "/api/ai/generate-appeal", "validation · rate limit · minimised data"])
    body += down(lx + bw / 2, 440, 470)
    body += box(lx, 470, bw, 112, C["emerald"], "AI + scoring", ["Gemini · structured JSON output", "shared/scoring.ts (deterministic)"])
    body += box(rx, 158, bw, 112, C["gold"], "Clients &amp; integrations", ["Next.js · HIS / EMR (FHIR, HL7v2)", "NPHIES gateway (after accreditation)"], True)
    body += down(rx + bw / 2, 272, 302)
    body += box(rx, 302, bw, 136, C["gold"], "FastAPI services", ["Orchestrator · agents A1–A6", "rules engine · FHIR validator", "hash-chained audit service"], True)
    body += down(rx + bw / 2, 440, 470)
    body += box(rx, 470, bw, 112, C["gold"], "Data", ["PostgreSQL + RLS per facility", "pgvector · policy versions"], True)
    body += f"""
<rect x="40" y="606" width="820" height="62" rx="16" fill="{C['violet']}" fill-opacity="0.08" stroke="{C['violet']}" stroke-opacity="0.45"/>
<text x="62" y="633" font-family="{EN}" font-size="15" font-weight="800" fill="{C['violet']}">Cross-cutting</text>
<text x="62" y="655" font-family="{EN}" font-size="14" fill="{C['muted']}">PDPL · CHI · NCA · in-Kingdom hosting · RBAC · encryption · human review · AI evaluation in CI</text>"""
    return frame(w, h, body)


def main():
    shield = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "shield.png"
    b64 = base64.b64encode(shield.read_bytes()).decode()
    files = {"hero.svg": hero(b64), "agents.svg": agents(), "readiness.svg": readiness(),
             "evidence-hunter.svg": twin(), "architecture.svg": architecture()}
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")
        print(name, len(svg) // 1024, "KB")


if __name__ == "__main__":
    main()
