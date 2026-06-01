import os, random, requests
from datetime import datetime

USERNAME    = os.environ.get("GITHUB_USERNAME", "your-username")
OUTPUT_PATH = "dist/space-shooter-dark.svg"
os.makedirs("dist", exist_ok=True)

# ── Fetch contributions via GitHub GraphQL (needs GITHUB_TOKEN in workflow) ──
def fetch_contributions(username):
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        query = """
        {
          user(login: "%s") {
            contributionsCollection {
              contributionCalendar {
                weeks {
                  contributionDays {
                    date
                    contributionCount
                  }
                }
              }
            }
          }
        }
        """ % username
        try:
            r = requests.post(
                "https://api.github.com/graphql",
                json={"query": query},
                headers={"Authorization": f"bearer {token}"},
                timeout=10
            )
            r.raise_for_status()
            weeks = (r.json()["data"]["user"]["contributionsCollection"]
                               ["contributionCalendar"]["weeks"])
            out = []
            for week in weeks:
                for day in week["contributionDays"]:
                    c = day["contributionCount"]
                    level = 0 if c==0 else 1 if c<=2 else 2 if c<=5 else 3 if c<=9 else 4
                    out.append({"date": day["date"], "level": level, "count": c})
            print(f"Fetched {len([x for x in out if x['level']>0])} active days via GraphQL")
            return out
        except Exception as e:
            print(f"GraphQL fetch failed: {e}")

    # Fallback: public contributions API
    try:
        r = requests.get(
            f"https://github-contributions-api.jogruber.de/v4/{username}?y=last",
            timeout=10)
        r.raise_for_status()
        data = r.json().get("contributions", [])
        print(f"Fetched {len([x for x in data if x.get('level',0)>0])} active days via public API")
        return data
    except Exception as e:
        print(f"Public API also failed: {e}")
        return []

contributions = fetch_contributions(USERNAME)

# ── Build grid ───────────────────────────────────────────────────────────────
COLS=53; ROWS=7; CELL=14; GAP=3; STEP=CELL+GAP
grid = [[0]*COLS for _ in range(ROWS)]

for entry in contributions:
    try:
        date    = datetime.strptime(entry["date"], "%Y-%m-%d")
        dow_svg = (date.weekday() + 1) % 7   # Sun=0 … Sat=6
        level   = entry.get("level", 0)
        today   = datetime.today()
        delta   = (today - date).days
        if delta < 0 or delta > 53*7:
            continue
        col = COLS - 1 - (delta // 7)
        row = dow_svg
        if 0 <= col < COLS and 0 <= row < ROWS:
            grid[row][col] = level
    except:
        pass

total_dots = sum(1 for c in range(COLS) for r in range(ROWS) if grid[r][c]>0)
print(f"Grid has {total_dots} active dots")

COLORS = {0:"#161b22",1:"#2d1b4d",2:"#4b2e83",3:"#6e44c1",4:"#9b72cf"}

# ── Layout ───────────────────────────────────────────────────────────────────
ML=32; MT=28
GRID_W = COLS*STEP; GRID_H = ROWS*STEP
SVG_W  = ML + GRID_W + 60
SVG_H  = MT + GRID_H + 80

# Ship Y = below grid
SHIP_Y = MT + GRID_H + 30

# Ship travels from left edge to right edge
SX0 = float(ML - 40)          # start X
SX1 = float(ML + GRID_W + 30) # end X
SPAN = SX1 - SX0

# Timing: ship takes TRAVEL_DUR to cross, then RESET_DUR pause (dots reset + ship hidden)
TRAVEL_DUR = COLS * 0.16     # ~8.5 s
RESET_DUR  = 0.8             # short pause
TOTAL_DUR  = TRAVEL_DUR + RESET_DUR

def pct(t):
    """Clamp t (seconds) to a keyTimes fraction string."""
    return f"{min(max(t/TOTAL_DUR, 0.0001), 0.9998):.5f}"

parts = []

# ── Background ───────────────────────────────────────────────────────────────
random.seed(99)
for _ in range(90):
    sx=random.randint(0,SVG_W); sy=random.randint(0,SVG_H-30)
    sr=random.choice([0.5,0.8,1.0]); delay=round(random.uniform(0,3),2)
    parts.append(
        f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="white" opacity="0.35">'
        f'<animate attributeName="opacity" values="0.35;0.9;0.35" '
        f'dur="{round(random.uniform(1.5,3.5),1)}s" begin="{delay}s" repeatCount="indefinite"/>'
        f'</circle>'
    )

# ── Day labels ───────────────────────────────────────────────────────────────
for i, lbl in enumerate(["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]):
    if i % 2 == 1:
        ly = MT + i*STEP + CELL/2 + 4
        parts.append(
            f'<text x="{ML-6}" y="{ly:.1f}" font-size="9" fill="#8b949e" '
            f'text-anchor="end" font-family="monospace">{lbl}</text>'
        )

# ── Dots, lasers, explosions ─────────────────────────────────────────────────
for col in range(COLS):
    cx = ML + col*STEP + CELL/2   # column center X

    # Time when ship center is exactly at cx
    # ship_x(t) = SX0 + SPAN * t/TRAVEL_DUR  →  t = (cx-SX0)/SPAN * TRAVEL_DUR
    arrive = (cx - SX0) / SPAN * TRAVEL_DUR

    for row in range(ROWS):
        level = grid[row][col]
        rx = ML + col*STEP
        ry = MT + row*STEP

        # Draw dot (all cells including empty for background grid look)
        did = f"d{row}_{col}"
        parts.append(
            f'<rect id="{did}" x="{rx}" y="{ry}" width="{CELL}" height="{CELL}" '
            f'rx="2" fill="{COLORS[level]}"/>'
        )

        if level == 0:
            continue

        # Stagger rows by 15ms so lasers don't all fire simultaneously
        ft = arrive + row * 0.015

        # Dot: visible → instant vanish at ft → stay gone → reappear just before loop end
        parts.append(
            f'<animate xlink:href="#{did}" attributeName="opacity" '
            f'values="1;1;0;0;1" '
            f'keyTimes="0;{pct(ft)};{pct(ft+0.05)};{pct(TOTAL_DUR-0.05)};1" '
            f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
        )

        dot_cy = ry + CELL/2

        # Laser: flash up from ship to dot at exact fire time
        LD = 0.08   # laser duration
        parts.append(
            f'<line x1="{cx:.1f}" y1="{SHIP_Y}" x2="{cx:.1f}" y2="{dot_cy:.1f}" '
            f'stroke="#00f2ff" stroke-width="1.5" opacity="0">'
            f'<animate attributeName="opacity" '
            f'values="0;0;1;0;0" '
            f'keyTimes="0;{pct(ft)};{pct(ft+LD*0.3)};{pct(ft+LD)};1" '
            f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
            f'</line>'
        )

        # Explosion
        ED = 0.20
        for dx,dy,pr in [(-4,-4,2),(4,-4,2),(0,-7,1.5),(-7,0,1.5),(7,0,1.5),(0,4,1)]:
            ex,ey = cx+dx, dot_cy+dy
            parts.append(
                f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{pr}" fill="#c084fc" opacity="0">'
                f'<animate attributeName="opacity" values="0;0;1;0;0" '
                f'keyTimes="0;{pct(ft)};{pct(ft+ED*0.3)};{pct(ft+ED)};1" '
                f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
                f'<animate attributeName="r" values="{pr};{pr};{pr*3:.1f};0;{pr}" '
                f'keyTimes="0;{pct(ft)};{pct(ft+ED*0.5)};{pct(ft+ED)};1" '
                f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
                f'</circle>'
            )

# ── Ship ─────────────────────────────────────────────────────────────────────
# Key fix: ship is a single <g> at y=SHIP_Y with ONE animateTransform (additive=sum)
# that animates only the X translation. No nested transforms.
tf = TRAVEL_DUR / TOTAL_DUR  # fraction when travel ends

parts.append(f'''
<g id="ship-group">
  <!-- X motion across grid, then snap back hidden -->
  <animateTransform attributeName="transform" type="translate"
    values="{SX0:.1f},{SHIP_Y};{SX1:.1f},{SHIP_Y};{SX0:.1f},{SHIP_Y}"
    keyTimes="0;{tf:.5f};1"
    dur="{TOTAL_DUR:.3f}s"
    repeatCount="indefinite"
    calcMode="linear"/>
  <!-- Hide during snap-back -->
  <animate attributeName="opacity"
    values="1;1;0;0;1"
    keyTimes="0;{tf:.5f};{tf+0.0001:.5f};0.9999;1"
    dur="{TOTAL_DUR:.3f}s"
    repeatCount="indefinite"
    calcMode="discrete"/>

  <!-- Body -->
  <rect x="-6" y="-10" width="12" height="16" rx="2" fill="#00f2ff"/>
  <!-- Cockpit -->
  <rect x="-3" y="-14" width="6" height="7" rx="2" fill="#e0f7ff" opacity="0.9"/>
  <!-- Wings -->
  <polygon points="-6,-2 -18,8 -6,8" fill="#7c3aed"/>
  <polygon points="6,-2 18,8 6,8" fill="#7c3aed"/>
  <!-- Wing accent -->
  <polygon points="-6,2 -14,8 -6,8" fill="#a855f7" opacity="0.6"/>
  <polygon points="6,2 14,8 6,8" fill="#a855f7" opacity="0.6"/>
  <!-- Engine -->
  <ellipse cx="0" cy="8" rx="4" ry="3" fill="#f97316">
    <animate attributeName="ry" values="3;6;3" dur="0.18s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.6;1" dur="0.18s" repeatCount="indefinite"/>
  </ellipse>
  <ellipse cx="0" cy="12" rx="2" ry="5" fill="#fbbf24" opacity="0.7">
    <animate attributeName="ry" values="5;8;5" dur="0.13s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.7;0.3;0.7" dur="0.13s" repeatCount="indefinite"/>
  </ellipse>
  <!-- Gun tip (where laser fires from) -->
  <rect x="-1" y="-16" width="2" height="4" rx="1" fill="#00f2ff"/>
</g>
''')

# ── Write SVG ────────────────────────────────────────────────────────────────
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">
  <rect width="{SVG_W}" height="{SVG_H}" fill="#0d1117" rx="8"/>
  {"".join(parts)}
</svg>'''

with open(OUTPUT_PATH, "w") as f:
    f.write(svg)

print(f"Done → {OUTPUT_PATH}  {SVG_W}×{SVG_H}  loop={TOTAL_DUR:.2f}s")
