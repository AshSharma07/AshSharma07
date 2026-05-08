import os
import random
import requests
from datetime import datetime
 
USERNAME = os.environ.get("GITHUB_USERNAME", "your-username")
OUTPUT_PATH = "dist/space-shooter-dark.svg"
os.makedirs("dist", exist_ok=True)
 
# Fetch contribution data
def fetch_contributions(username):
    url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("contributions", [])
    except Exception as e:
        print(f"Warning: Could not fetch contributions: {e}")
        return []
 
contributions = fetch_contributions(USERNAME)
 
# Build a 7-row x 53-col grid (standard GitHub style)
COLS = 53
ROWS = 7
CELL = 14
GAP = 3
STEP = CELL + GAP
 
grid = [[0] * COLS for _ in range(ROWS)]
 
for entry in contributions:
    date = datetime.strptime(entry["date"], "%Y-%m-%d")
    dow = date.weekday()
    dow_svg = (dow + 1) % 7  # GitHub grid: Sun=0
    level = entry.get("level", 0)
 
    today = datetime.today()
    delta = (today - date).days
    if delta < 0 or delta > 53 * 7:
        continue
    col = COLS - 1 - (delta // 7)
    row = dow_svg
    if 0 <= col < COLS and 0 <= row < ROWS:
        grid[row][col] = level
 
# Color scheme
COLORS = {
    0: "#161b22",
    1: "#2d1b4d",
    2: "#4b2e83",
    3: "#6e44c1",
    4: "#9b72cf",
}
 
# SVG dimensions
MARGIN_LEFT = 32
MARGIN_TOP = 28
GRID_W = COLS * STEP
GRID_H = ROWS * STEP
SVG_W = MARGIN_LEFT + GRID_W + 60
SVG_H = MARGIN_TOP + GRID_H + 80
 
SHIP_START_X = MARGIN_LEFT - 30
SHIP_END_X = MARGIN_LEFT + GRID_W + 20
SHIP_Y = MARGIN_TOP + GRID_H + 32
 
# Total animation duration
TOTAL_DUR = COLS * 0.18
COL_DUR = 0.18
 
# ── Dot elements ──────────────────────────────────────────────────────────────
dot_elements = []
dot_anims = []
 
for col in range(COLS):
    col_time = col * COL_DUR
    for row in range(ROWS):
        level = grid[row][col]
        if level == 0:
            continue
        rx = MARGIN_LEFT + col * STEP
        ry = MARGIN_TOP + row * STEP
        dot_id = f"d{row}_{col}"
        color = COLORS[level]
 
        dot_elements.append(
            f'<rect id="{dot_id}" x="{rx}" y="{ry}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>'
        )
 
        shoot_time = col_time + row * 0.025
        # Keyframe percentages within the total loop duration
        t0 = max(shoot_time / TOTAL_DUR, 0)
        t1 = min((shoot_time + 0.15) / TOTAL_DUR, 0.999)
        # Dot is visible → fades out at shoot_time → stays invisible → reappears at loop end
        dot_anims.append(
            f'<animate xlink:href="#{dot_id}" attributeName="opacity" '
            f'values="1;1;0;0;1" '
            f'keyTimes="0;{t0:.4f};{t1:.4f};0.9999;1" '
            f'dur="{TOTAL_DUR:.2f}s" '
            f'repeatCount="indefinite" '
            f'calcMode="discrete"/>'
        )
 
# ── Laser elements ────────────────────────────────────────────────────────────
laser_elements = []
 
for col in range(COLS):
    col_time = col * COL_DUR
    col_x = MARGIN_LEFT + col * STEP + CELL / 2
    for row in range(ROWS):
        level = grid[row][col]
        if level == 0:
            continue
        ry = MARGIN_TOP + row * STEP
        laser_id = f"l{row}_{col}"
        laser_y1 = SHIP_Y
        laser_y2 = ry + CELL / 2
 
        shoot_time = col_time + row * 0.025
        t0 = max(shoot_time / TOTAL_DUR, 0)
        tmid = min((shoot_time + 0.06) / TOTAL_DUR, 0.999)
        t1 = min((shoot_time + 0.12) / TOTAL_DUR, 0.999)
 
        laser_elements.append(
            f'<line id="{laser_id}" x1="{col_x:.1f}" y1="{laser_y1}" '
            f'x2="{col_x:.1f}" y2="{laser_y2:.1f}" '
            f'stroke="#00f2ff" stroke-width="1.5" opacity="0">'
            f'<animate attributeName="opacity" '
            f'values="0;0;1;0;0" '
            f'keyTimes="0;{t0:.4f};{tmid:.4f};{t1:.4f};1" '
            f'dur="{TOTAL_DUR:.2f}s" repeatCount="indefinite" calcMode="linear"/>'
            f'</line>'
        )
 
# ── Explosion particles ───────────────────────────────────────────────────────
explosion_elements = []
 
for col in range(COLS):
    col_time = col * COL_DUR
    col_x = MARGIN_LEFT + col * STEP + CELL / 2
    for row in range(ROWS):
        level = grid[row][col]
        if level == 0:
            continue
        ry = MARGIN_TOP + row * STEP + CELL / 2
        shoot_time = col_time + row * 0.025
 
        t0 = max(shoot_time / TOTAL_DUR, 0)
        tmid = min((shoot_time + 0.10) / TOTAL_DUR, 0.999)
        t1 = min((shoot_time + 0.20) / TOTAL_DUR, 0.999)
 
        for dx, dy, r in [(-5, -5, 2), (5, -5, 2), (0, -8, 1.5), (-8, 0, 1.5), (8, 0, 1.5)]:
            ex, ey = col_x + dx, ry + dy
            explosion_elements.append(
                f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{r}" fill="#9b72cf" opacity="0">'
                f'<animate attributeName="opacity" '
                f'values="0;0;1;0;0" '
                f'keyTimes="0;{t0:.4f};{tmid:.4f};{t1:.4f};1" '
                f'dur="{TOTAL_DUR:.2f}s" repeatCount="indefinite" calcMode="linear"/>'
                f'<animate attributeName="r" '
                f'values="{r};{r};{r*2.5:.1f};0;{r}" '
                f'keyTimes="0;{t0:.4f};{tmid:.4f};{t1:.4f};1" '
                f'dur="{TOTAL_DUR:.2f}s" repeatCount="indefinite" calcMode="linear"/>'
                f'</circle>'
            )
 
# ── Ship ──────────────────────────────────────────────────────────────────────
ship_anim = f'''<animateTransform
  attributeName="transform"
  type="translate"
  from="{SHIP_START_X} 0"
  to="{SHIP_END_X} 0"
  dur="{TOTAL_DUR:.2f}s"
  repeatCount="indefinite"
  restart="always"/>'''
 
ship_svg = f'''<g id="ship">
  {ship_anim}
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
</g>'''
 
# ── Stars ─────────────────────────────────────────────────────────────────────
random.seed(42)
stars = []
for _ in range(80):
    sx = random.randint(0, SVG_W)
    sy = random.randint(0, SVG_H - 40)
    sr = random.choice([0.5, 0.8, 1.0])
    delay = round(random.uniform(0, 2), 2)
    stars.append(
        f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="white" opacity="0.5">'
        f'<animate attributeName="opacity" values="0.5;1;0.5" dur="2s" begin="{delay}s" repeatCount="indefinite"/>'
        f'</circle>'
    )
 
# ── Day-of-week labels ────────────────────────────────────────────────────────
DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
dow_label_els = []
for i, label in enumerate(DOW_LABELS):
    if i % 2 == 1:
        ly = MARGIN_TOP + i * STEP + CELL / 2 + 4
        dow_label_els.append(
            f'<text x="{MARGIN_LEFT - 6}" y="{ly:.1f}" font-size="9" fill="#8b949e" '
            f'text-anchor="end" font-family="monospace">{label}</text>'
        )
 
# ── Assemble SVG ──────────────────────────────────────────────────────────────
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">
 
  <!-- Background -->
  <rect width="{SVG_W}" height="{SVG_H}" fill="#0d1117" rx="8"/>
 
  <!-- Stars -->
  {"".join(stars)}
 
  <!-- Day labels -->
  {"".join(dow_label_els)}
 
  <!-- Contribution dots -->
  {"".join(dot_elements)}
 
  <!-- Lasers -->
  {"".join(laser_elements)}
 
  <!-- Explosions -->
  {"".join(explosion_elements)}
 
  <!-- Dot loop animations -->
  {"".join(dot_anims)}
 
  <!-- Spaceship -->
  <g transform="translate(0 {SHIP_Y})">
    {ship_svg}
  </g>
 
</svg>'''
 
with open(OUTPUT_PATH, "w") as f:
    f.write(svg)
 
print(f"Generated {OUTPUT_PATH} ({SVG_W}x{SVG_H}px, {TOTAL_DUR:.1f}s loop)")
