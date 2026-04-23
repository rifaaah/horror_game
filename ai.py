"""Ghost AI – pure Python Finite State Machine (no external deps)."""
import random, math

class GhostState:
    WANDER  = "wander"
    CHASE   = "chase"
    ATTACK  = "attack"
    SEARCH  = "search"
    FROZEN  = "frozen"

class GhostFSM:
    DETECT  = 14.0
    ATTACK  = 2.2
    LOSE    = 28.0

    def __init__(self, personality=1.0):
        self.state          = GhostState.WANDER
        self.personality    = personality
        self.last_known     = None
        self.wander_target  = None
        self.wander_timer   = 0.0
        self.attack_timer   = 0.0

    def update(self, gx, gz, px, pz, invisible, frozen, safe, dt):
        """Returns (state, move_to=(tx,tz)|None, do_attack=bool)"""
        if frozen or safe:
            self.state = GhostState.FROZEN
            return self.state, None, False

        dx, dz = px - gx, pz - gz
        dist = math.sqrt(dx*dx + dz*dz)

        # transitions
        if self.state == GhostState.WANDER:
            if not invisible and dist < self.DETECT:
                self.state = GhostState.CHASE

        elif self.state == GhostState.CHASE:
            self.last_known = (px, pz)
            if dist < self.ATTACK:
                self.state = GhostState.ATTACK
            elif dist > self.LOSE:
                self.state = GhostState.WANDER
            elif invisible:
                self.state = GhostState.SEARCH

        elif self.state == GhostState.ATTACK:
            if dist > self.ATTACK * 2:
                self.state = GhostState.CHASE
            self.attack_timer -= dt

        elif self.state == GhostState.SEARCH:
            if not invisible and dist < self.DETECT:
                self.state = GhostState.CHASE
            elif self.last_known:
                lx, lz = self.last_known
                if math.sqrt((gx-lx)**2+(gz-lz)**2) < 1.5:
                    self.state = GhostState.WANDER

        # wander target refresh
        self._tick_wander(gx, gz, dt)

        # produce action
        do_attack = False
        move_to   = None

        if self.state == GhostState.WANDER:
            move_to = self.wander_target
        elif self.state == GhostState.CHASE:
            move_to = (px, pz) if not invisible else self.last_known
        elif self.state == GhostState.ATTACK:
            move_to = (px, pz)
            if self.attack_timer <= 0 and not invisible:
                do_attack = True
                self.attack_timer = 1.3 / self.personality
        elif self.state == GhostState.SEARCH:
            move_to = self.last_known

        return self.state, move_to, do_attack

    def _tick_wander(self, gx, gz, dt):
        self.wander_timer -= dt
        if (self.wander_target is None or self.wander_timer <= 0 or
                (self.wander_target and
                 math.sqrt((gx-self.wander_target[0])**2 +
                           (gz-self.wander_target[1])**2) < 1.5)):
            self.wander_target = (random.uniform(-48, 48),
                                  random.uniform(-48, 48))
            self.wander_timer  = random.uniform(5, 12)
