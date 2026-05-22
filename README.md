# Pixel Shooter

A single-file, browser-based top-down arena shooter with retro pixel art. Written in vanilla HTML/CSS/JS — no build step, no external assets, no dependencies.

## Play

Open [`index.html`](index.html) in any modern browser (Chrome, Edge, Firefox, Safari). Everything lives in the one file.

## Controls

| Action | Input |
|---|---|
| Move (8-directional) | `WASD` or Arrow Keys |
| Aim | Mouse |
| Shoot | Click or Hold |

## Features

- 480×270 pixel-perfect canvas, integer-scaled to your window
- Hand-drawn pixel sprites encoded as in-code arrays
- Procedural chiptune SFX via the Web Audio API
- 5 hand-tuned levels, each capped by a unique boss
- 6 equipment pickups (weapons & defenses)
- 5 passive powerups (temporary buffs)
- Particle effects, screen shake, hit-flash, invuln blinking
- High score persisted in `localStorage`

## Bosses

| Level | Boss | Behavior | Guaranteed Drop |
|---|---|---|---|
| 1 | **Bruiser** | Chases + telegraphed charges + cross bursts | Rapid Fire |
| 2 | **Needle** | Keeps distance, teleports, telegraphed sniper shots | Shield |
| 3 | **Hydra** | Ring bullets; splits into 2 mids → 2 minis on death | Spread |
| 4 | **Conjurer** | Summons enemies + alternates ring blasts | Rocket Ammo |
| 5 | **Overlord** | 3-phase ultimate: radial burst → charging spread → summon adds | Laser |

## Equipment Pickups

| Icon | Name | Effect |
|---|---|---|
| Red cross | Health | +1 HP |
| Yellow star | Spread | 3-bullet cone, 8 s |
| Orange bolt | Rapid | Half cooldown, 8 s |
| Cyan ring | Shield | Absorbs next 3 hits |
| Grey rocket | Rocket | +6 explosive AOE rounds |
| Green prism | Laser | Piercing beam, 7 s |

## Powerups

| Icon | Name | Effect |
|---|---|---|
| Magenta lightning | Speed | +50% movement speed, 8 s |
| Red sword | Damage | 2× bullet damage, 8 s |
| Cyan crystal | Slow-Mo | Enemies move at 40% speed, 5 s |
| Gold $$ | Score x2 | Double score on every kill, 10 s |
| Yellow magnet | Magnet | Pickups fly toward you, 10 s |

## Project layout

```
top-down-shooter/
├── index.html   ← the whole game
├── README.md
└── .gitignore
```

## License

Personal project; do whatever you like with it.
