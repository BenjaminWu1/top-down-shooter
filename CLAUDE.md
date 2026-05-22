# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A browser-based top-down arena shooter. **The entire game lives in `index.html`** — vanilla HTML/CSS/JS, no build step, no dependencies, no external assets. All sprites are inline pixel-array data; all SFX are procedurally generated via Web Audio API.

`shooter game.html` is an older untracked draft — ignore it unless asked. The shipped game is `index.html`, served from GitHub Pages at https://benjaminwu1.github.io/top-down-shooter/ (the `.nojekyll` file disables Jekyll on Pages so the raw file is served as-is).

## Running / "Building"

There is no build, test, or lint tooling. To run the game:

- **Local:** open `index.html` directly in a browser (no server needed).
- **Deploy:** push to `main` — GitHub Pages serves `index.html` from the repo root.

When iterating, reload the browser tab; there is no hot reload.

## Architecture

`index.html` is organized as one ~2350-line script with banner-comment section headers (`// =====` blocks). The major sections, in order:

1. **CONSTANTS & CANVAS** — fixed 480×270 pixel canvas, integer-scaled to the window via `resize()`. `imageSmoothingEnabled=false` is load-bearing for the pixel-art look.
2. **SPRITES** — every sprite is a `{pal, rows}` object built by `S(pal, rows)`, where `rows` is an array of ASCII strings and `pal` maps each character to a CSS color (or `null` for transparent). `drawSprite` walks the rows and `fillRect`s a 1×1 pixel per non-null character. Most entities have two frames (`_a`/`_b`) animated by a `frameT`/`frame` timer.
3. **AUDIO** — `tone()` / `noiseHit()` synthesize chiptune SFX with oscillators + filtered noise. `initAudio()` lazy-creates the `AudioContext` on the first mouse click (browsers block autoplay).
4. **LEVELS** — `LEVELS` is a 10-element array of `{total, rate, mix, boss}`. `mix` is a weighted list consumed by `pickWeighted()` for enemy spawn rolls. The boss for each level is named in `BOSS_NAMES`. Non-boss enemy HP/speed scales with level via `enemyScale()` (≈1.0 at L1 → ≈1.72 at L10) applied inside `createEnemy`. Bosses keep fixed per-kind stats tuned for their level.
5. **STATE** — `STATE` enum (`MENU`, `HOWTO`, `PLAYING`, `LEVEL_COMPLETE`, `GAME_OVER`, `VICTORY`) drives both `update()` and `draw()` via dispatch on the `state` variable. High score persists in `localStorage` under the key `shooter_high`.
6. **INPUT** — global `keys[]` map plus a `mouse` object; mouse coords are scaled from CSS pixels back into the 480×270 logical space.
7. **ENTITY FACTORIES** — `createPlayer`, `createEnemy(kind, ...)`, `createBullet(...)`, `createPickup(...)`, `createCompanion()`. All entities are plain objects with a `type` field (`'player'`, `'enemy'`, `'bullet'`, `'pickup'`, `'companion'`) and live in the global `entities` array. Dead entities set `dead:true` and are filtered out once per frame. The companion is also tracked via a global `companion` reference for convenient access.
8. **SPAWNING & LEVEL FLOW** — `spawnEnemyAtEdge`, `spawnBoss`, `startLevel(idx)`, `startGame()`. The boss only spawns after `spawnedCount >= levelData.total` **and** most regular enemies have died (see `updatePlaying`).
9. **UPDATE** — `update(dt)` dispatches on `state`. `updatePlaying(dt)` is the core game tick: powerup timers → player movement/aim → shooting → enemy spawn → entity update → collisions → win/loss check. **Slow-Mo powerup** is implemented by scaling `dt` only for enemies and enemy bullets (see the `enemyDt` variable) — player and player bullets keep full-speed `dt`.
10. **WEAPONS** — `fireWeapon(mx, my)` has a fixed priority cascade: **rocket → laser → homing → plasma → spread → minigun → default**. Modifiers stack on top: `rapidTime` halves cooldown, `damageTime` doubles bullet damage. When adding a new weapon, slot it into this priority chain rather than branching elsewhere. Bullet behavior flags worth knowing: `pierce` (uses `hitSet`, doesn't die on hit), `explosive` (calls `explode()`), `homing` (steers each tick — player-bullets toward nearest enemy, enemy-bullets toward player), `bounces` (reflects off screen edges; clears `hitSet` on bounce so plasma can re-hit). Plasma combines `pierce + bounces`.
11. **COMPANION** — A persistent AI ally (`type:'companion'`) follows the player and auto-fires at the nearest enemy within range. Has its own HP, `invuln` window, and `hitFlash`. Bullets it spawns use `owner:'player'` so the existing player-bullet vs enemy collision loop just works. Lives in `entities` AND as a global `companion` reference. Refreshed each level start in `startLevel` (full HP if alive, or recreated if dead). Damage flow: `damageCompanion(amount)`. AI lives in `updateCompanion(dt)`.
12. **COMBAT** — `damagePlayer` (respects `shieldHp` first, then `invuln` window), `damageCompanion`, `killEnemy` (handles score, pickup drops, splitter-on-death spawn logic, boss-guaranteed drops). Enemy-bullet collision and enemy-melee collision each check player AND companion separately.
13. **ENEMY AI** — one update function per enemy kind: `updateSeek` (grunt/runner/tank), `updateShooter`, `updateBruiser`, `updateSniper`, `updateSplitter`, `updateSummoner`, `updateOverlord`, plus the L6-L10 bosses: `updateTwin`, `updateReaper`, `updateBomber`, `updatePhantom`, `updateNemesis`. `updateEnemy(e, dt)` dispatches on `e.kind`. Boss telegraph attacks use a `telegraph` timer + `phase`/`phaseT` for multi-stage patterns (Overlord has 3 phases, Nemesis has 4).
14. **DRAW** — `draw()` dispatches on `state`. `drawGame()` renders the world with optional screen-shake offset (`shakeTime`/`shakeAmt`), then `drawHUD` and `drawWeaponHUD` overlay UI. Per-type drawers: `drawPlayer`, `drawEnemy`, `drawBulletEntity`, `drawPickupEntity`, `drawCompanion`. Menu screens (`drawMenu`, `drawHowTo`, `drawLevelComplete`, `drawGameOver`, `drawVictory`) are click-handled in `handleMenu`/`handleLevelComplete`/`handleEndScreen` using `clickedRect`.
15. **MAIN LOOP** — `loop(t)` clamps `dt` to 33ms (≈30fps floor) to keep collision math stable on tab-switches, then `update(dt); draw();`.

### Adding things — quick reference

- **New enemy kind:** add a sprite pair to `SPR`, a `case` in `createEnemy`, an `update<Kind>` function, dispatch in `updateEnemy`, sprite mapping in `drawEnemy`'s switch, and (if it should appear) weight it into a level's `mix`. If it's a boss, also add an entry to `BOSS_NAMES` and a guaranteed drop in `killEnemy`'s `drops` map.
- **New equipment/powerup pickup:** add sprite + color, extend `applyPickup` with the effect, add a timer field on the player in `createPlayer` (for timed buffs), decay it in `updatePlaying`, and apply the effect where relevant (`fireWeapon`, movement, etc.). Render the icon in `drawPickupEntity` (extend both `sprMap` and `glowColors`), the HUD timer in `drawWeaponHUD`, and the listing in `drawHowTo`'s `eq` array.
- **Tuning difficulty:** edit `LEVELS` (counts/rates/mix), the per-kind boss stats in `createEnemy`, and `enemyScale()` for the non-boss progression curve.

### Coordinate system

World is logical 480×270. All gameplay positions, radii, and speeds are in those units. `resize()` only scales the canvas element's CSS size — the backing store stays 480×270 and the mouse handler rescales pointer coords into world space. Don't accidentally use `clientX`/`clientY` directly.
