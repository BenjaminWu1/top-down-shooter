#!/usr/bin/env python3
"""
Sync Game-Overview.docx with the current game (index.html).

A small, repeatable maintenance tool. It opens the Word doc with python-docx and
applies a curated list of TARGETED edits:

  * REPLACEMENTS - rewrite a whole paragraph, located by a unique substring of
    its current text (paragraph STYLE is preserved; the text is replaced).
  * INSERTS      - add new bullet paragraphs immediately before a heading.

It is IDEMPOTENT, so re-running after future game changes is safe:
  * a replacement whose "find" text is already gone is reported "already current"
    and skipped (pick "find" substrings that do NOT appear in the new text);
  * an insert whose leading text already exists in the doc is not duplicated.

When the game changes again, DON'T hand-edit the docx - add an entry here and
re-run:  python tools/update_overview.py

Requires:  pip install python-docx     (NOT stdlib - unlike tools/validate.py)
"""
import os
import sys

try:
    import docx
except ImportError:
    print("ERROR: python-docx is not installed. Run:  pip install python-docx",
          file=sys.stderr)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.normpath(os.path.join(HERE, "..", "Game-Overview.docx"))

# ---------------------------------------------------------------------------
# Edits. Each REPLACEMENTS entry is (find_substring, new_full_paragraph_text).
# The find_substring must uniquely identify ONE paragraph and must NOT occur in
# the new text (so a second run is a no-op).
# ---------------------------------------------------------------------------
REPLACEMENTS = [
    # 1. The big picture - refresh the line count.
    ("index.html (~4,726 lines)",
     "The entire game is one file: index.html (~4,943 lines). One <script> block, "
     "vanilla JS, no build, no dependencies, no external assets. Sprites are inline "
     "ASCII-art arrays; all SFX are synthesized via Web Audio. It deploys by pushing "
     "to main (GitHub Pages serves the raw file)."),

    # 2. Canvas/world/camera - 4 tiers + MAP_EXPAND, camera now on every tier.
    ("Three world-size tiers",
     "Four world-size tiers, chosen in startLevel(idx) via worldScale = floor(idx/10)+1 "
     "and then enlarged by a single constant MAP_EXPAND = 1.15 (about 1.32x area), "
     "rounded: L1-L10 = 552x311, L11-L20 = 1104x621, L21-L30 = 1656x932, "
     "L31-L40 = 2208x1242. Arena AREA grows with the block. Because even the smallest "
     "tier now exceeds the 480x270 viewport, the camera follows the player on EVERY "
     "tier (updateCamera collapses to 0,0 only when there is no room to scroll). Each "
     "10-level block also gets a distinct theme: forest -> lava -> ice -> void."),

    # 7. Weapons - fireWeapon no longer a form-changing cascade; enhancers only.
    ("fixed priority cascade: rocket",
     "fireWeapon(mx,my) ALWAYS fires the class basic attack - powerups NEVER change its "
     "form, they only ENHANCE it. Four timed (~8s) enhancers stack: rapidTime halves "
     "cooldown, damageTime doubles damage (with damageMult), pierceTime sets the bullet "
     "pierce flag (shots punch through enemies), multiTime fires a parallel DOUBLE shot "
     "(two bullets offset +/-3 perpendicular to aim, same projectile). Class defaults: "
     "Scout blue-dot SMG (dmg 0.85, cd 0.06), Tank slug (dmg 2, radius 3), Soldier "
     "pistol (dmg 1)."),

    # 7. Bullet flags - plasma combo gone; homing/bounces are enemy-only now.
    ("Plasma = pierce + bounces",
     "Bullet flags (createBullet): pierce (uses hitSet, does not die on hit), explosive "
     "(explode()), homing (enemy bullets steer toward the player), bounces (reflects off "
     "edges, clears hitSet), isGrenade, fromAlly. The homing/bounces flags are now used "
     "only by ENEMY AI - the old player rocket/laser/plasma weapons were removed and "
     "their bullet sprites are orphaned."),

    # 7. Pickups - new enhancer set, removed the 6 form-changers.
    ("Pickups (applyPickup): equipment - health, spread",
     "Pickups (applyPickup): WEAPON ENHANCERS (timed ~8s, never change the attack's "
     "form) - rapid (half cooldown), pierce (shots punch through), multi (single -> "
     "double shot), damage (2x); defenses - health, shield, armor; utility powerups - "
     "speed, slowmo, score2x, magnet; class resources - fuel, beverage, battery. The 6 "
     "old form-changing weapons (rocket/laser/plasma/minigun/spread/homing) were removed "
     "as pickups. Three drop pools in killEnemy (Tank->fuel, Soldier->beverage, "
     "Scout->battery), each MUST sum to 1.0 (validator C5). 22% drop chance per non-boss "
     "kill (55% for elite mini-bosses). Bosses give a guaranteed enhancer/defense drop "
     "plus a health."),

    # 9. Bosses - updateTwin/updateBomber are now the mid-bosses, not orphaned.
    ("updateTwin and updateBomber (TWIN STRIKER / BOMBARDIER) are defined but orphaned",
     "updateTwin and updateBomber are no longer orphaned - they are the L31-L40 "
     "MID-BOSSES (see the mid-boss bullets below). Each L31-40 level carries a midBoss "
     "field (twin/bomber/splitter/reaper), a DIFFERENT kind than its end boss."),

    # 11. Draw/HUD - enemy counter removed; enhancer chips above the RMB bar.
    ("Boss HP bar, enemy counter, arrival flash are all screen-space",
     "draw() flow on game states: save -> translate(-camX,-camY) -> drawBackground -> "
     "drawGame() (entities + particles) -> restore, then un-translated drawHUD() + "
     "overlays. The boss HP bar and boss-arrival flash are screen-space. (The on-screen "
     "ENEMIES-left counter was removed.) The four basic-attack enhancer chips "
     "(RAPID/PIERCE/MULTI/DMG) render top-left, stacked ABOVE the RMB resource bar "
     "(FUEL/ENERGY/POWER); movement/utility buffs sit in the bottom-left strip."),

    # 12. Validation - mention the headless runtime+balance check too. (The "find"
    # phrase must NOT recur in the new text, or this re-fires every run.)
    ("it does not gate the deploy",
     "tools/validate.py (pure stdlib) is a static invariant linter (not runtime): one "
     "<script>, brace balance, 40 levels, every mix sums to 1.0 (C4), all 3 drop pools "
     "sum to 1.0 (C5), boss tiers, skill wiring, GAMEPLAY_KEYS coverage. Run "
     "python tools/validate.py after editing LEVELS, drop pools, skills, or keys; CI "
     "runs it on push as a signal only (it never blocks the Pages deploy). There is "
     "ALSO an optional (non-CI) runtime + balance check, tools/headless_check.py (needs "
     "pip install py_mini_racer): it executes the game in V8 with a stubbed canvas/DOM "
     "across all 40 levels and asserts ~18 balance properties - including the new "
     "'end boss waits 15-30s after the mid-boss dies, with monsters filling the gap'."),

    # "Things to keep in mind" - the cascade reminder is obsolete; enhancers only.
    ("The weapon priority cascade in fireWeapon",
     "Weapon pickups only ENHANCE the basic attack (rapid/pierce/multi/damage) - they "
     "must NEVER change its projectile form."),

    # 3. STATE machine - SHOP state added.
    ("CHARACTER_SELECT, ASSISTANT_SELECT. Both update() and draw() dispatch",
     "STATE enum: MENU, HOWTO, PLAYING, LEVEL_COMPLETE, GAME_OVER, VICTORY, "
     "CHARACTER_SELECT, ASSISTANT_SELECT, SHOP. Both update() and draw() dispatch on "
     "the state variable."),

    # 3. Run setup flow - now a loadout screen + shop, not 'pick exactly 2'.
    ("ASSISTANT_SELECT (pick exactly 2 of 5)",
     "Run setup flow: MENU (pick level) -> CHARACTER_SELECT (pick class) -> "
     "ASSISTANT_SELECT (the LOADOUT screen: equip 0-2 OWNED assistants + assign "
     "owned skills to X/C/B/V) -> PLAYING. SHOP (the ARMORY) opens from a lower-left "
     "MENU button. The real entry point is startSelectedRun() (uses selectedChar + "
     "selectedLevel + the persistent profile)."),

    # 5. Player classes - active skills are now a loadout, not the fixed kit.
    # (find must NOT recur in the new text, or it re-fires every run.)
    ("off them. Display names and live stats:",
     "Three classes; class keys never change (soldier/scout/tank) so all logic keys "
     "off them. Each keeps a class-locked LMB + held-RMB; the active X/C/B/V skills "
     "are now a PROFILE LOADOUT (F=HEAL locked, +1 slot per 5 levels) drawn from the "
     "SKILLS catalog, NOT the per-class CHARACTERS.skills kit (now vestigial / kept "
     "only for validator C7). Display names and live stats:"),

    # 10. Allies - owned + equip 0..2, not forced-2.
    ("player picks exactly 2 (selectedAssistants)",
     "Roster in ASSISTANTS (drone, henchman, nunchaku, bomber, poison); the player "
     "OWNS a default drone + any bought in the SHOP, and EQUIPS 0-2 of them on the "
     "loadout screen (profile.equippedAssistants; default removable - the old "
     "exactly-2 rule is gone). startSelectedRun seeds selectedAssistants from the "
     "profile; spawned at run start (spawnSelectedAssistants) and rebuilt each level "
     "(refreshAssistants - survivors refilled, dead recreated)."),
]

# INSERTS: bullets added immediately before the paragraph whose text contains the
# heading key. (before_heading, [bullet_text, ...])
INSERTS = [
    ("6. RMB secondaries", [
        "META-PROGRESSION (persistent): one shared account profile in localStorage "
        "(shooter_profile) - level, XP, gold, owned skills + assistants, the X/C/B/V "
        "loadout, and equipped assistants. XP earned on ANY character credits the one "
        "profile, so all characters level together. loadProfile() guards a non-string "
        "(headless stubs localStorage as a Proxy).",

        "LEVELING + SCALING: XP from kills (small, accrued) + level-clear/victory "
        "(banked); xpToNext grows geometrically (cap 40). applyLevelScaling() at run "
        "start raises base damage, fire rate / attack speed, max HP, and the held-RMB "
        "'second basic attack' DURATION (its fuel/energy/power pool starts short and "
        "grows with level). Drop rate also scales up with level (gate only).",

        "SHOP (STATE.SHOP, the ARMORY): spend Gold on tiered skills (cheap/small -> "
        "expensive/big) and extra assistants; purchases persist. LOADOUT screen: F is "
        "locked to HEAL, X/C/B/V unlock +1 per 5 levels and are filled from owned "
        "skills; the persistent LV/XP bar + gold show upper-right on every menu.",
    ]),
    ("10. Allies", [
        "Reusable boss abilities (escalate by levelIdx, no-op for clones): bossInvuln "
        "(1.2s damage-absorb shield), bossSummonExploders, bossSpawnClone, bossGasBomb, "
        "bossHeal. The gas pool (bossGasBomb) spawns on the player but now ARMS for 0.5s "
        "- a pulsing yellow telegraph ring that deals NO damage - so you can step out "
        "before it goes live (no 100%-hit instant chip).",

        "L31-L40 mid-boss + gap: a mid-boss (twin/bomber/splitter/reaper, a different "
        "kind than the end boss) spawns at 50% spawn progress. The end boss NEVER "
        "co-exists with it - it is held back until the mid-boss DIES plus a 15-30s gap "
        "(bossGapTimer), during which a trickle of monsters keeps spawning so the arena "
        "is never empty.",
    ]),
]


def set_paragraph_text(p, text):
    """Replace a paragraph's text while keeping its paragraph style. Collapses to a
    single run, preserving the first run's character formatting where possible."""
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(text)


def main():
    if not os.path.exists(DOCX):
        print("ERROR: not found: " + DOCX, file=sys.stderr)
        return 2
    doc = docx.Document(DOCX)
    changed = 0

    # --- Replacements ---
    for find, new in REPLACEMENTS:
        hit = next((p for p in doc.paragraphs if find in p.text), None)
        if hit is not None:
            set_paragraph_text(hit, new)
            changed += 1
            print("[edit] " + find[:60])
        else:
            # Either already updated (idempotent re-run) or the doc drifted.
            already = any(new[:40] in p.text for p in doc.paragraphs)
            print(("[ok  ] already current: " if already else "[MISS] not found: ")
                  + find[:60])

    # --- Inserts (idempotent: skip a bullet whose lead text already exists) ---
    for heading, bullets in INSERTS:
        target = next((p for p in doc.paragraphs if heading in p.text), None)
        if target is None:
            print("[MISS] heading not found: " + heading)
            continue
        existing = [p.text for p in doc.paragraphs]
        for b in bullets:
            if any(b[:45] in e for e in existing):
                print("[ok  ] bullet already present: " + b[:50])
                continue
            target.insert_paragraph_before(b, style="List Bullet")
            changed += 1
            print("[add ] bullet before '%s': %s" % (heading, b[:50]))

    doc.save(DOCX)
    print("\nSaved %s (%d change(s) this run)." % (os.path.basename(DOCX), changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
