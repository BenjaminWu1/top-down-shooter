# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A browser-based top-down arena shooter. **The entire game lives in `index.html`** — vanilla HTML/CSS/JS, no build step, no dependencies, no external assets. All sprites are inline pixel-array data; all SFX are procedurally generated via Web Audio API.

`shooter game.html` is an older untracked draft — ignore it unless asked. The shipped game is `index.html`, served from GitHub Pages at https://benjaminwu1.github.io/top-down-shooter/ (the `.nojekyll` file disables Jekyll on Pages so the raw file is served as-is).

`README.md` is out of date — it still describes 5 levels and 5 bosses. The shipped game has **30 levels grouped into 6 boss tiers of 5 levels each**, a persistent blue drone companion, a summonable sword-knight ally on the X key, and a Tank-only B-key flame burst. Trust this file and the code, not the README, for current scope.

## Running / "Building"

There is no build, test, or lint tooling. To run the game:

- **Local:** open `index.html` directly in a browser (no server needed).
- **Deploy:** push to `main` — GitHub Pages serves `index.html` from the repo root.

When iterating, reload the browser tab; there is no hot reload.

## Git workflow

**Save work to GitHub continuously — don't let progress sit in an uncommitted state.** As you work, commit each finished change to git and push it to GitHub right away. This repo serves the live site directly from `main`, and the only reliable record of "what we've done" is what's been pushed. If a session ends with uncommitted changes (browser crash, machine reboot, agent timeout, the user clearing context), that work is effectively gone. Treat every commit-and-push as a save game.

**Rhythm to follow during a session:**

1. **Finish one coherent unit of work** — a new feature, a bug fix, a tuning pass, a doc update, etc. (Not "everything for today" — one thing.)
2. **Verify it works** — reload `index.html` in a browser and exercise the change. Tests and lint do not exist for this repo, so manual verification is the only signal.
3. **Stage just the files for that change** — `git add <specific files>`, not `git add -A`. Avoids accidentally committing unrelated drift, secrets, or large binaries.
4. **Commit with a clean message** (see format below).
5. **`git push origin main` immediately** — don't batch pushes. Pushing is also how the live GitHub Pages site updates, so each push is a public release.
6. **Repeat for the next change.** Do not stack three features into one commit, and do not let large uncommitted diffs accumulate over multiple changes.

**Commit message format:**

- Short imperative subject, ≤72 chars.
- Prefixed with one of `feat:` / `fix:` / `docs:` / `refactor:` / `ci:` / `chore:` to match the existing history (`git log` shows the convention).
- Add a body paragraph only when the *why* is not obvious from the subject (e.g., explaining a bug's root cause, a tuning rationale, or a non-obvious design tradeoff).
- Co-authored-by trailer when the commit comes from a Claude Code session.

**Hard rules:**

- **Never force-push `main`** (`git push --force` / `git push --force-with-lease`) without an explicit, in-session request from the user. Force-pushing rewrites the live site's history and can lose teammates' work.
- **Never skip hooks** (`--no-verify`, `--no-gpg-sign`, etc.) without an explicit request. If a hook fails, fix the underlying issue rather than bypassing it.
- **Never amend an already-pushed commit.** Create a new commit instead — amending after push requires a force-push to reconcile, and that violates the rule above.
- **Don't commit files that may contain secrets** — `.env`, `credentials.json`, anything with API keys. If the user asks you to commit something that looks sensitive, warn them first.

**At session end:**

Before the conversation closes, run `git status` and confirm the tree is clean. If there are unstaged or uncommitted changes that represent real work, commit and push them now — do not leave them for the user to deal with. If there are intentionally-unfinished WIP changes that should not ship, say so explicitly and ask the user how to handle them rather than silently leaving them on disk.

## Architecture

`index.html` is organized as one ~3500-line script with banner-comment section headers (`// =====` blocks). The major sections, in order:

1. **CONSTANTS & CANVAS** — fixed 480×270 pixel canvas, integer-scaled to the window via `resize()`. `imageSmoothingEnabled=false` is load-bearing for the pixel-art look.
2. **SPRITES** — every sprite is a `{pal, rows}` object built by `S(pal, rows)`, where `rows` is an array of ASCII strings and `pal` maps each character to a CSS color (or `null` for transparent). `drawSprite` walks the rows and `fillRect`s a 1×1 pixel per non-null character. Most entities have two frames (`_a`/`_b`) animated by a `frameT`/`frame` timer.
3. **AUDIO** — `tone()` / `noiseHit()` synthesize chiptune SFX with oscillators + filtered noise. `initAudio()` lazy-creates the `AudioContext` on the first mouse click (browsers block autoplay).
4. **LEVELS** — `LEVELS` is a **30-element** array of `{total, rate, mix, boss, bossName?}`. `mix` is a weighted list consumed by `pickWeighted()` for enemy spawn rolls. **Mix weights must sum to 1.0** — `pickWeighted` does not normalize; entries past the cumulative-1.0 mark are unreachable. The boss kind for each level is in `boss`; the displayed name comes from `BOSS_NAMES[boss]` unless the level provides an override `bossName`. Bosses are assigned in **6 tiers of 5 levels each, no two tiers sharing a boss AI**: L1-L5 `bruiser`, L6-L10 `sniper`, L11-L15 `splitter`, L16-L20 `summoner`, L21-L25 `overlord`, L26-L30 `nemesis`. Every level inside a tier gets its own `bossName` (BRUISER/RAMPAGER/JUGGERNAUT/COLOSSUS/BEHEMOTH for tier 1, etc.) so each fight feels distinct even though the AI is identical. Non-boss enemy HP/speed scales with level via `enemyScale() = 1 + levelIdx*0.08` (≈1.0 at L1 → ≈3.32 at L30) inside `createEnemy`. **Bosses scale too**: `spawnBoss` applies `hpScale = 1 + levelIdx*0.07` and `spdScale = 1 + levelIdx*0.015` on top of the base per-kind stats so the same AI at L30 has ~3× the HP of its L1 counterpart.
5. **STATE** — `STATE` enum (`MENU`, `HOWTO`, `PLAYING`, `LEVEL_COMPLETE`, `GAME_OVER`, `VICTORY`) drives both `update()` and `draw()` via dispatch on the `state` variable. High score persists in `localStorage` under the key `shooter_high`.
6. **INPUT** — global `keys[]` map plus a `mouse` object; mouse coords are scaled from CSS pixels back into the 480×270 logical space.
7. **ENTITY FACTORIES** — `createPlayer`, `createEnemy(kind, ...)`, `createBullet(...)`, `createPickup(...)`, `createCompanion()`, `createSwordAlly(x, y)`. All entities are plain objects with a `type` field (`'player'`, `'enemy'`, `'bullet'`, `'pickup'`, `'companion'`, `'sword_ally'`) and live in the global `entities` array. Dead entities set `dead:true` and are filtered out once per frame. The blue drone companion is also tracked via a global `companion` reference for convenient access; sword allies are only found by iterating `entities` (there can be at most one alive at a time — see the summon skill below).
8. **SPAWNING & LEVEL FLOW** — `spawnEnemyAtEdge`, `spawnBoss`, `startLevel(idx)`, `startGame()`. The boss only spawns after `spawnedCount >= levelData.total` **and** most regular enemies have died (see `updatePlaying`).
9. **UPDATE** — `update(dt)` dispatches on `state`. `updatePlaying(dt)` is the core game tick: powerup timers → player movement/aim → shooting → enemy spawn → entity update → collisions → win/loss check. **Slow-Mo powerup** is implemented by scaling `dt` only for enemies and enemy bullets (see the `enemyDt` variable) — player and player bullets keep full-speed `dt`.
10. **WEAPONS** — `fireWeapon(mx, my)` has a fixed priority cascade: **rocket → laser → homing → plasma → spread → minigun → default**. Modifiers stack on top: `rapidTime` halves cooldown, `damageTime` doubles bullet damage. When adding a new weapon, slot it into this priority chain rather than branching elsewhere. Bullet behavior flags worth knowing: `pierce` (uses `hitSet`, doesn't die on hit), `explosive` (calls `explode()`), `homing` (steers each tick — player-bullets toward nearest enemy, enemy-bullets toward player), `bounces` (reflects off screen edges; clears `hitSet` on bounce so plasma can re-hit). Plasma combines `pierce + bounces`.
11. **ALLIES** — The game has two ally entity types:
    - **`companion`** — persistent blue drone, always present from level start, follows the player, auto-fires at the nearest enemy within 140 units. AI in `updateCompanion(dt)`, damage flow in `damageCompanion(amount)`. Tracked both inside `entities` and via the global `companion` reference. Refreshed each level start in `startLevel` (full HP if alive, recreated if dead).
    - **`sword_ally`** — summoned melee knight, spawned by the X-key skill (universal across all three characters, 25s cooldown). Short attack range (~24 units) but a wide 120° cone arc. One alive at a time — re-summoning kills the previous one. AI in `updateSwordAlly(dt)` and `swordAllyAttack(s)`; damage flow in `damageSwordAlly(s, amount)`. Cleared between levels by the existing `startLevel` filter that keeps only `player` + `companion`. Renders a yellow arc behind the sprite while `swingTime > 0`.

    Both allies fire/swing as "owner:'player'" so existing player-bullet vs enemy collision logic just works, and enemy-bullet / enemy-melee collisions check player + companion + sword_ally separately.
12. **COMBAT** — `damagePlayer` (respects `shieldHp` first, then `invuln` window), `damageCompanion`, `damageSwordAlly`, `killEnemy` (handles score, pickup drops, splitter-on-death spawn logic, boss-guaranteed drops). `killEnemy` is **idempotent** — it sets `en._killed = true` on first entry and short-circuits subsequent calls so the splitter cascade cannot fire twice when a grenade's collision hit AND its `explode()` both see the same dying enemy. Enemy-bullet collision and enemy-melee collision each check player AND companion AND sword-ally separately. `explode()` is the shared AoE primitive: damages enemies in radius (operating on a **snapshot** of enemies — newly-spawned splitter children from the same blast are not re-damaged), spawns particles, and bumps `shakeTime`/`shakeAmt` (the variables still get set but `draw()` no longer applies an offset — see DRAW). `particles` is a global array hard-capped at 300 entries and reset to `[]` in both `startGame` and `startLevel`.
13. **ENEMY AI** — one update function per enemy kind: `updateSeek` (grunt/runner/tank), `updateShooter`, `updateBruiser`, `updateSniper`, `updateSplitter`, `updateSummoner`, `updateOverlord`, plus the orphaned-but-still-defined `updateTwin`, `updateReaper`, `updateBomber`, `updatePhantom`, `updateNemesis` (Nemesis is the L26-L30 finale AI; the other four are not currently referenced in `LEVELS` after the 6-tier reshuffle but are left in place for future reuse). `updateEnemy(e, dt)` dispatches on `e.kind`. Boss telegraph attacks use a `telegraph` timer + `phase`/`phaseT` for multi-stage patterns (Overlord has 3 phases, Nemesis has 4).
14. **DRAW** — `draw()` dispatches on `state`. Screen shake is currently **disabled** — `draw()` no longer applies a translate offset. Combat code still assigns `shakeTime`/`shakeAmt` (harmless), so re-enabling shake is a one-line change: restore the `SHAKE_LEVEL` constant and the `ctx.translate(sx, sy)` block inside `draw()`. `drawGame()` renders the world, then `drawHUD` and `drawWeaponHUD` overlay UI. Per-type drawers: `drawPlayer`, `drawEnemy`, `drawBulletEntity`, `drawPickupEntity`, `drawCompanion`, `drawSwordAlly` (which also draws the swing-arc cone while `s.swingTime > 0`). Menu screens (`drawMenu`, `drawHowTo`, `drawLevelComplete`, `drawGameOver`, `drawVictory`) are click-handled in `handleMenu`/`handleLevelComplete`/`handleEndScreen` using `clickedRect`. The main menu has a `? GUIDE` button (top-right via `guideButtonRect()`) that switches to `STATE.HOWTO`.
15. **MAIN LOOP** — `loop(t)` clamps `dt` to 33ms (≈30fps floor) to keep collision math stable on tab-switches, then `update(dt); draw();`. Don't bypass this clamp from new code — without it a backgrounded tab can return a multi-second `dt` that tunnels fast bullets clean through enemies.

    `update` and `draw` are each wrapped in their **own** try/catch with a `console.error` so an exception in one cannot kill the rAF chain or freeze the canvas on a stale frame. A defensive cap also runs at the top of each frame: if `entities.length > 600`, it prunes dead entries and trims to player+companion plus the 380 most-recent others. Keep both safety nets in place when refactoring — they're cheap and they kept a real freeze-on-M bug from being totally invisible to the user.

### Adding things — quick reference

- **New enemy kind:** add a sprite pair to `SPR`, a `case` in `createEnemy`, an `update<Kind>` function, dispatch in `updateEnemy`, sprite mapping in `drawEnemy`'s switch, and (if it should appear) weight it into a level's `mix`. If it's a boss, also add an entry to `BOSS_NAMES` and a guaranteed drop in `killEnemy`'s `drops` map.
- **New equipment/powerup pickup:** add sprite + color, extend `applyPickup` with the effect, add a timer field on the player in `createPlayer` (for timed buffs), decay it in `updatePlaying`, and apply the effect where relevant (`fireWeapon`, movement, etc.). Render the icon in `drawPickupEntity` (extend both `sprMap` and `glowColors`), the HUD timer in `drawWeaponHUD`, and the listing in `drawHowTo`'s `eq` array. **Crucially: add the kind to the drop pool inside `killEnemy` and re-balance weights so they sum to 1.0** — the old code appended fuel after the weights already summed to 1.0, which silently gave fuel a 0% drop rate for a long time. There are two pools now (Tank vs non-Tank); both must stay summed to 1.0.
- **New ally type:** factory function returning `{type:'<name>', ...}`, an `update<Name>` AI function, a dispatch in the main entity update loop (`updatePlaying`), an enemy-bullet collision block + enemy-melee collision block (mirror the sword_ally pattern), a `drawSwordAlly`-style renderer, draw-dispatch in `drawGame`, and a damage handler. Make sure `startLevel`'s `entities.filter(...)` either preserves your ally type across levels or strips it.
- **Tuning difficulty:** edit `LEVELS` (counts/rates/mix), the per-kind boss stats in `createEnemy`, and `enemyScale()` for the non-boss progression curve.

### Input & focus

Letter keys (especially W/A/S/D/X/C/B) used to allow browser default actions, which on some setups (notably Windows 11 / Chinese IME, certain Chrome focus modes) would scroll the page even with `overflow:hidden` set on `<body>`. The skill HUD lives near the bottom of the canvas, so any scroll pushed it out of view and the player thought the game was frozen. The current input layer defends against this in four places:

1. **`GAMEPLAY_KEYS` Set** — every key the game listens for is in this set, and the global keydown/keyup handlers `preventDefault()` for anything in it.
2. **Canvas is focusable** — `canvas.tabIndex = -1`, `outline:none`, focused on every mousedown and on `window.load`. Keys route through a focused canvas which has no default scroll behavior.
3. **Hard scroll-lock** — a `window.scroll` listener immediately snaps `scrollTo(0, 0)` if anything (browser auto-scroll-into-view, virtual keyboards, extensions) tries to move the document.
4. **`Cmd/Ctrl + scroll` is not touched** — only key-driven scrolling is suppressed.

When adding a new gameplay key, **also add it to `GAMEPLAY_KEYS`**, or the bug returns.

### Special skills (X / C / B)

Each character in `CHARACTERS` has a `skills:{x, c, b?}` map and a matching `skillLabels:{x, c, b?}`. The `b` slot is optional — only the Tank has it today. All three keys dispatch through `triggerSkill(name, dx, dy, mag)` which returns `true` on successful fire so the per-key cooldown only charges on success.

- **X is the universal summon-sword-ally skill** for all three characters (label `BLADE`, 25 s cooldown, defined in `skillCdMax.summon`). It pushes a `sword_ally` entity at the player's position after killing any previous one.
- **C is class-specific**: Soldier `slowmo`, Scout `slowmo`, Tank `wall` (4 s full invuln).
- **B is Tank-only `flameburst`** (label `BURST`, 20 s cooldown, defined in `skillCdMax.flameburst`). Casting sets `player.flameburstTime = 3`; `updatePlaying` then calls `tickFlameburst(dt)` every frame while the timer is positive, which damages enemies inside a radius-36 ring centered on the player (6 DPS scaled by `damageMult` and the DAMAGE powerup) and sprays flame particles. The ring follows the player as they move. Re-casting before the timer expires just refreshes it.

The HUD chip for B is rendered conditionally — `drawSkillHUD()` only pushes a B entry when `ch.skills.b` exists, so Soldier and Scout still show only two chips. The character-select card's skill listing follows the same pattern with `ch.skillLabels.b`. The dispatch in `updatePlaying` is also gated (`if(keys['KeyB'] && player.skillCd.b <= 0 && charSkills.b)`), so adding a B skill to another character is purely a data change in `CHARACTERS`.

The old M-slot was removed; the X/C/B HUD is rendered by `drawSkillHUD()`. Several skill handlers (`dash`, `blink`, `grenade`, `nuke`) remain in `triggerSkill` but are currently unreferenced — leave them for now in case future characters revive them.

### Session changes (recent design decisions)

These changes are recent enough to be worth recording so future passes don't unintentionally regress them:

- **30 levels in 6 boss tiers** — five levels per tier, each tier locked to one boss AI (`bruiser` → `sniper` → `splitter` → `summoner` → `overlord` → `nemesis`). Within a tier the boss AI is identical but each level keeps a unique `bossName` (BRUISER/RAMPAGER/JUGGERNAUT/COLOSSUS/BEHEMOTH for tier 1, etc.); `spawnBoss`'s per-level HP/speed multiplier handles the difficulty gap inside a tier. Victory screen reads "All N bosses fell" using `LEVELS.length` (no hardcoded number).
- **L16-L20 endgame curve** — totals 66→92, rates 0.36→0.28, mixes shed grunt entirely and lean on tank / shooter / charger / exploder. L20 mix has no runners, just the heavies.
- **L21-L30 push the curve further** — totals climb 100→220 and rate tightens 0.27→0.16. L25 onward is also a 3× world (see Coordinate system), so the heavier spawn pressure plays out across a bigger arena. Final boss is L30 ANNIHILATOR — the toughest `nemesis` instance.
- **Level-select grid is 6×5** — `levelBoxRect` uses `bw=26, bh=15, gap=2` to fit 30 boxes between `ys=124` and `y≈207`, leaving room for the HIGH SCORE line at `y=215`. The CLEAR/— second-line text was dropped when boxes shrank from `bh=18` to `bh=15`; the box's green-vs-blue color is now the sole cleared indicator. If you add more levels, this layout will need another reshape.
- **Companion stats tuned up** — HP 6, fire rate 0.25 s, bullet dmg 3 / speed 260 / life 1.5, detection radius 140 units, post-hit invuln 0.85 s. (Was HP 3 / 0.32 s / dmg 1 / speed 220 / radius 110 / invuln 0.7 originally.)
- **Sword ally stats** — HP 4 (was 3), `swingDmg: 5` (was 3), `attackArc` 120°, `attackRange` 24, `attackRate` 0.55 s, 30 s spawn invuln 0.3 s.
- **Tank overall buff pass** — Tank stats raised significantly so it's competitive with Soldier/Scout: `hp: 8→12`, `speed: 80→95`, `damageMult: 1.0→1.2`, `startShield: 3→4`, `shieldMax: 3→5` (tank only), `maxFuel: 8→12`. Flamethrower: `range: 180→210`, `halfAngle: 0.6→0.7` (~40°), `dps: 5→7`. Flamethrower DPS still scales with `damageMult` and the `damageTime` powerup. Tank's `desc` text in `CHARACTERS` updated to `'HEAVY · +20% DAMAGE · FLAMETHROWER (RMB)'`.
- **Tank now has a dedicated default weapon (heavy slug)** — `fireWeapon`'s class-default branch added a `player.char === 'tank'` case BEFORE the soldier-pistol fallthrough. Tank slug: `dmg: 2`, `radius: 3`, `speed: 300`, `life: 1.6`. Same `fireRate` as the pistol (so cadence is unchanged), but each shot does 2× base damage (≈2.4 after `damageMult: 1.2`). The old comment "Tank's left-click is the same as Soldier's pistol" is no longer true — update it if you reshuffle this function.
- **Tank drop pool** — fuel and armor get real slices; both pools sum to 1.0. The fuel-never-drops bug from the prior implementation is fixed.
- **Armor pickup (`armor`)** — "extra protective case". Raises `shieldMax` to 5 (cap was 3), refills shield, grants 1.5 s invuln on grab.
- **Magnet pickup** — was 0.04 weight (≈0.9% per kill). Bumped to 0.06-0.08 (≈1.3-1.8% per kill).
- **Screen shake disabled** — `draw()` no longer applies the translate. Per user preference; combat code still assigns `shakeTime`/`shakeAmt`, so this is a one-line revert.
- **Fuel HUD shows label only** — the numeric fuel value (`'FUEL X.X'`) was replaced with just `'FUEL'`; the bar still shows the ratio visually.
- **Tank gets a B-key flame burst** — `flameburst` skill, 20 s cooldown, 3 s duration. Implemented as a `player.flameburstTime` timer decayed in `updatePlaying` and a `tickFlameburst(dt)` helper next to `fireFlamethrower`. Radius 36, 6 DPS scaled by `damageMult` and the DAMAGE powerup. Universal at first then narrowed to Tank only — Soldier/Scout have no `skills.b` entry so the HUD chip, character-card line, and KeyB dispatch all hide for them.
- **Tank fuel drop weight bumped 0.13 → 0.20** — fuel pickups appear ~50% more often for Tank so the flamethrower stays viable on long levels. The other 14 slots in the Tank pool (health 0.10, slowmo 0.03, score2x 0.02, rocket 0.04, magnet 0.05, …) were shaved to keep the weights summed to exactly 1.0. The non-Tank pool was untouched.
- **Boss HP/speed scale per level** — `spawnBoss` multiplies the base per-kind stats by `1 + levelIdx*0.07` (HP) and `1 + levelIdx*0.015` (speed). At L1 (idx 0) the multiplier is 1.0 so bruiser is unchanged; the L30 ANNIHILATOR has ~515 HP / ~34 speed vs the original 170/24. Without this, the 6-tier reshuffle would have made L26 NEMESIS exactly as tough as L10 — the scaling is what makes each reuse of an AI feel meaningful.

### Coordinate system

World is logical, viewport is 480×270. There are three world-size tiers, picked inside `startLevel(idx)`:

- **L1-L13 (idx ≤ 12)** — 1× world, `worldW = 480, worldH = 270`. Camera stays at (0,0).
- **L14-L24 (13 ≤ idx ≤ 23)** — 2× world, `worldW = 960, worldH = 540`. Camera follows the player.
- **L25-L30 (idx ≥ 24)** — 3× world, `worldW = 1440, worldH = 810`. Camera follows the player.

A camera follows the player on the 2× and 3× tiers. The relevant globals near the top of the script:

- `W, H` — constants, 480×270. The on-screen viewport. **Use for HUD / menu / mouse-screen-space math.**
- `worldW, worldH` — mutable, set in `startLevel(idx)`. The playable arena. **Use for entity clamps, bullet despawn/bounce, spawn-edge calculations, world-center positions, decor placement.**
- `camX, camY` — top-left corner of the camera in world space. Smoothly lerped toward `(player.x - W/2, player.y - H/2)` by `updateCamera(dt)`, clamped so the view never crosses world edges. Stays at `(0,0)` whenever `worldW === W`.

**Mouse coordinates are screen-space.** `mouse.x/y` are in `0..W, 0..H` (the visible canvas), NOT world space. To get the cursor's world position add the camera: `mouse.x + camX, mouse.y + camY`. The player aim angle and Scout's `blink` skill do this; new code that reads the cursor in gameplay must do the same.

**`draw()` flow on game states**: `ctx.save() → translate(-camX, -camY) → drawBackground(theme, idx, worldW, worldH) → drawGame()` (entities + particles only) `→ ctx.restore()`, THEN `drawHUD()` and any overlay (LEVEL_COMPLETE / GAME_OVER / VICTORY). HUD and overlays render un-translated so they stay pinned to the screen. The boss HP bar, "ENEMIES: N" counter, and boss-arrival flash are all screen-space — they don't follow the boss across the arena. `drawBackground` and `drawDecor` scale their decoration counts by `(bw*bh)/(W*H)` so 2× and 3× arenas don't look bare.

`resize()` only scales the canvas element's CSS size — the backing store stays 480×270×PX and the mouse handler rescales pointer coords into the 480×270 screen space. Don't accidentally use `clientX`/`clientY` directly.
