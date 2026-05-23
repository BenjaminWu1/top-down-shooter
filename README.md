# Pixel Shooter

[![Play online](https://img.shields.io/badge/play-online-2ea44f?style=for-the-badge)](https://benjaminwu1.github.io/top-down-shooter/)

A single-file, browser-based top-down arena shooter with retro pixel art. Written in vanilla HTML/CSS/JS — no build step, no external assets, no dependencies. The entire game is `index.html`.

## Play

**Online (no install):** https://benjaminwu1.github.io/top-down-shooter/

**Locally:** clone the repo and open [`index.html`](index.html) in any modern browser (Chrome, Edge, Firefox, Safari). Everything lives in the one file.

## Controls

| Action | Input |
|---|---|
| Move (8-directional) | `WASD` or Arrow Keys |
| Aim | Mouse |
| Shoot | Click or Hold |
| Flamethrower (Tank) | Right mouse button |
| Summon sword-knight (`BLADE`) | `X` |
| Class skill | `C` |
| Flame burst (Tank only, `BURST`) | `B` |

## Characters

Pick one of three classes at the start of a run:

| Class | Profile | HP | Skills (`X` / `C` / `B`) |
|---|---|---|---|
| **Soldier** | Balanced · +25% damage | 5 | Summon blade · Slow-mo · — |
| **Scout** | Fragile but fast | 3 | Summon blade · Slow-mo · — |
| **Tank** | Heavy · +20% damage · flamethrower · starts with shield + fuel | 12 | Summon blade · Wall (4 s invuln) · Flame burst |

- **`X` — Blade (all classes):** summons a melee sword-knight ally that fights alongside you. 25 s cooldown; one alive at a time.
- **`C` — class skill:** Soldier & Scout get **Slow-Mo** (enemies crawl); Tank gets **Wall** (4 s of full invulnerability).
- **`B` — Flame burst (Tank only):** a 3-second ring of fire around the Tank. 20 s cooldown.

A persistent **blue drone companion** (6 HP) is always at your side — it auto-fires at the nearest enemy.

## Progression

- **30 levels** grouped into **6 boss tiers of 5 levels each.** Each tier is built around one boss AI, but every level inside a tier has its own boss name and scaled HP/speed, so all 30 fights feel distinct.
- The arena grows as you advance: levels 1–13 use the base 480×270 world, levels 14–24 a 2× world, and levels 25–30 a 3× world — the larger arenas scroll with a camera that follows you.
- Non-boss enemies scale up in HP and speed every level.

## Bosses

| Tier | Levels | Boss AI | Names | Behavior |
|---|---|---|---|---|
| 1 | 1–5 | **Bruiser** | Bruiser · Rampager · Juggernaut · Colossus · Behemoth | Chases + telegraphed charges + cross bursts |
| 2 | 6–10 | **Needle** | Needle · Marksman · Deadeye · Sharpshot · Huntsman | Keeps distance, teleports, aimed sniper shots |
| 3 | 11–15 | **Hydra** | Hydra · Multiform · Sunderer · Fragmenter · Scion | Ring bullets; splits into smaller copies on death |
| 4 | 16–20 | **Conjurer** | Conjurer · Necromancer · Warlock · Shepherd · Archdemon | Summons adds + alternates ring blasts |
| 5 | 21–25 | **Overlord** | Overlord · Tyrant · Sovereign · Emperor · Godking | 3-phase: radial burst → charging spread → summon adds |
| 6 | 26–30 | **Nemesis** | Nemesis · Archfiend · Worldeater · Voidlord · Annihilator | 4-phase finale; L30 Annihilator is the toughest fight |

## Equipment Pickups

Weapons and defenses that change how you fight:

| Name | Effect |
|---|---|
| Health | +1 HP |
| Spread | 3-bullet cone, 8 s |
| Rapid | Half cooldown, 8 s |
| Shield | Absorbs the next 3 hits |
| Armor | Raises shield cap to 5, refills it, brief invulnerability |
| Rocket | +6 explosive AOE rounds |
| Laser | Piercing beam, 7 s |
| Minigun | Rapid-fire bullets, 8 s |
| Plasma | Bouncing, piercing shots, 8 s |
| Homing | Seeking missiles, 8 s |

## Powerups

Passive temporary buffs:

| Name | Effect |
|---|---|
| Speed | +50% movement speed, 8 s |
| Damage | 2× bullet damage, 8 s |
| Slow-Mo | Enemies move at 40% speed, 5 s |
| Score x2 | Double score on every kill, 10 s |
| Magnet | Pickups fly toward you, 10 s |
| Fuel | Refills the Tank's flamethrower fuel |

## Features

- 480×270 pixel-perfect canvas, integer-scaled to your window
- Hand-drawn pixel sprites encoded as in-code arrays
- Procedural chiptune SFX via the Web Audio API
- 3 playable classes, each with its own weapon and skills
- 30 levels across 6 boss tiers, with growing scrolling arenas
- A persistent companion drone and a summonable sword-knight ally
- 10 equipment pickups and 6 powerups
- Particle effects, hit-flash, invulnerability blinking
- High score persisted in `localStorage`

## Project layout

```
top-down-shooter/
├── index.html   ← the whole game (HTML/CSS/JS, sprites, audio)
├── README.md
├── CLAUDE.md    ← architecture notes for contributors
└── .gitignore
```

## License

Personal project; do whatever you like with it.
