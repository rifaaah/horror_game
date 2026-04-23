"""
╔══════════════════════════════════════════════════════════╗
║          CEMETERY ESCAPE  —  3D Horror Survival          ║
║              Requires only:  pip install pygame          ║
╠══════════════════════════════════════════════════════════╣
║  WASD / Arrows  – Move                                   ║
║  Mouse          – Look                                   ║
║  E              – Interact with pedestal                 ║
║  1/2/3          – Use ability (Speed/Invisible/Freeze)   ║
║  ESC            – Quit                                   ║
║  During puzzle: 1-4 for memory, 0-9+Backspace for code  ║
╚══════════════════════════════════════════════════════════╝
"""
import pygame, sys, math, random, time, os

# ── Optional: silence pygame welcome message ──
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from player import Player
from ghost  import Ghost
from world  import GRAVES, TREES, PEDESTALS, HINTS, GATE_POS, BOUNDARY
from puzzle import MemoryPuzzle, CodePuzzle
from ai     import GhostState

# ═══════════════════════════════════════════════════════════════════════════ #
#  Constants
# ═══════════════════════════════════════════════════════════════════════════ #
W, H       = 1280, 720
HALF_W     = W // 2
HALF_H     = H // 2
FOV        = math.radians(75)
NEAR       = 0.3
FAR        = 60.0
INTERACT_D = 4.5
CAMERA_H   = 1.7   # player eye height

# Fog parameters
FOG_START  = 8.0
FOG_END    = 45.0
SKY_COLOR  = (4, 6, 12)

# ═══════════════════════════════════════════════════════════════════════════ #
#  Software 3D Renderer (Raycaster + Billboard Sprites)
# ═══════════════════════════════════════════════════════════════════════════ #
class Renderer:
    """Minimal software 3D renderer using pygame surfaces."""

    def __init__(self, surf):
        self.surf      = surf
        self.w, self.h = surf.get_size()
        self.half_w    = self.w // 2
        self.half_h    = self.h // 2
        # depth buffer
        self.z_buf     = [FAR] * self.w

    def begin_frame(self):
        self.surf.fill(SKY_COLOR)
        # Ground plane (simple gradient)
        ground_surf = pygame.Surface((self.w, self.h // 2))
        for y in range(self.h // 2):
            t = y / (self.h // 2)
            r = int(8 + t * 14)
            g = int(10 + t * 18)
            b = int(6 + t * 10)
            pygame.draw.line(ground_surf, (r, g, b), (0, y), (self.w, y))
        self.surf.blit(ground_surf, (0, self.h // 2))
        self.z_buf = [FAR] * self.w

    def _project(self, wx, wy, wz, cam_x, cam_z, cam_yaw, cam_pitch=0.0):
        """World → screen. Returns (sx, sy, depth) or None if behind."""
        dx = wx - cam_x
        dz = wz - cam_z
        # rotate into camera space
        cos_y, sin_y = math.cos(-cam_yaw), math.sin(-cam_yaw)
        rx =  cos_y * dx - sin_y * dz
        rz =  sin_y * dx + cos_y * dz   # depth (forward)
        ry =  wy - CAMERA_H             # vertical offset

        if rz < NEAR:
            return None
        scale = (self.half_w / math.tan(FOV / 2)) / rz
        sx = int(self.half_w + rx * scale)
        sy = int(self.half_h - ry * scale)
        return sx, sy, rz

    def _fog(self, color, depth):
        t = max(0.0, min(1.0, (depth - FOG_START) / (FOG_END - FOG_START)))
        fr, fg, fb = SKY_COLOR
        r = int(color[0] * (1-t) + fr * t)
        g = int(color[1] * (1-t) + fg * t)
        b = int(color[2] * (1-t) + fb * t)
        return (r, g, b)

    # ── Draw a world-space box ────────────────────────────────────────────
    def draw_box(self, cx, cy, cz, sx, sy, sz,
                 cam_x, cam_z, cam_yaw, color_top, color_side,
                 tilt_deg=0):
        """Draw a simplified billboard box (front face only for perf)."""
        # 8 corners
        corners_local = [
            (-sx/2, -sy/2, -sz/2), ( sx/2, -sy/2, -sz/2),
            ( sx/2,  sy/2, -sz/2), (-sx/2,  sy/2, -sz/2),
            (-sx/2, -sy/2,  sz/2), ( sx/2, -sy/2,  sz/2),
            ( sx/2,  sy/2,  sz/2), (-sx/2,  sy/2,  sz/2),
        ]
        faces = [
            ([4,5,6,7], color_top),    # top face
            ([0,1,2,3], color_side),   # front
            ([5,1,2,6], color_side),   # right
            ([4,0,3,7], color_side),   # left
            ([4,5,1,0], (max(0,color_side[0]-20), max(0,color_side[1]-20), max(0,color_side[2]-20))),  # bottom
        ]
        tilt = math.radians(tilt_deg)
        projected = []
        depths = []
        for lx, ly, lz in corners_local:
            # apply tilt (rotate around z)
            rx2 = lx * math.cos(tilt) - ly * math.sin(tilt)
            ry2 = lx * math.sin(tilt) + ly * math.cos(tilt)
            wx = cx + rx2
            wy = cy + ry2
            wz = cz + lz
            p = self._project(wx, wy, wz, cam_x, cam_z, cam_yaw)
            projected.append(p)
            depths.append(p[2] if p else FAR)

        avg_depth = sum(depths) / len(depths)

        for indices, fcol in faces:
            pts = [projected[i] for i in indices if projected[i]]
            if len(pts) < 3:
                continue
            screen_pts = [(p[0], p[1]) for p in pts]
            fogged = self._fog(fcol, avg_depth)
            try:
                pygame.draw.polygon(self.surf, fogged, screen_pts)
            except Exception:
                pass

    # ── Draw a cylinder (simplified as octagon prism) ─────────────────────
    def draw_cylinder(self, cx, cy, cz, radius, height,
                      cam_x, cam_z, cam_yaw, color, segments=6):
        angles = [math.pi*2*i/segments for i in range(segments)]
        # draw side quads
        for i in range(segments):
            a0, a1 = angles[i], angles[(i+1)%segments]
            for ya, yb in [(cy, cy+height)]:
                pts = []
                for a, y in [(a0, ya),(a1, ya),(a1, yb),(a0, yb)]:
                    wx = cx + math.cos(a)*radius
                    wz = cz + math.sin(a)*radius
                    p  = self._project(wx, y, wz, cam_x, cam_z, cam_yaw)
                    pts.append(p)
                valid = [p for p in pts if p]
                if len(valid) < 3:
                    continue
                dep = sum(p[2] for p in valid)/len(valid)
                fogged = self._fog(color, dep)
                try:
                    pygame.draw.polygon(self.surf, fogged,
                                        [(p[0],p[1]) for p in valid])
                except Exception:
                    pass

    # ── Draw a billboard sprite (always faces camera) ─────────────────────
    def draw_sprite(self, wx, wy, wz, width, height,
                    cam_x, cam_z, cam_yaw, color, alpha=200, shape='ellipse'):
        p = self._project(wx, wy + height/2, wz, cam_x, cam_z, cam_yaw)
        if not p:
            return
        sx, sy, depth = p
        if depth > FAR:
            return
        scale = (self.half_w / math.tan(FOV/2)) / depth
        pw    = max(2, int(width  * scale))
        ph    = max(2, int(height * scale))

        fogged = self._fog(color, depth)

        # Create small surface for the sprite
        spr = pygame.Surface((pw, ph), pygame.SRCALPHA)
        if shape == 'ellipse':
            pygame.draw.ellipse(spr, (*fogged, alpha), (0, 0, pw, ph))
        else:
            spr.fill((*fogged, alpha))

        self.surf.blit(spr, (sx - pw//2, sy - ph//2))
        return depth   # return depth for z-sorting

    # ── Draw a line in 3D ─────────────────────────────────────────────────
    def draw_line3d(self, x1,y1,z1, x2,y2,z2,
                    cam_x, cam_z, cam_yaw, color, width=1):
        p1 = self._project(x1,y1,z1, cam_x, cam_z, cam_yaw)
        p2 = self._project(x2,y2,z2, cam_x, cam_z, cam_yaw)
        if not p1 or not p2:
            return
        dep = (p1[2]+p2[2])/2
        fogged = self._fog(color, dep)
        try:
            pygame.draw.line(self.surf, fogged,
                             (p1[0],p1[1]),(p2[0],p2[1]), width)
        except Exception:
            pass

    # ── Text in 3D space (billboard) ─────────────────────────────────────
    def draw_text3d(self, text, wx, wy, wz, cam_x, cam_z, cam_yaw,
                    font, color=(255,255,80)):
        p = self._project(wx, wy, wz, cam_x, cam_z, cam_yaw)
        if not p:
            return
        sx, sy, depth = p
        if depth > 30 or depth < NEAR:
            return
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(sx, sy))
        self.surf.blit(surf, rect)


# ═══════════════════════════════════════════════════════════════════════════ #
#  Main Game Class
# ═══════════════════════════════════════════════════════════════════════════ #
class Game:
    STATE_PLAY    = 'play'
    STATE_PUZZLE  = 'puzzle'
    STATE_DEAD    = 'dead'
    STATE_WIN     = 'win'

    def __init__(self):
        pygame.init()
        pygame.display.set_caption('Cemetery Escape')
        self.screen   = pygame.display.set_mode((W, H))
        self.clock    = pygame.time.Clock()
        self.renderer = Renderer(self.screen)

        # Fonts
        self.font_lg  = pygame.font.SysFont('consolas', 32, bold=True)
        self.font_md  = pygame.font.SysFont('consolas', 22)
        self.font_sm  = pygame.font.SysFont('consolas', 16)
        self.font_xl  = pygame.font.SysFont('consolas', 56, bold=True)

        # Mouse capture
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

        self._init_game()

    def _init_game(self):
        self.player   = Player()
        self.cam_yaw  = 0.0    # horizontal look angle (radians)
        self.cam_pitch= 0.0    # unused in projection but stored

        self.ghosts   = [
            Ghost(x, z, ghost_id=i, personality=round(0.7+i*0.2,1))
            for i,(x,z) in enumerate([(- 30,10),(25,-30),(-15,35),(38,5)])
        ]

        self.pedestals   = PEDESTALS     # from world.py (shared)
        self.solved      = [False]*3
        self.active_puz  = None
        self.gate_open   = False
        self.state       = self.STATE_PLAY

        self.notif_msg   = '👻 Solve 3 puzzles and reach the EXIT gate!'
        self.notif_col   = (100, 220, 255)
        self.notif_timer = 5.0

        self.safe_ring_rot = 0.0
        self.t = 0.0
        self.prev_time = time.time()

        # Flicker lights state
        self.flicker = [random.uniform(0, math.pi*2) for _ in range(6)]

    # ── Puzzle callbacks ──────────────────────────────────────────────────
    def _on_success(self, idx, reward):
        self.solved[idx] = True
        self.pedestals[idx].solved = True
        self.player.in_safe = False
        self.player.unlock(reward)
        self.active_puz = None
        self.state = self.STATE_PLAY
        self._notify(f'✓ {reward.upper()} UNLOCKED! Press {["1","2","3"][["speed","invisible","freeze"].index(reward)]} to use', (60,255,100))
        if all(self.solved):
            self.gate_open = True
            self._notify('🚪 All puzzles solved! Reach the EXIT GATE at the north!', (255,200,40), 6.0)

    def _on_failure(self, idx):
        self.player.in_safe = False
        self.player.take_damage(30)
        # spawn extra ghost
        angle = random.uniform(0, math.pi*2)
        ex = Ghost(self.player.x + math.cos(angle)*5,
                   self.player.z + math.sin(angle)*5,
                   ghost_id=random.randint(0,3),
                   personality=random.uniform(0.9,1.4))
        self.ghosts.append(ex)
        self.active_puz = None
        self.state = self.STATE_PLAY
        self._notify('✗ Wrong! A ghost appeared!', (255, 60, 60))

    def _notify(self, msg, col=(255,255,255), dur=3.0):
        self.notif_msg   = msg
        self.notif_col   = col
        self.notif_timer = dur

    # ── Main loop ─────────────────────────────────────────────────────────
    def run(self):
        while True:
            now = time.time()
            dt  = min(now - self.prev_time, 0.05)
            self.prev_time = now
            self.t += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                self._handle_event(event, dt)

            self._update(dt)
            self._render()
            pygame.display.flip()
            self.clock.tick(60)

    # ── Event handling ────────────────────────────────────────────────────
    def _handle_event(self, event, dt):
        if event.type == pygame.MOUSEMOTION and self.state == self.STATE_PLAY:
            dx, dy = event.rel
            self.cam_yaw   += dx * 0.002
            self.cam_pitch  = max(-0.4, min(0.4, self.cam_pitch - dy*0.002))

        if event.type == pygame.KEYDOWN:
            k = pygame.key.name(event.key)

            # Quit / restart
            if event.key == pygame.K_ESCAPE:
                if self.state in (self.STATE_DEAD, self.STATE_WIN):
                    pygame.quit(); sys.exit()
                pygame.quit(); sys.exit()
            if k == 'r' and self.state == self.STATE_DEAD:
                self._init_game(); return

            # Puzzle relay
            if self.state == self.STATE_PUZZLE and self.active_puz:
                self.active_puz.handle_key(k)
                return

            # Interact
            if k == 'e' and self.state == self.STATE_PLAY:
                self._try_interact()

            # Abilities
            if self.state == self.STATE_PLAY:
                if k == '1': self.player.use_ability('speed')
                if k == '2': self.player.use_ability('invisible')
                if k == '3': self.player.use_ability('freeze')

    # ── Interaction ───────────────────────────────────────────────────────
    def _try_interact(self):
        for ped in self.pedestals:
            if ped.solved: continue
            dx, dz = ped.x - self.player.x, ped.z - self.player.z
            if math.sqrt(dx*dx+dz*dz) < INTERACT_D:
                self._start_puzzle(ped.index)
                return

    def _start_puzzle(self, idx):
        self.state = self.STATE_PUZZLE
        self.player.in_safe = True

        if idx == 1:
            self.active_puz = CodePuzzle(idx, self._on_success, self._on_failure)
        else:
            self.active_puz = MemoryPuzzle(idx, self._on_success, self._on_failure)
        self.active_puz.start()

    # ── Update ────────────────────────────────────────────────────────────
    def _update(self, dt):
        if self.notif_timer > 0:
            self.notif_timer -= dt

        if self.state == self.STATE_PLAY:
            self._update_play(dt)
        elif self.state == self.STATE_PUZZLE:
            self._update_puzzle(dt)

    def _update_play(self, dt):
        # Movement
        keys = pygame.key.get_pressed()
        move_x = move_z = 0.0
        fwd_x  =  math.sin(self.cam_yaw)
        fwd_z  =  math.cos(self.cam_yaw)
        right_x=  math.cos(self.cam_yaw)
        right_z= -math.sin(self.cam_yaw)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_x += fwd_x; move_z += fwd_z
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_x -= fwd_x; move_z -= fwd_z
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_x += right_x; move_z += right_z
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_x -= right_x; move_z -= right_z

        self.player.move(move_x, move_z, dt)
        self.player.update(dt)

        # Ghosts
        for ghost in self.ghosts:
            attacked = ghost.update(self.player, dt)
            if attacked:
                self.player.take_damage(20)

        # Win / lose
        if self.player.dead:
            self.state = self.STATE_DEAD
        if self.gate_open:
            gx, gz = GATE_POS
            dx, dz = gx - self.player.x, gz - self.player.z
            if math.sqrt(dx*dx+dz*dz) < 5:
                self.state = self.STATE_WIN

        self.safe_ring_rot += dt * 60

    def _update_puzzle(self, dt):
        self.player.update(dt)
        if self.active_puz:
            self.active_puz.update(dt)

    # ══════════════════════════════════════════════════════════════════════ #
    #  RENDER
    # ══════════════════════════════════════════════════════════════════════ #
    def _render(self):
        self.renderer.begin_frame()

        cx, cz  = self.player.x, self.player.z
        yaw     = self.cam_yaw

        self._draw_world(cx, cz, yaw)
        self._draw_ghosts(cx, cz, yaw)
        self._draw_ui()

        if self.state == self.STATE_PUZZLE and self.active_puz:
            self._draw_puzzle_ui()
        if self.state == self.STATE_DEAD:
            self._draw_overlay('💀  YOU DIED  💀', 'Press R to restart | ESC to quit', (120,0,0))
        if self.state == self.STATE_WIN:
            self._draw_overlay('🌅  YOU ESCAPED!  🌅', 'Congratulations! Press ESC', (0,80,20))

    # ── World rendering ────────────────────────────────────────────────────
    def _draw_world(self, cx, cz, yaw):
        R = self.renderer
        t = self.t

        # ── Graves
        for g in GRAVES:
            depth_check = math.sqrt((g.x-cx)**2+(g.z-cz)**2)
            if depth_check > FAR: continue
            col_side = (55, 55, 55)
            col_top  = (65, 65, 65)
            R.draw_box(g.x, g.height/2, g.z,
                       g.width, g.height, 0.15,
                       cx, cz, yaw, col_top, col_side, tilt_deg=g.tilt)
            # base slab
            R.draw_box(g.x, 0.1, g.z, g.width*1.4, 0.2, 0.45,
                       cx, cz, yaw, (40,40,40),(35,35,35))

        # ── Trees
        for tree in TREES:
            dep = math.sqrt((tree.x-cx)**2+(tree.z-cz)**2)
            if dep > FAR: continue
            # trunk
            R.draw_cylinder(tree.x, 0, tree.z, 0.18, tree.height,
                            cx, cz, yaw, (28,18,8))
            # branches as lines
            for bx, bz, by, bl in tree.branches:
                wx1, wz1 = tree.x, tree.z
                wx2 = tree.x + bx
                wz2 = tree.z + bz
                R.draw_line3d(wx1, by, wz1, wx2, by+0.3, wz2,
                              cx, cz, yaw, (22,14,6), 2)

        # ── Code hint signs
        for hint in HINTS:
            dep = math.sqrt((hint.x-cx)**2+(hint.z-cz)**2)
            if dep > 25: continue
            R.draw_box(hint.x, 1.4, hint.z, 2.0, 0.6, 0.05,
                       cx, cz, yaw, (0,0,0),(10,10,10))
            R.draw_text3d(hint.text, hint.x, 1.4, hint.z,
                          cx, cz, yaw, self.font_sm, (255,220,60))

        # ── Puzzle pedestals
        for ped in self.pedestals:
            dep = math.sqrt((ped.x-cx)**2+(ped.z-cz)**2)
            if dep > FAR: continue
            cols = {'cyan':(0,220,220),'magenta':(220,0,220),'yellow':(220,220,0)}
            col  = (0,180,0) if ped.solved else cols[ped.color_key]
            # pulse glow
            pulse = 0.7 + 0.3 * math.sin(t*2 + ped.index)
            gc = tuple(int(c*pulse) for c in col)
            R.draw_cylinder(ped.x, 0, ped.z, 0.5, 1.5, cx, cz, yaw, gc)
            # glow ring on ground
            ring_pts = 12
            for i in range(ring_pts):
                a0 = math.pi*2*i/ring_pts + math.radians(self.safe_ring_rot * 0.3)
                a1 = math.pi*2*(i+1)/ring_pts + math.radians(self.safe_ring_rot*0.3)
                rx0, rz0 = ped.x + math.cos(a0)*2.5, ped.z + math.sin(a0)*2.5
                rx1, rz1 = ped.x + math.cos(a1)*2.5, ped.z + math.sin(a1)*2.5
                R.draw_line3d(rx0,0.05,rz0, rx1,0.05,rz1, cx,cz,yaw,
                              tuple(int(c*0.7) for c in col), 2)
            # Label
            if dep < 8:
                label = '✓ SOLVED' if ped.solved else '[E] Solve Puzzle'
                R.draw_text3d(label, ped.x, 2.0, ped.z,
                              cx, cz, yaw, self.font_sm,
                              (60,255,60) if ped.solved else (255,255,100))

        # ── Exit gate
        gx, gz = GATE_POS
        dep = math.sqrt((gx-cx)**2+(gz-cz)**2)
        if dep < FAR:
            # Posts
            for ox in (-3, 3):
                R.draw_box(gx+ox, 3, gz, 0.5, 6, 0.5,
                           cx, cz, yaw, (60,40,20),(50,30,15))
            # Bar
            bar_col = (30,160,30) if self.gate_open else (160,30,30)
            bar_y = 5.5 if self.gate_open else 2.0
            R.draw_box(gx, bar_y, gz, 6, 0.3, 0.3,
                       cx, cz, yaw, bar_col, bar_col)
            # Label
            if dep < 15:
                status = '🚪 EXIT — OPEN!' if self.gate_open else '🔒 EXIT — Locked'
                col2 = (60,255,60) if self.gate_open else (255,80,80)
                R.draw_text3d(status, gx, 5.0, gz, cx, cz, yaw, self.font_md, col2)

        # ── Safe zone ring (puzzle active)
        if self.state == self.STATE_PUZZLE:
            ring_r = 4.0
            segs = 16
            for i in range(segs):
                a0 = math.pi*2*i/segs + math.radians(self.safe_ring_rot)
                a1 = math.pi*2*(i+1)/segs + math.radians(self.safe_ring_rot)
                R.draw_line3d(cx+math.cos(a0)*ring_r, 0.1, cz+math.sin(a0)*ring_r,
                              cx+math.cos(a1)*ring_r, 0.1, cz+math.sin(a1)*ring_r,
                              cx, cz, yaw, (80,255,180), 3)

    def _draw_ghosts(self, cx, cz, yaw):
        R = self.renderer
        # Sort back-to-front
        sorted_ghosts = sorted(self.ghosts,
                               key=lambda g: -(((g.x-cx)**2+(g.z-cz)**2)),
                               reverse=False)
        for ghost in sorted_ghosts:
            dep = math.sqrt((ghost.x-cx)**2+(ghost.z-cz)**2)
            if dep > FAR: continue
            col    = ghost.current_color
            alpha  = ghost.alpha
            gy     = ghost.y + 0.9

            # Body (tall ellipse)
            R.draw_sprite(ghost.x, gy, ghost.z, 1.2, 1.8,
                          cx, cz, yaw, col, alpha, 'ellipse')
            # Head
            R.draw_sprite(ghost.x, gy + 1.0, ghost.z, 0.7, 0.7,
                          cx, cz, yaw, col, alpha+20, 'ellipse')
            # Eyes (dark dots)
            for ex_off in (-0.12, 0.12):
                R.draw_sprite(ghost.x + ex_off*math.cos(yaw),
                              gy + 1.15,
                              ghost.z - ex_off*math.sin(yaw),
                              0.08, 0.08, cx, cz, yaw,
                              (5,0,10), 230, 'ellipse')
            # State label when close
            if dep < 10:
                label = {'wander':'~','chase':'!','attack':'!!',
                         'search':'?','frozen':'❄'}.get(ghost.state, '')
                R.draw_text3d(label, ghost.x, gy+1.6, ghost.z,
                              cx, cz, yaw, self.font_md,
                              (255,60,60) if ghost.state=='attack' else (255,200,0))

    # ── HUD ───────────────────────────────────────────────────────────────
    def _draw_ui(self):
        S = self.screen
        t = self.t

        # ── Health bar
        bar_w = 240
        pygame.draw.rect(S, (40,10,10), (20, 20, bar_w+4, 22))
        hp_w  = int(bar_w * self.player.hp_frac)
        r_col = int(lerp(200,30, self.player.hp_frac))
        g_col = int(lerp(20,180, self.player.hp_frac))
        pygame.draw.rect(S, (r_col, g_col, 20), (22, 22, hp_w, 18))
        pygame.draw.rect(S, (180,180,180), (20,20,bar_w+4,22), 1)
        hp_txt = self.font_sm.render(f'❤  {self.player.hp} / {self.player.MAX_HP}', True, (255,255,255))
        S.blit(hp_txt, (28, 23))

        # ── Ability bars
        ab_names  = ['speed','invisible','freeze']
        ab_labels = ['[1] Speed','[2] Invisible','[3] Freeze']
        ab_cols   = [(0,200,255),(200,0,255),(0,200,255)]
        ab_cols2  = [(0,200,255),(220,60,220),(80,180,255)]

        for i,(name, lbl) in enumerate(zip(ab_names, ab_labels)):
            ab  = self.player.abilities[name]
            px  = 20 + i * 175
            py  = 50
            bw  = 160

            pygame.draw.rect(S, (20,20,30), (px, py, bw+4, 20))
            if ab.unlocked:
                fw  = int(bw * ab.cd_frac)
                col = ab_cols2[i]
                if ab.active:
                    pulse = int(128+127*math.sin(t*8))
                    col = (min(255,col[0]+pulse//4), col[1], col[2])
                pygame.draw.rect(S, col, (px+2, py+2, fw, 16))
            pygame.draw.rect(S, (100,100,120), (px, py, bw+4, 20), 1)

            col2 = (255,255,255) if ab.unlocked else (80,80,80)
            txt  = self.font_sm.render(lbl + (' ✓' if ab.active else ''), True, col2)
            S.blit(txt, (px+4, py+2))

        # ── Crosshair
        pygame.draw.line(S, (200,200,200), (HALF_W-10, HALF_H), (HALF_W+10, HALF_H), 1)
        pygame.draw.line(S, (200,200,200), (HALF_W, HALF_H-10), (HALF_W, HALF_H+10), 1)

        # ── Interact hint
        near_ped = self._nearest_unsolved_pedestal()
        if near_ped is not None and self.state == self.STATE_PLAY:
            hint = self.font_md.render('[E]  Solve Puzzle', True, (255,255,80))
            rx = hint.get_rect(center=(HALF_W, H-80))
            S.blit(hint, rx)

        # ── Ghost proximity warning
        min_ghost_d = min((math.sqrt((g.x-self.player.x)**2+(g.z-self.player.z)**2)
                           for g in self.ghosts), default=999)
        if min_ghost_d < 8:
            alpha = int(min(200, (8-min_ghost_d)/8 * 200))
            warn  = pygame.Surface((W, H), pygame.SRCALPHA)
            warn.fill((200,0,0, alpha//4))
            S.blit(warn, (0,0))

        # ── Player flash on damage
        if self.player.flash_timer > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255,0,0,80))
            S.blit(fl, (0,0))

        # ── Notification
        if self.notif_timer > 0 and self.notif_msg:
            alpha = min(255, int(self.notif_timer * 100))
            ntxt  = self.font_md.render(self.notif_msg, True, self.notif_col)
            nr    = ntxt.get_rect(center=(HALF_W, H//2 - 120))
            bg    = pygame.Surface((ntxt.get_width()+16, ntxt.get_height()+8), pygame.SRCALPHA)
            bg.fill((0,0,0,160))
            S.blit(bg, (nr.x-8, nr.y-4))
            S.blit(ntxt, nr)

        # ── Compass / minimap (tiny)
        self._draw_minimap()

        # ── FPS
        fps = self.clock.get_fps()
        fps_t = self.font_sm.render(f'FPS:{fps:.0f}', True, (80,80,80))
        S.blit(fps_t, (W-70, H-20))

    def _draw_minimap(self):
        S   = self.screen
        mmx, mmy = W-110, 20
        mmw, mmh = 90, 90
        scale = mmw / (BOUNDARY*2)

        pygame.draw.rect(S, (0,0,0,180), (mmx, mmy, mmw, mmh))
        pygame.draw.rect(S, (60,60,60),  (mmx, mmy, mmw, mmh), 1)

        # Gate
        gx, gz = GATE_POS
        gmx = mmx + int((gx+BOUNDARY)*scale)
        gmz = mmy + int((gz+BOUNDARY)*scale)
        col = (0,255,0) if self.gate_open else (255,50,50)
        pygame.draw.rect(S, col, (gmx-3, gmz-3, 6, 6))

        # Pedestals
        for ped in self.pedestals:
            px2 = mmx + int((ped.x+BOUNDARY)*scale)
            pz2 = mmy + int((ped.z+BOUNDARY)*scale)
            col2 = (0,200,0) if ped.solved else (0,200,200)
            pygame.draw.circle(S, col2, (px2, pz2), 3)

        # Ghosts
        for g in self.ghosts:
            gxm = mmx + int((g.x+BOUNDARY)*scale)
            gzm = mmy + int((g.z+BOUNDARY)*scale)
            col3 = (255,80,80) if g.state in ('chase','attack') else (120,120,200)
            pygame.draw.circle(S, col3, (gxm, gzm), 2)

        # Player
        pxm = mmx + int((self.player.x+BOUNDARY)*scale)
        pzm = mmy + int((self.player.z+BOUNDARY)*scale)
        pygame.draw.circle(S, (255,220,180), (pxm, pzm), 4)
        # Player direction arrow
        ax = pxm + int(math.sin(self.cam_yaw)*7)
        az = pzm + int(math.cos(self.cam_yaw)*7)
        pygame.draw.line(S, (255,255,255), (pxm,pzm),(ax,az),2)

        lbl = self.font_sm.render('MAP', True, (100,100,100))
        S.blit(lbl, (mmx+2, mmy+mmh-16))

    # ── Puzzle UI ─────────────────────────────────────────────────────────
    def _draw_puzzle_ui(self):
        if not self.active_puz: return
        S    = self.screen
        puz  = self.active_puz
        t    = self.t

        # Semi-transparent panel
        panel = pygame.Surface((700, 420), pygame.SRCALPHA)
        panel.fill((0,0,0,200))
        px, py = HALF_W-350, HALF_H-210
        S.blit(panel, (px, py))
        pygame.draw.rect(S, (80,80,120), (px,py,700,420), 2)

        # Safe zone banner
        stz = self.font_sm.render('🌟  SAFE ZONE — Ghosts are frozen  🌟', True, (100,255,200))
        S.blit(stz, stz.get_rect(center=(HALF_W, py+18)))

        if isinstance(puz, MemoryPuzzle):
            self._draw_memory_puzzle_ui(puz, px, py, t)
        else:
            self._draw_code_puzzle_ui(puz, px, py)

        # Status message
        stxt = self.font_lg.render(puz.status_msg, True, puz.status_col)
        S.blit(stxt, stxt.get_rect(center=(HALF_W, py+370)))

    def _draw_memory_puzzle_ui(self, puz, px, py, t):
        S = self.screen

        title = self.font_xl.render('MEMORY PUZZLE', True, (100,220,255))
        S.blit(title, title.get_rect(center=(HALF_W, py+70)))

        instr = 'Watch the sequence…' if puz.show_phase else 'Repeat with keys 1–4'
        itxt  = self.font_md.render(instr, True, (200,200,200))
        S.blit(itxt, itxt.get_rect(center=(HALF_W, py+130)))

        # Progress dots
        prog_x = HALF_W - (len(puz.sequence)*18)//2
        for i in range(len(puz.sequence)):
            col = (0,220,0) if i < len(puz.player_input) else (60,60,60)
            pygame.draw.circle(S, col, (prog_x + i*18, py+165), 7)

        # Buttons
        btns_x = HALF_W - 170
        for i in range(4):
            bx = btns_x + i*90
            by = py + 195
            col = puz.button_color(i)
            pygame.draw.rect(S, col, (bx, by, 70, 70), border_radius=8)
            pygame.draw.rect(S, (200,200,200),(bx,by,70,70),2, border_radius=8)
            lbl = self.font_lg.render(str(i+1), True, (255,255,255))
            S.blit(lbl, lbl.get_rect(center=(bx+35, by+35)))

        # Sequence length indicator
        seq_t = self.font_sm.render(f'Sequence length: {len(puz.sequence)}', True,(120,120,120))
        S.blit(seq_t, seq_t.get_rect(center=(HALF_W, py+290)))

    def _draw_code_puzzle_ui(self, puz, px, py):
        S = self.screen

        title = self.font_xl.render('CODE PUZZLE', True, (255,220,60))
        S.blit(title, title.get_rect(center=(HALF_W, py+70)))

        hint  = self.font_md.render('Find the 4-digit code written on signs in the world', True, (200,200,200))
        S.blit(hint, hint.get_rect(center=(HALF_W, py+130)))

        # Display entered code
        disp  = self.font_xl.render(puz.display_str, True, (80,220,255))
        S.blit(disp, disp.get_rect(center=(HALF_W, py+210)))

        # Digit buttons guide
        guide = self.font_sm.render('Use number keys 0-9  |  Backspace to delete', True,(120,120,120))
        S.blit(guide, guide.get_rect(center=(HALF_W, py+290)))

    # ── Overlay (death / win) ──────────────────────────────────────────────
    def _draw_overlay(self, title, subtitle, bg_col):
        S    = self.screen
        over = pygame.Surface((W, H), pygame.SRCALPHA)
        over.fill((*bg_col, 180))
        S.blit(over, (0,0))

        ttxt = self.font_xl.render(title, True, (255,255,255))
        S.blit(ttxt, ttxt.get_rect(center=(HALF_W, HALF_H-40)))

        stxt = self.font_lg.render(subtitle, True, (200,200,200))
        S.blit(stxt, stxt.get_rect(center=(HALF_W, HALF_H+30)))

    # ── Helper ─────────────────────────────────────────────────────────────
    def _nearest_unsolved_pedestal(self):
        for ped in self.pedestals:
            if ped.solved: continue
            dx, dz = ped.x-self.player.x, ped.z-self.player.z
            if math.sqrt(dx*dx+dz*dz) < INTERACT_D:
                return ped.index
        return None


# ═══════════════════════════════════════════════════════════════════════════ #
def lerp(a, b, t):
    return a + (b-a)*t

# ═══════════════════════════════════════════════════════════════════════════ #
if __name__ == '__main__':
    game = Game()
    game.run()
