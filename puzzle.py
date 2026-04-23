"""Puzzle system – MemoryPuzzle and CodePuzzle (pure Python logic)."""
import random

ABILITY_REWARDS = ['speed', 'invisible', 'freeze']

# ─────────────────────────────────────────────────────────────────────────────
class PuzzleBase:
    def __init__(self, index, on_success, on_failure):
        self.index      = index
        self.on_success = on_success
        self.on_failure = on_failure
        self.solved     = False
        self.active     = False
        self.reward     = ABILITY_REWARDS[index % len(ABILITY_REWARDS)]
        self.status_msg = ''
        self.status_col = (255, 255, 255)
        self._end_timer = -1.0   # countdown before calling callback

    def start(self): self.active = True
    def stop(self):  self.active = False

    def update(self, dt):
        if self._end_timer >= 0:
            self._end_timer -= dt
            if self._end_timer < 0:
                self._fire_callback()

    def handle_key(self, key): pass

    def _fire_callback(self): pass

# ─────────────────────────────────────────────────────────────────────────────
class MemoryPuzzle(PuzzleBase):
    """Watch a flashing sequence, then repeat it with keys 1-4."""

    BUTTON_KEYS = {'1':0, '2':1, '3':2, '4':3}
    BTN_COLORS  = [(200,30,30),(30,180,30),(30,30,200),(180,180,0)]
    BTN_DIM     = [(80,10,10),(10,70,10),(10,10,80),(70,70,0)]
    BTN_LABELS  = ['1','2','3','4']

    def __init__(self, index, on_success, on_failure):
        super().__init__(index, on_success, on_failure)
        self.seq_len       = 4 + index
        self.sequence      = []
        self.player_input  = []
        self.show_phase    = True    # True=showing sequence, False=player turn
        self.show_index    = 0
        self.show_timer    = 0.0
        self.flash_idx     = -1      # which button is currently lit
        self.flash_timer   = 0.0
        self._success      = False

    def start(self):
        super().start()
        self.sequence     = [random.randint(0,3) for _ in range(self.seq_len)]
        self.player_input = []
        self.show_phase   = True
        self.show_index   = 0
        self.show_timer   = 0.8
        self.flash_idx    = -1
        self.flash_timer  = 0.0
        self.status_msg   = 'Watch the sequence…'
        self.status_col   = (180, 220, 255)
        self._end_timer   = -1.0
        self._success     = False

    def update(self, dt):
        super().update(dt)
        if not self.active or not self.show_phase:
            return
        self.show_timer -= dt
        self.flash_timer = max(0, self.flash_timer - dt)
        if self.flash_timer <= 0:
            self.flash_idx = -1
        if self.show_timer <= 0:
            if self.show_index < len(self.sequence):
                self.flash_idx   = self.sequence[self.show_index]
                self.flash_timer = 0.45
                self.show_index += 1
                self.show_timer  = 0.75
            else:
                self.show_phase = False
                self.status_msg = 'Your turn! Press 1–4'
                self.status_col = (255, 255, 100)

    def handle_key(self, key):
        if not self.active or self.show_phase or self._end_timer >= 0:
            return
        if key not in self.BUTTON_KEYS:
            return
        idx = self.BUTTON_KEYS[key]
        self.player_input.append(idx)
        pos = len(self.player_input) - 1

        if self.player_input[pos] != self.sequence[pos]:
            self.status_msg  = '✗ Wrong! Ghost spawns!'
            self.status_col  = (255, 60, 60)
            self._end_timer  = 1.2
            self._success    = False
        elif len(self.player_input) == len(self.sequence):
            self.status_msg  = f'✓ Correct! {self.reward.upper()} unlocked!'
            self.status_col  = (60, 255, 100)
            self._end_timer  = 1.5
            self._success    = True

    def _fire_callback(self):
        self.stop()
        if self._success:
            self.solved = True
            self.on_success(self.index, self.reward)
        else:
            self.on_failure(self.index)

    # Render helpers
    def button_color(self, i):
        if self.flash_idx == i:
            return self.BTN_COLORS[i]
        return self.BTN_DIM[i]

# ─────────────────────────────────────────────────────────────────────────────
class CodePuzzle(PuzzleBase):
    """Enter the correct 4-digit code (find numbers on world signs)."""

    CODES = ['3791', '4862', '5047']

    def __init__(self, index, on_success, on_failure):
        super().__init__(index, on_success, on_failure)
        self.code      = self.CODES[index % len(self.CODES)]
        self.entered   = ''
        self._success  = False

    def start(self):
        super().start()
        self.entered    = ''
        self.status_msg = 'Find the code on signs in the world'
        self.status_col = (255, 220, 80)
        self._end_timer = -1.0
        self._success   = False

    def handle_key(self, key):
        if not self.active or self._end_timer >= 0:
            return
        if key == 'backspace' and self.entered:
            self.entered = self.entered[:-1]
            return
        if key.isdigit() and len(self.entered) < len(self.code):
            self.entered += key
            if len(self.entered) == len(self.code):
                if self.entered == self.code:
                    self.status_msg = f'✓ Correct! {self.reward.upper()} unlocked!'
                    self.status_col = (60, 255, 100)
                    self._success   = True
                else:
                    self.status_msg = '✗ Wrong code! Ghost spawns!'
                    self.status_col = (255, 60, 60)
                    self._success   = False
                self._end_timer = 1.3

    def _fire_callback(self):
        self.stop()
        if self._success:
            self.solved = True
            self.on_success(self.index, self.reward)
        else:
            self.on_failure(self.index)

    @property
    def display_str(self):
        s = ''
        for i in range(len(self.code)):
            s += (self.entered[i] if i < len(self.entered) else '_') + ' '
        return s.strip()
