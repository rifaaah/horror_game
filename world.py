"""Cemetery world data – positions, sizes, colours.
Rendering is done by the renderer in main.py."""
import random, math

random.seed(42)   # reproducible layout

BOUNDARY = 50.0

class GraveData:
    def __init__(self, x, z, height, tilt, width):
        self.x, self.z = x, z
        self.height    = height
        self.tilt      = tilt
        self.width     = width

class TreeData:
    def __init__(self, x, z, height, branches):
        self.x, self.z   = x, z
        self.height      = height
        self.branches    = branches  # list of (bx,bz,by,length)

class PedestalData:
    def __init__(self, x, z, index, color_key):
        self.x, self.z  = x, z
        self.index      = index
        self.color_key  = color_key  # 'cyan'|'magenta'|'yellow'
        self.solved     = False

class HintSign:
    def __init__(self, x, z, text):
        self.x, self.z = x, z
        self.text      = text

def _scatter(count, radius, cx_ex=8, cz_ex=8, min_d=4):
    pts = []
    tries = 0
    while len(pts) < count and tries < 2000:
        tries += 1
        x = random.uniform(-radius, radius)
        z = random.uniform(-radius, radius)
        if abs(x) < cx_ex and abs(z) < cz_ex:
            continue
        if any(math.sqrt((x-px)**2+(z-pz)**2) < min_d for px,pz in pts):
            continue
        pts.append((x, z))
    return pts

def build_world():
    graves   = []
    trees    = []
    pedestals = [
        PedestalData(-20, -20, 0, 'cyan'),
        PedestalData( 20, -15, 1, 'magenta'),
        PedestalData(  0,  25, 2, 'yellow'),
    ]
    hints = [
        HintSign(-25, -25, "Code: 3791"),
        HintSign( 25, -20, "Code: 4862"),
        HintSign(  5,  30, "Code: 5047"),
    ]

    for x, z in _scatter(40, 44, min_d=3):
        graves.append(GraveData(
            x, z,
            height  = random.uniform(1.2, 2.2),
            tilt    = random.uniform(-10, 10),
            width   = random.uniform(0.5, 0.8),
        ))

    for x, z in _scatter(20, 48, min_d=6):
        branches = []
        h = random.uniform(3, 6)
        for _ in range(random.randint(3, 6)):
            bx = random.uniform(-1.5, 1.5)
            bz = random.uniform(-1.5, 1.5)
            by = random.uniform(h*0.5, h)
            bl = random.uniform(0.8, 2.5)
            branches.append((bx, bz, by, bl))
        trees.append(TreeData(x, z, h, branches))

    return graves, trees, pedestals, hints

GRAVES, TREES, PEDESTALS, HINTS = build_world()

GHOST_SPAWNS = [
    (-30, 10), (25, -30), (-15, 35), (38, 5)
]

GATE_POS = (0, 50)   # x, z — north edge
