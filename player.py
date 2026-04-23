"""Player – movement, health, abilities (pure Python)."""
import math

SPEED_BASE  = 6.0
BOUNDARY    = 48.0

class Ability:
    def __init__(self, cooldown, duration):
        self.unlocked  = False
        self.active    = False
        self.cooldown  = cooldown
        self.duration  = duration
        self.cd_timer  = 0.0
        self.dur_timer = 0.0

    def try_activate(self):
        if self.unlocked and not self.active and self.cd_timer <= 0:
            self.active    = True
            self.dur_timer = self.duration
            self.cd_timer  = self.cooldown
            return True
        return False

    def tick(self, dt):
        if self.cd_timer  > 0: self.cd_timer  -= dt
        if self.active:
            self.dur_timer -= dt
            if self.dur_timer <= 0:
                self.active = False

    @property
    def cd_frac(self):
        """0=on cooldown, 1=ready"""
        if self.cooldown == 0: return 1.0
        return max(0.0, min(1.0, 1.0 - self.cd_timer / self.cooldown))

class Player:
    MAX_HP = 100

    def __init__(self):
        self.x   = 0.0
        self.z   = 0.0
        self.y   = 0.0          # height (for future use)
        self.yaw = 0.0          # facing angle in radians

        self.hp          = self.MAX_HP
        self.dead        = False
        self.in_safe     = False   # puzzle safe-zone
        self.dmg_cd      = 0.0

        self.speed = SPEED_BASE

        self.abilities = {
            'speed':     Ability(cooldown=15, duration=5),
            'invisible': Ability(cooldown=20, duration=6),
            'freeze':    Ability(cooldown=25, duration=4),
        }

        self.flash_timer = 0.0   # red flash on damage

    # ── Movement ──────────────────────────────────────────────────────────
    def move(self, dx, dz, dt):
        spd = SPEED_BASE * (2.2 if self.abilities['speed'].active else 1.0)
        length = math.sqrt(dx*dx + dz*dz)
        if length > 0:
            dx, dz = dx/length, dz/length
            self.x = max(-BOUNDARY, min(BOUNDARY, self.x + dx*spd*dt))
            self.z = max(-BOUNDARY, min(BOUNDARY, self.z + dz*spd*dt))
            self.yaw = math.atan2(dx, dz)

    # ── Damage ────────────────────────────────────────────────────────────
    def take_damage(self, amt):
        if self.dead or self.in_safe or self.dmg_cd > 0:
            return
        if self.abilities['invisible'].active:
            return
        self.hp      = max(0, self.hp - amt)
        self.dmg_cd  = 1.5
        self.flash_timer = 0.4
        if self.hp <= 0:
            self.dead = True

    # ── Abilities ─────────────────────────────────────────────────────────
    def use_ability(self, name):
        return self.abilities[name].try_activate()

    def unlock(self, name):
        if name in self.abilities:
            self.abilities[name].unlocked = True

    # ── Tick ──────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.dmg_cd    > 0: self.dmg_cd    -= dt
        if self.flash_timer > 0: self.flash_timer -= dt
        for ab in self.abilities.values():
            ab.tick(dt)

    # ── Helpers ───────────────────────────────────────────────────────────
    @property
    def invisible(self): return self.abilities['invisible'].active
    @property
    def freeze_ghosts(self): return self.abilities['freeze'].active
    @property
    def hp_frac(self): return self.hp / self.MAX_HP
