# Pixel Shooter

[![Play online](https://img.shields.io/badge/play-online-2ea44f?style=for-the-badge)](https://benjaminwu1.github.io/top-down-shooter/)

A single-file, browser-based top-down arena shooter with retro pixel art. Written in vanilla HTML/CSS/JS — no build step, no external assets, no dependencies. **The entire game is `index.html`**: every sprite is an in-code pixel array and every sound effect is generated on the fly with the Web Audio API.

## Play

**Online (no install, no account):** https://benjaminwu1.github.io/top-down-shooter/ — just open the link in any modern desktop browser (Chrome, Edge, Firefox, Safari).

**Locally:** clone the repo and open [`index.html`](index.html) directly in a browser. Everything lives in the one file.

> It's a keyboard + mouse game, so it's meant for a computer rather than a phone.

## Controls

| Action | Input |
|---|---|
| Move (8-directional) | `WASD` or Arrow Keys |
| Aim | Mouse |
| Primary attack | Left click (hold to keep firing) |
| **Secondary attack** (class-specific) | **Right mouse button** (hold) |
| Sprint — `X` | +30% move speed for 5 s |
| Class skill — `C` | unique per class (see below) |
| Heal — `F` | +1 HP |
| Blast — `B` | circular AoE burst around you |
| Ultimate — `V` | unique per class (see below) |
| Pause / resume | `Space` (or click) |
| Character stats window | `Tab` (freezes play; `Tab`/`Esc`/click to close) |
| Quit to main menu | `Esc` |

Run setup is: **pick a level → pick a character → pick 2 of 5 assistants → play.** High score is saved in your browser's `localStorage`.

## Characters

Choose one of three classes — each plays completely differently, with its own primary weapon, a held right-mouse secondary, and a five-slot skill kit.

| Class | Profile | HP | Primary (LMB) | Secondary (RMB) |
|---|---|---|---|---|
| **Dr.Syed** | 21st-century rainforest warrior · +25% damage | 10 | Pistol | **Blade slash** — continuous, very high damage over a wide *obtuse* arc; runs on a ~6 s **energy** bar |
| **Xu Yihui** | Blue cyberpunk mech · fast & nimble | 9 | Fast SMG | **3× laser beams** — three instant straight-line beams that damage every enemy along each line at once; runs on a ~20-shot **power** bar (refilled by **battery**) |
| **Benjamin Wu** | U.S.-Army heavy · +20% damage · starts with shield | 12 (+4 shield) | Heavy slug | **Flamethrower** — sustained cone of fire; runs on a 12-unit **fuel** bar |

### Skills

Every class shares **X / F / B**; **C** and **V** are class-specific.

| Slot | Dr.Syed | Xu Yihui | Benjamin Wu |
|---|---|---|---|
| `X` | **Sprint** — +30% move speed (5 s) | Sprint | Sprint |
| `C` | **Napalm** — 3 s ring of fire | **Blink** — teleport to the cursor | **Wall** — 4 s full invulnerability |
| `F` | **Heal** — +1 HP | Heal | Heal |
| `B` | **Blast** — instant circular AoE | Blast | Blast |
| `V` | **Barrage** — fan of 5 explosive shells | **Dash** — dodge with brief i-frames | **Blade+** — summon a fast sword-knight ally |

### The energy / fuel / power bar

All three secondaries draw from a depletable bar shown top-left (no number — the fill is the gauge), and each slowly self-regenerates and is topped up by a class-specific pickup:

- **Dr.Syed** — **energy** for the blade; regenerates **0.2/s** (fast), refilled by a green **beverage**.
- **Xu Yihui** — **power** for the laser beams (~20 volleys, 1 per shot); regenerates **0.1/s**, refilled by a cyan **battery**.
- **Benjamin Wu** — **fuel** for the flamethrower; regenerates **0.1/s**, refilled by a **fuel** canister.

## Assistants

You start owning the **Drone** and buy the rest in the **SHOP** with gold. On the loadout screen you equip **up to 2** of the allies you own; they fight at your side and are rebuilt each level:

- **Drone** — floats nearby and auto-fires at the closest enemy.
- **Brute** — tanky melee bruiser with a wide club swing.
- **Nunchaku** — fast, high-damage close-range striker.
- **Bomber** — lobs high-damage, large-radius bombs from behind you.
- **Poison** — emits a continuous toxic aura that damages everything around it.

Each ally has its own **upgrade level (1–10)**. A fresh ally is deliberately weak; spend gold in the SHOP to level it up (the cost rises each level), restoring its HP, damage, range, and attack speed toward full power.

## Progression

- **40 levels** grouped into **8 boss tiers of 5 levels each.** Each tier is built around one boss AI, but every level inside a tier has its own boss name and scaled HP/speed, so all 40 fights feel distinct.
- The arena grows as you advance: levels **1–13** use the base 480×270 world, **14–24** a 2× world, and **25–40** a 3× world — the larger arenas scroll with a camera that follows you.
- Enemies and bosses scale up in HP and speed on a **three-phase difficulty curve** — gentle through levels 1–15, a moderate ramp 16–24, then a sharp spike 25–40, so the late game leans on your account upgrades.
- **Drops are gated by level:** levels 1–15 give basic, sparse pickups; levels 16–24 add advanced weapon enhancers and utility power-ups; levels 25–40 unlock the full variety.

## Bosses

| Tier | Levels | Boss AI | Names (per level) | Behavior |
|---|---|---|---|---|
| 1 | 1–5 | **Bruiser** | Bruiser · Rampager · Juggernaut · Colossus · Behemoth | Chases + telegraphed charges + cross bursts |
| 2 | 6–10 | **Needle** | Needle · Marksman · Deadeye · Sharpshot · Huntsman | Keeps distance, teleports, aimed sniper shots |
| 3 | 11–15 | **Hydra** | Hydra · Multiform · Sunderer · Fragmenter · Scion | Ring bullets; splits into smaller copies on death |
| 4 | 16–20 | **Conjurer** | Conjurer · Necromancer · Warlock · Shepherd · Archdemon | Summons adds + alternates ring blasts |
| 5 | 21–25 | **Overlord** | Overlord · Tyrant · Sovereign · Emperor · Godking | 3-phase: radial burst → charging spread → summon adds |
| 6 | 26–30 | **Nemesis** | Nemesis · Archfiend · Worldeater · Voidlord · Annihilator | 4-phase onslaught |
| 7 | 31–35 | **Reaper** | Reaper · Harvester · Soulreaper · Deathscythe · Oblivion | Dashes + ring slashes |
| 8 | 36–40 | **Phantom** | Phantom · Wraith · Specter · Revenant · **Apocalypse** | Final tier; **L40 Apocalypse** is the last fight |

## Pickups

Enemies drop attack enhancers, defenses, and buffs. The drop pool is tuned per class (Benjamin Wu can roll **fuel**, Dr.Syed can roll **beverage**).

**Attack enhancers** (these only *enhance* your basic attack — they never change its form): Rapid (half cooldown) · Pierce (shots punch through enemies) · Multi (single → parallel double shot) · Damage (2×). All ~8s timed buffs; their gauges show top-left, above your secondary-attack bar.

**Equipment:** Health (+1 HP) · Shield (absorb hits) · Armor (raise shield cap + brief invuln).

**Powerups:** Speed (+50% move) · Slow-Mo (enemies crawl) · Score ×2 · Magnet (pickups fly to you).

**Class resources:** Fuel (Benjamin Wu's flamethrower) · Beverage (Dr.Syed's blade energy) · Battery (Xu Yihui's laser power).

## Features

- 480×270 pixel-perfect canvas, integer-scaled to your window
- Hand-drawn pixel sprites encoded as in-code arrays
- Procedural chiptune SFX via the Web Audio API
- 3 distinct playable classes, each with a primary, a right-mouse secondary, and a 5-slot skill kit
- Pick-2-of-5 assistant loadout + a summonable sword-knight
- 40 levels across 8 boss tiers, with growing scrolling arenas
- Equipment, powerups, and class-specific resource pickups
- Particle effects, hit-flash, invulnerability blinking, pause
- Character-stats readouts: an in-run **Tab** window (live values) and a **PARAMETERS** button on the menu (base stats + the gain per account level)
- High score persisted in `localStorage`

## Development

The game itself needs no tooling — just open `index.html`. There is one optional, **dependency-free** static validator (`tools/validate.py`, Python 3 standard library only) that lints the game's documented invariants rather than its runtime behavior:

```sh
python tools/validate.py      # or, on Windows: tools\validate.bat
```

It checks that every level's spawn `mix` and all three enemy drop pools sum to exactly 1.0, that there are 40 levels in 8 boss tiers, that each character's skills are wired to cooldowns, and that the script's brackets balance — then exits non-zero if anything is off. The same script runs in CI on every push/PR to `main` (`.github/workflows/validate.yml`); it's a pass/fail signal and does **not** gate the live-site deploy. It is *not* a substitute for playtesting — gameplay, AI, and rendering bugs still need a browser reload to catch.

## Project layout

```
top-down-shooter/
├── index.html              ← the whole game (HTML/CSS/JS, sprites, audio)
├── tools/
│   ├── validate.py         ← dependency-free invariant validator
│   └── validate.bat        ← Windows wrapper
├── .github/workflows/
│   └── validate.yml        ← CI: runs the validator on push/PR
├── docs/                   ← contributor notes (imported by CLAUDE.md via @import)
│   ├── architecture.md     ← index.html walkthrough + coordinate system
│   ├── systems.md          ← input, skills, RMB secondaries, pause
│   └── session-changes.md  ← changelog of recent design decisions
├── README.md
├── CLAUDE.md               ← entry point: essentials + @imports the docs/ files
└── .gitignore
```

## License

Personal project; do whatever you like with it.
