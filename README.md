# 👻 Cemetery Escape — 3D Horror Survival
### Requires only: `pip install pygame`

---

## ⚙️ Setup (ONE command)

```bash
pip install pygame
python main.py
```

That's it. No Ursina, no OpenGL, no extra deps.

---

## 🗂️ Files

```
cemetery3d/
├── main.py    ← Game loop, 3D renderer, camera, HUD, puzzle UI
├── player.py  ← Movement, health, 3 abilities with cooldowns
├── ghost.py   ← Ghost entity, bobbing, visual states
├── ai.py      ← FSM: Wander / Chase / Attack / Search / Frozen
├── puzzle.py  ← MemoryPuzzle + CodePuzzle (pure Python)
├── world.py   ← Cemetery layout: graves, trees, pedestals, gate
└── README.md
```

---

## 🎮 Controls

| Key               | Action                              |
|-------------------|-------------------------------------|
| WASD / Arrows     | Move                                |
| Mouse             | Look / rotate camera                |
| **E**             | Interact with glowing pedestal      |
| **1**             | Speed Boost (unlock puzzle 0 first) |
| **2**             | Invisibility (unlock puzzle 1 first)|
| **3**             | Ghost Freeze (unlock puzzle 2 first)|
| **R**             | Restart (on Game Over screen)       |
| **ESC**           | Quit                                |

**Memory Puzzle:** Keys **1–4** to repeat the flashing button sequence.  
**Code Puzzle:** Keys **0–9** + **Backspace** to enter the 4-digit code.

---

## 🎯 How to Win

1. **Explore** the foggy cemetery. Avoid 4 roaming ghosts.
2. **Find** the 3 glowing pedestals (shown on the minimap).
3. **Press E** near a pedestal → enter safe zone (ghosts freeze).
4. **Solve** the puzzle:
   - 🔮 **Memory** (pedestals 0 & 2): Watch flashing 1-4 buttons → repeat the sequence.
   - 🔑 **Code** (pedestal 1): Find the number on yellow signs in the world → type it.
5. **Success** → unlock an ability. **Failure** → -30 HP + new ghost spawns.
6. **All 3 solved** → exit gate opens (north, top of minimap).
7. **Walk to the gate** → You escape! 🎉

---

## 👻 Ghost AI States

| State   | Trigger                          | Behaviour              |
|---------|----------------------------------|------------------------|
| WANDER  | Default                          | Random roaming         |
| CHASE   | You're within 14 units           | Runs toward you        |
| ATTACK  | Within 2.2 units                 | Deals 20 HP damage     |
| SEARCH  | You turned invisible mid-chase   | Checks last known pos  |
| FROZEN  | Freeze ability / puzzle safe zone| Completely stops       |

---

## ⚡ Abilities (unlock by solving puzzles)

| Key | Ability     | Duration | Cooldown | Effect                         |
|-----|-------------|----------|----------|--------------------------------|
| 1   | Speed Boost | 5s       | 15s      | 2.2× movement speed            |
| 2   | Invisibility| 6s       | 20s      | Ghosts ignore you, go SEARCH   |
| 3   | Ghost Freeze| 4s       | 25s      | All ghosts frozen in place     |

---

## 🗺️ Minimap (top-right)

- **White dot + arrow** = you (arrow = look direction)
- **Cyan dots** = unsolved pedestals
- **Green dots** = solved pedestals
- **Red square** = locked gate / **Green** = open gate
- **Red blips** = chasing ghosts / **Blue blips** = wandering ghosts

---

## 💡 Tips

- Use trees and graves for cover — ghosts lose chase if you go invisible behind obstacles.
- Memorise the code signs **before** interacting with the pedestal.
- After a puzzle failure, use **Speed + Invisibility** to escape the spawned ghost.
- The gate is at the very north (top of minimap at Z=50).

---

## 🔧 Tweaks

In `main.py`:
- `FOG_END = 45.0` → lower for denser fog
- Change ghost count in `__init_game__` → add more `Ghost(...)` entries
- `INTERACT_D = 4.5` → pedestal interaction radius
