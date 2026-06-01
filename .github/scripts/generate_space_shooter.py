import os
import random
import requests
from datetime import datetime

USERNAME = os.environ.get("GITHUB_USERNAME", "your-username")
OUTPUT_PATH = "dist/space-shooter-dark.svg"
os.makedirs("dist", exist_ok=True)

def fetch_contributions(username):
    url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("contributions", [])
    except Exception as e:
        print(f"Warning: Could not fetch contributions: {e}")
        return []

contributions = fetch_contributions(USERNAME)

COLS = 53
ROWS = 7
CELL = 14
GAP  = 3
STEP = CELL + GAP

grid = [[0] * COLS for _ in range(ROWS)]
for entry in contributions:
    date    = datetime.strptime(entry["date"], "%Y-%m-%d")
    dow_svg = (date.weekday() + 1) % 7
    level   = entry.get("level", 0)
    today   = datetime.today()
    delta   = (today - date).days
    if delta < 0 or delta > 53 * 7:
        continue
    col = COLS - 1 - (delta // 7)
    row = dow_svg
    if 0 <= col < COLS and 0 <= row < ROWS:
        grid[row][col] = level

COLORS = {0:"#161b22", 1:"#2d1b4d", 2:"#4b2e83", 3:"#6e44c1", 4:"#9b72cf"}

MARGIN_LEFT = 32
MARGIN_TOP  = 28
GRID_W = COLS * STEP
GRID_H = ROWS * STEP
SVG_W  = MARGIN_LEFT + GRID_W + 60
SVG_H  = MARGIN_TOP  + GRID_H + 80

# Ship travels along the BOTTOM of the grid
SHIP_Y = MARGIN_TOP + GRID_H + 32

# The ship's X at time T:  ship_x(T) = SHIP_START_X + (SHIP_END_X - SHIP_START_X) * T / TOTAL_DUR
# We want the laser to fire when ship_x == col_center_x
# col_center_x = MARGIN_LEFT + col * STEP + CELL/2
# So fire_time = (col_center_x - SHIP_START_X) / (SHIP_END_X - SHIP_START_X) * TOTAL_DUR

SHIP_START_X = float(MARGIN_LEFT - 30)
SHIP_END_X   = float(MARGIN_LEFT + GRID_W + 20)
SHIP_TRAVEL  = SHIP_END_X - SHIP_START_X

# Give a small pause at end before looping so dots can "respawn"
TRAVEL_DUR = COLS * 0.17   # time ship is actually moving
PAUSE_DUR  = 1.5           # pause at end before restart
TOTAL_DUR  = TRAVEL_DUR + PAUSE_DUR

parts = []   # collect all SVG elements

# ── Stars ──────────────────────────────────────────────────────────────────
random.seed(42)
for _ in range(80):
    sx    = random.randint(0, SVG_W)
    sy    = random.randint(0, SVG_H - 40)
    sr    = random.choice([0.5, 0.8, 1.0])
    delay = round(random.uniform(0, 2), 2)
    parts.append(
        f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="white" opacity="0.4">'
        f'<animate attributeName="opacity" values="0.4;1;0.4" dur="2s" begin="{delay}s" repeatCount="indefinite"/>'
        f'</circle>'
    )

# ── Day labels ──────────────────────────────────────────────────────────────
DOW_LABELS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
for i, label in enumerate(DOW_LABELS):
    if i % 2 == 1:
        ly = MARGIN_TOP + i * STEP + CELL / 2 + 4
        parts.append(
            f'<text x="{MARGIN_LEFT-6}" y="{ly:.1f}" font-size="9" fill="#8b949e" '
            f'text-anchor="end" font-family="monospace">{label}</text>'
        )

# ── Dots + lasers + explosions ──────────────────────────────────────────────
for col in range(COLS):
    col_cx = MARGIN_LEFT + col * STEP + CELL / 2   # center x of this column

    # Exact time the ship nose is at col_cx
    ship_arrive = (col_cx - SHIP_START_X) / SHIP_TRAVEL * TRAVEL_DUR

    for row in range(ROWS):
        level = grid[row][col]
        rx = MARGIN_LEFT + col * STEP
        ry = MARGIN_TOP  + row * STEP
        dot_cy = ry + CELL / 2
        color  = COLORS[level]

        # ── dot (always draw, even level-0 as background cell) ──
        dot_id = f"d{row}_{col}"
        parts.append(
            f'<rect id="{dot_id}" x="{rx}" y="{ry}" width="{CELL}" height="{CELL}" '
            f'rx="2" fill="{color}"/>'
        )

        if level == 0:
            continue   # no laser/explosion for empty cells

        # Fire time: ship arrives at column, then tiny per-row stagger so
        # it looks like one sweep rather than all rows at once
        fire_t  = ship_arrive + row * 0.018   # seconds into the loop
        laser_d = 0.10    # laser visible duration (s)
        fade_d  = 0.12    # dot fade duration (s)
        exp_d   = 0.18    # explosion duration (s)

        # All keyTimes are fractions of TOTAL_DUR
        def kt(t): return min(max(t / TOTAL_DUR, 0.0001), 0.9999)

        ft  = kt(fire_t)
        flt = kt(fire_t + laser_d)
        fdt = kt(fire_t + fade_d)
        fet = kt(fire_t + exp_d)
        # "reset" point — just before loop end, dots pop back
        rst = 0.9999

        # ── dot fade: visible → shot → gone → reappear at reset ──
        parts.append(
            f'<animate xlink:href="#{dot_id}" attributeName="opacity" '
            f'values="1;1;0;0;1" '
            f'keyTimes="0;{ft:.4f};{fdt:.4f};{rst};1" '
            f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
        )

        # ── laser beam ──
        parts.append(
            f'<line x1="{col_cx:.1f}" y1="{SHIP_Y}" x2="{col_cx:.1f}" y2="{dot_cy:.1f}" '
            f'stroke="#00f2ff" stroke-width="1.5" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;0;0" '
            f'keyTimes="0;{ft:.4f};{kt(fire_t+laser_d*0.4):.4f};{flt:.4f};1" '
            f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
            f'</line>'
        )

        # ── explosion particles ──
        for dx, dy, pr in [(-5,-5,2),(5,-5,2),(0,-8,1.5),(-8,0,1.5),(8,0,1.5)]:
            ex, ey = col_cx + dx, dot_cy + dy
            parts.append(
                f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{pr}" fill="#9b72cf" opacity="0">'
                f'<animate attributeName="opacity" values="0;0;1;0;0" '
                f'keyTimes="0;{ft:.4f};{kt(fire_t+exp_d*0.4):.4f};{fet:.4f};1" '
                f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
                f'<animate attributeName="r" values="{pr};{pr};{pr*2.5:.1f};0;{pr}" '
                f'keyTimes="0;{ft:.4f};{kt(fire_t+exp_d*0.5):.4f};{fet:.4f};1" '
                f'dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>'
                f'</circle>'
            )

# ── Ship ────────────────────────────────────────────────────────────────────
# Ship moves only during TRAVEL_DUR, then snaps back (we hide it during pause)
# We use two animations: translateX and opacity
travel_frac = TRAVEL_DUR / TOTAL_DUR

parts.append(f'''
<g transform="translate(0 {SHIP_Y})">
  <g>
    <!-- Move ship across during travel phase, snap back at loop end -->
    <animateTransform attributeName="transform" type="translate"
      values="{SHIP_START_X} 0;{SHIP_END_X} 0;{SHIP_START_X} 0"
      keyTimes="0;{travel_frac:.4f};1"
      dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="linear"/>
    <!-- Hide ship during snap-back pause -->
    <animate attributeName="opacity"
      values="1;1;0;0;1"
      keyTimes="0;{travel_frac:.4f};{travel_frac+0.001:.4f};0.9999;1"
      dur="{TOTAL_DUR:.3f}s" repeatCount="indefinite" calcMode="discrete"/>

    <!-- Body -->
    <rect x="-6" y="-10" width="12" height="16" rx="2" fill="#00f2ff"/>
    <!-- Cockpit -->
    <rect x="-3" y="-14" width="6" height="7" rx="2" fill="#ffffff" opacity="0.85"/>
    <!-- Left wing -->
    <polygon points="-6,-2 -16,6 -6,6" fill="#6e44c1"/>
    <!-- Right wing -->
    <polygon points="6,-2 16,6 6,6" fill="#6e44c1"/>
    <!-- Engine glow -->
    <ellipse cx="0" cy="7" rx="4" ry="3" fill="#ff6600" opacity="0.9">
      <animate attributeName="ry" values="3;5;3" dur="0.2s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.9;0.6;0.9" dur="0.2s" repeatCount="indefinite"/>
    </ellipse>
    <ellipse cx="0" cy="10" rx="2" ry="4" fill="#ffaa00" opacity="0.7">
      <animate attributeName="ry" values="4;6;4" dur="0.15s" repeatCount="indefinite"/>
    </ellipse>
  </g>
</g>
''')

# ── Assemble ─────────────────────────────────────────────────────────────────
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">
  <rect width="{SVG_W}" height="{SVG_H}" fill="#0d1117" rx="8"/>
  {"".join(parts)}
</svg>'''

with open(OUTPUT_PATH, "w") as f:
    f.write(svg)

print(f"Generated {OUTPUT_PATH}  {SVG_W}x{SVG_H}px  loop={TOTAL_DUR:.2f}s  (travel={TRAVEL_DUR:.2f}s + pause={PAUSE_DUR:.2f}s)")
