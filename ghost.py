"""Ghost entity – wraps GhostFSM and owns position/visual state."""
import math, random
from ai import GhostFSM, GhostState

class Ghost:
    SPEED_WANDER = 3.5
    SPEED_CHASE  = 7.0

    # RGB colours for different ghost personalities
    TINTS = [
        (160, 255, 200),   # greenish
        (200, 160, 255),   # purple
        (255, 210, 160),   # amber
        (160, 220, 255),   # icy blue
    ]

    def __init__(self, x, z, ghost_id=0, personality=1.0):
        self.x, self.z    = float(x), float(z)
        self.y            = 0.0
        self.ghost_id     = ghost_id
        self.personality  = personality
        self.fsm          = GhostFSM(personality)
        self.state        = GhostState.WANDER
        self.bob_phase    = random.uniform(0, math.pi*2)

        base = self.TINTS[ghost_id % len(self.TINTS)]
        self.base_color   = base   # (r,g,b) 0-255

        self.current_color = base
        self.alpha         = 200   # 0-255

    # ── Update ────────────────────────────────────────────────────────────
    def update(self, player, dt):
        state, move_to, do_attack = self.fsm.update(
            self.x, self.z,
            player.x, player.z,
            player.invisible,
            player.freeze_ghosts,
            player.in_safe,
            dt
        )
        self.state = state

        # Movement
        if move_to:
            tx, tz = move_to
            dx, dz = tx - self.x, tz - self.z
            dist   = math.sqrt(dx*dx + dz*dz)
            if dist > 0.3:
                spd = (self.SPEED_CHASE if state in
                       (GhostState.CHASE, GhostState.ATTACK)
                       else self.SPEED_WANDER) * self.personality
                self.x += (dx/dist) * spd * dt
                self.z += (dz/dist) * spd * dt

        # Bob
        self.y = math.sin(self._time_acc() + self.bob_phase) * 0.25

        # Visual colour
        self._update_color(state)

        return do_attack

    def _time_acc(self):
        # simple accumulator using a class-level counter isn't available,
        # so we'll use a module-level time trick via caller
        import time
        return time.time() * 1.8

    def _update_color(self, state):
        import time
        t = time.time()
        r, g, b = self.base_color

        if state == GhostState.FROZEN:
            self.current_color = (100, 200, 255)
            self.alpha = 140
        elif state == GhostState.ATTACK:
            pulse = abs(math.sin(t * 10))
            self.current_color = (255, int(pulse*200), 0)
            self.alpha = 230
        elif state == GhostState.CHASE:
            pulse = 0.6 + 0.4*abs(math.sin(t*5))
            self.current_color = (int(r*pulse), 20, 20)
            self.alpha = 220
        else:
            self.current_color = self.base_color
            self.alpha = 180

    def dist_to(self, px, pz):
        dx, dz = self.x - px, self.z - pz
        return math.sqrt(dx*dx + dz*dz)
