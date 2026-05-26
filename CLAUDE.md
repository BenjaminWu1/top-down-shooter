# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A browser-based top-down arena shooter. **The entire game lives in `index.html`** — vanilla HTML/CSS/JS, no build step, no dependencies, no external assets. All sprites are inline pixel-array data; all SFX are procedurally generated via Web Audio API.

`shooter game.html` is an older untracked draft — ignore it unless asked. The shipped game is `index.html`, served from GitHub Pages at https://benjaminwu1.github.io/top-down-shooter/ (the `.nojekyll` file disables Jekyll on Pages so the raw file is served as-is).

`README.md` is now current (rewritten to match this build); keep it in sync when scope changes. There is also a `Game-Overview.docx` design doc — **keep it in sync when the game changes by adding/adjusting entries in `tools/update_overview.py` and running `python tools/update_overview.py` (needs `pip install python-docx`), not by hand-editing the binary docx**; that script applies curated, idempotent paragraph edits/inserts so re-running is safe. The game has **40 levels grouped into 8 boss tiers of 5 levels each**. It also has a **meta-progression layer** (persistent `shooter_profile` in localStorage): a shared account **Level/XP/Gold**, level-driven base-stat scaling (damage, fire rate, max HP, and the held-RMB "second basic attack" duration), a Gold **SHOP** (ARMORY) for unlocking tiered skills + assistants, and a customizable **LOADOUT** — **F is locked to HEAL** and **X/C/B/V are assignable skill slots that unlock +1 every 5 levels** from a `SKILLS` catalog (so the per-class fixed kits in `CHARACTERS.skills` are now vestigial, kept only for validator C7). The game offers a 5-strong assistant roster (the player **owns** a default `drone` + shop purchases and **equips 0-2** per run) and three **stylistically-distinct** playable classes, each with a class-locked LMB + held-RMB secondary (the historical "5-skill set on X/C/F/B/V" is superseded by the loadout): **Dr.Syed** (class key `soldier`) = 21st-c. rainforest warrior (camo + AK47-on-chest + dagger sprite; pistol LMB + energy-limited **blade**-slash RMB swept over a wide *obtuse* arc, refilled by 'beverage' pickups + slow self-regen, NAPALM/BARRAGE AoE), **Xu Yihui** (class key `scout`) = blue cyberpunk-mech assassin (mech sprite with left bullet-launcher + right laser-launcher; fast SMG + 3× straight-line **hitscan laser-beam** RMB drained from a ~20-shot **power** pool refilled by 'battery' pickups + slow self-regen, BLINK/DASH mobility), **Benjamin Wu** (class key `tank`, the 3rd char) = U.S.-Army flamethrower bruiser (dark-uniform sprite with back fuel-tanks + chest rifle; slug + flamethrower RMB, WALL/BLADE+, high HP). **Space pauses/resumes.** Trust this file and the code, not the README, for current scope.

## Running / "Building"

There is no build step and no JS runtime is required to play. To run the game:

- **Local:** open `index.html` directly in a browser (no server needed).
- **Deploy:** push to `main` — GitHub Pages serves `index.html` from the repo root.

When iterating, reload the browser tab; there is no hot reload.

## Validation

There is one optional, dependency-free static validator: **`tools/validate.py`** (pure Python 3 stdlib — Python is installed; Node is **not**). It is a *linter for the game's documented invariants*, not a runtime/behavioral test (it cannot catch gameplay/AI/draw bugs — manual browser reload is still the only check for those).

- **Run it:** `python tools/validate.py` (from anywhere — it resolves `index.html` relative to its own location). Windows convenience wrapper: `tools\validate.bat`. Exits non-zero if any check FAILs.
- **What it checks:** C1 exactly one `<script>` block · C2 brace/paren/bracket balance (a *heuristic* syntax smoke-check, after stripping comments/strings — not a full JS parser) · C3 `LEVELS` has 40 entries · **C4 every level `mix` sums to 1.0** · **C5 all three `killEnemy` drop pools sum to 1.0** (kinds/weights aligned) · C6 boss tiers form 8 contiguous blocks of 5 in the documented order + every boss kind is in `BOSS_NAMES` · C7 each character's `skills`/`skillLabels` cover the `{x,c,f,b,v}` slots and every skill name has a `skillCdMax` entry · C8 (WARN-only) `GAMEPLAY_KEYS` covers every `keys['…']` code read. C4/C5 guard the two invariants this codebase has actually regressed before (unreachable `mix` entries; the "fuel never drops" bug).
- **CI:** `.github/workflows/validate.yml` runs it on push/PR to `main` (GitHub's Python, no local install). It is a **signal only** — it does not gate the Pages deploy, so a red check never takes the live site down.
- **When you change `LEVELS`, the drop pools, the skill set, or `GAMEPLAY_KEYS`, run the validator** before committing; if you add a new invariant worth guarding, add a `check(...)` to `tools/validate.py`.

There is also an **optional headless runtime + balance check: `tools/headless_check.py`**. Unlike `validate.py` (static), it actually *executes* the game's JS in a V8 engine (`pip install py_mini_racer`) with the canvas/DOM/audio replaced by no-op stubs. **Part 1** drives `update()`/`draw()` across all 40 levels, force-spawns every mid-boss + end boss, and directly calls the boss-ability helpers + `maybeElite` + every draw state — catching runtime errors the in-game `try/catch` swallows (ReferenceError/TypeError, a renamed-but-still-called function, etc.). **Part 2** asserts gameplay-balance properties against the live data/functions: difficulty curve (total non-decreasing, rate non-increasing), empirical mix reachability (every mix kind actually gets rolled by `pickWeighted`), boss/enemy/elite scaling, mid-boss validity (L31-40 distinct+valid, L1-30 none), **boss-ability level-gating** (each ability is off one level below its threshold and on at/above it), the **three-phase scaling curve** (`difficultyRamp`/`enemyScale`/`bossHpScale`/`bossSpdScale` strictly rise + are continuous + are L1 no-ops), **level-gated drop variety** (low levels never drop a kind outside their allow-set; advanced kinds unlock at L25+), the **RMB resource logic** (all three pools regen while RMB is held + arm the 1 s `rmbLockT` lockout when emptied, which then blocks firing), and **assistant level scaling** (`assistLevelFrac` 0.35→1.0; each ally's HP/damage rises L1→L10). It can't see pixels, so visual/aesthetic correctness still needs a browser reload. It is **not** wired into CI (CI stays stdlib-only); run it locally after logic/balance changes: `python tools/headless_check.py`. When you add a new ability/level-gate or tuning lever worth guarding, add a `check(...)` to its `DRIVER_BALANCE`.

## Git workflow

**STANDING INSTRUCTION — commit and push are PRE-AUTHORIZED; do them automatically, do NOT ask first.** As you do work in this repo, committing each finished change to git and pushing it to GitHub (`git push origin main`) is a required part of the work, not an optional extra. This overrides any default "only commit/push when the user explicitly asks" behavior: in THIS repo the user has standing-authorized it, so just do it every time you finish a coherent unit of work — never let changes pile up uncommitted while waiting for permission. (You still follow the Hard rules below — e.g. never force-push, never commit secrets.)

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

## Detailed docs

The deep reference material is split into focused files under `docs/`, imported here so Claude Code still loads all of it automatically each session (behavior is identical to keeping it inline — the file is just broken into smaller pieces):

- `docs/architecture.md` — the `index.html` section-by-section walkthrough (1–15), the "Adding things" quick reference, and the coordinate/camera system.
- `docs/systems.md` — input & focus handling, the X/C/F/B/V special skills, the per-class right-mouse secondaries, and pause.
- `docs/session-changes.md` — the running changelog of recent design decisions, so future passes don't regress them.

@docs/architecture.md
@docs/systems.md
@docs/session-changes.md
