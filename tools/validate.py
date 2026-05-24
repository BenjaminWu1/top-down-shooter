#!/usr/bin/env python3
"""
Static validator / linter for the top-down-shooter game.

The whole game is one file (index.html: vanilla HTML/CSS/JS, no build step, no
dependencies). No JS runtime is installed and the code is not modularized, so
true unit tests are not practical here. Instead this script statically checks
the numeric INVARIANTS that CLAUDE.md says have caused real bugs -- weighted
`mix` lists and the three drop pools MUST each sum to 1.0, LEVELS must hold 40
entries in 8 boss tiers, every character skill must be wired to a cooldown --
plus a brace-balance syntax smoke-check.

Pure Python 3 standard library: no pip installs. Prints PASS/FAIL/WARN per
check and exits non-zero if any check FAILs, so it works as a manual gate and
in CI alike. WARN does not fail the run.

Usage:
    python tools/validate.py [path/to/index.html]

If no path is given, index.html is resolved relative to this script (repo root),
so it works from any working directory and on the CI runner.
"""
import re
import sys
from pathlib import Path

EPS = 1e-6

# Documented boss-tier order: 8 tiers of 5 levels each (CLAUDE.md / LEVELS).
TIER_ORDER = ['bruiser', 'sniper', 'splitter', 'summoner',
              'overlord', 'nemesis', 'reaper', 'phantom']
EXPECTED_LEVELS = 40
TIER_SIZE = 5

# Skill slots every character is expected to define.
SKILL_SLOTS = {'x', 'c', 'f', 'b', 'v'}

_failures = []
_warnings = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not ok:
        _failures.append(name)
    return ok


def warn(name, detail=""):
    print(f"[WARN] {name}" + (f" -- {detail}" if detail else ""))
    _warnings.append(name)


# ---------------------------------------------------------------------------
# Load + extract the single <script> block
# ---------------------------------------------------------------------------
def load_html(argv):
    if len(argv) > 1:
        path = Path(argv[1])
    else:
        path = Path(__file__).resolve().parent.parent / "index.html"
    if not path.is_file():
        print(f"[FAIL] cannot find index.html at {path}")
        sys.exit(2)
    return path.read_text(encoding="utf-8"), path


def line_of(text, offset):
    """1-based line number of a character offset in text."""
    return text.count("\n", 0, offset) + 1


# ---------------------------------------------------------------------------
# C2 helper: blank out comments + string literals (preserving newlines) so a
# brace-balance walk ignores braces that live inside strings/comments.
# ---------------------------------------------------------------------------
def strip_comments_strings(code):
    out = []
    i, n = 0, len(code)
    state = "code"   # code | line_comment | block_comment | string
    quote = ""
    while i < n:
        c = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line_comment"; out.append("  "); i += 2; continue
            if c == "/" and nxt == "*":
                state = "block_comment"; out.append("  "); i += 2; continue
            if c in ("'", '"', "`"):
                state = "string"; quote = c; out.append(" "); i += 1; continue
            out.append(c); i += 1; continue
        if state == "line_comment":
            if c == "\n":
                state = "code"; out.append("\n")
            else:
                out.append(" ")
            i += 1; continue
        if state == "block_comment":
            if c == "*" and nxt == "/":
                state = "code"; out.append("  "); i += 2; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        # state == "string"
        if c == "\\":
            out.append("  "); i += 2; continue   # skip the escaped character
        if c == quote:
            state = "code"; out.append(" "); i += 1; continue
        out.append("\n" if c == "\n" else " "); i += 1; continue
    return "".join(out)


def check_brace_balance(code, base_line):
    """base_line = the HTML line where the script content starts, so reported
    line numbers point into index.html, not the extracted substring."""
    stripped = strip_comments_strings(code)
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = set("([{")
    stack = []
    line = 1
    for ch in stripped:
        if ch == "\n":
            line += 1
            continue
        if ch in opens:
            stack.append((ch, line))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                abs_line = base_line + line - 1
                return False, f"unexpected '{ch}' at line {abs_line}"
            stack.pop()
    if stack:
        oc, ol = stack[-1]
        return False, f"unclosed '{oc}' opened at line {base_line + ol - 1}"
    return True, ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def main():
    html, path = load_html(sys.argv)
    print(f"Validating {path}\n")

    # C1 -- exactly one <script> block.
    scripts = list(re.finditer(r"<script[^>]*>(.*?)</script>", html, re.S))
    if not check("C1 single <script> block", len(scripts) == 1,
                 f"found {len(scripts)}"):
        # Without a clean single block, the rest of the parsing is unreliable.
        return finish()
    code = scripts[0].group(1)
    base_line = line_of(html, scripts[0].start(1))

    # C2 -- brace/paren/bracket balance (syntax smoke-check; heuristic).
    ok, detail = check_brace_balance(code, base_line)
    check("C2 brackets balanced (syntax smoke-check)", ok, detail)

    # --- pull out the data blocks we validate ---
    levels_m = re.search(r"const\s+LEVELS\s*=\s*\[(.*?)\];", code, re.S)
    if not check("C3 LEVELS block present", levels_m is not None):
        return finish()
    levels_block = levels_m.group(1)
    level_objs = re.findall(r"\{[^{}]*\}", levels_block)   # each level is brace-flat

    # C3 -- LEVELS count == 40.
    check(f"C3 LEVELS has {EXPECTED_LEVELS} entries",
          len(level_objs) == EXPECTED_LEVELS, f"found {len(level_objs)}")

    # C4 -- every mix sums to 1.0. Only mix uses ['kind',number] pairs, so we can
    # sum those numbers directly from each level string.
    bad_mix = []
    for idx, lvl in enumerate(level_objs, start=1):
        nums = re.findall(r"\[\s*'[a-z_]+'\s*,\s*([0-9.]+)\s*\]", lvl)
        if not nums:
            bad_mix.append(f"L{idx}: no mix pairs")
            continue
        s = sum(float(x) for x in nums)
        if abs(s - 1.0) > EPS:
            bad_mix.append(f"L{idx}: sum={s:.4f}")
    check("C4 every level mix sums to 1.0", not bad_mix, "; ".join(bad_mix))

    # C6 -- boss tiers: 8 contiguous blocks of 5 in the documented order, and
    # every boss kind is a key in BOSS_NAMES. (Run before C5 so we can reuse the
    # boss list; numbered C6 to match the plan.)
    bosses = [re.search(r"boss:\s*'([a-z]+)'", lvl).group(1)
              if re.search(r"boss:\s*'([a-z]+)'", lvl) else None
              for lvl in level_objs]
    expected = [TIER_ORDER[i // TIER_SIZE] for i in range(len(level_objs))]
    tier_detail = ""
    if bosses != expected:
        diffs = [f"L{i+1}:{b}!={e}" for i, (b, e) in enumerate(zip(bosses, expected)) if b != e]
        tier_detail = "; ".join(diffs[:6]) + (" ..." if len(diffs) > 6 else "")
    check("C6 boss tiers (8 x 5, documented order)", bosses == expected, tier_detail)

    boss_names_m = re.search(r"const\s+BOSS_NAMES\s*=\s*\{(.*?)\};", code, re.S)
    boss_keys = set(re.findall(r"(\w+)\s*:", boss_names_m.group(1))) if boss_names_m else set()
    missing_names = sorted({b for b in bosses if b and b not in boss_keys})
    check("C6b every boss kind has a BOSS_NAMES entry",
          not missing_names, ", ".join(missing_names))

    # C5 -- the three drop pools in killEnemy each sum to 1.0, kinds/weights aligned.
    ke_start = code.find("function killEnemy(")
    ke_end = code.find("\nfunction ", ke_start + 1)
    body = code[ke_start:ke_end] if ke_start != -1 else ""
    kinds_arrs = re.findall(r"kinds\s*=\s*\[([^\]]*)\]", body)
    weights_arrs = re.findall(r"weights\s*=\s*\[([^\]]*)\]", body)
    pool_detail = []
    pool_ok = True
    if len(kinds_arrs) != 3 or len(weights_arrs) != 3:
        pool_ok = False
        pool_detail.append(f"expected 3 pools, found kinds={len(kinds_arrs)} weights={len(weights_arrs)}")
    else:
        names = ["tank", "soldier", "scout/default"]
        for nm, k, w in zip(names, kinds_arrs, weights_arrs):
            kn = re.findall(r"'([^']+)'", k)
            wn = [float(x) for x in re.findall(r"[0-9]*\.?[0-9]+", w)]
            s = sum(wn)
            if abs(s - 1.0) > EPS:
                pool_ok = False
                pool_detail.append(f"{nm} sum={s:.4f}")
            if len(kn) != len(wn):
                pool_ok = False
                pool_detail.append(f"{nm} kinds({len(kn)})!=weights({len(wn)})")
    check("C5 all 3 drop pools sum to 1.0 (kinds/weights aligned)",
          pool_ok, "; ".join(pool_detail))

    # C7 -- character skills wired: each class has skills+skillLabels over the
    # same slots, and every skill name has a skillCdMax entry.
    chars_m = re.search(r"const\s+CHARACTERS\s*=\s*\{(.*)\n\};", code, re.S)
    cd_m = re.search(r"skillCdMax\s*:\s*\{([^}]*)\}", code)
    skill_names = set()
    c7_detail = []
    c7_ok = True
    if not chars_m or not cd_m:
        c7_ok = False
        c7_detail.append("CHARACTERS or skillCdMax block not found")
    else:
        cd_keys = set(re.findall(r"(\w+)\s*:", cd_m.group(1)))
        # Each class: name:'...' then skills:{...} and skillLabels:{...}
        skills_blocks = re.findall(r"skills:\s*\{([^}]*)\}", chars_m.group(1))
        labels_blocks = re.findall(r"skillLabels:\s*\{([^}]*)\}", chars_m.group(1))
        if len(skills_blocks) != 3 or len(labels_blocks) != 3:
            c7_ok = False
            c7_detail.append(f"found {len(skills_blocks)} skills / {len(labels_blocks)} skillLabels blocks (want 3 each)")
        for i, (sb, lb) in enumerate(zip(skills_blocks, labels_blocks)):
            s_keys = set(re.findall(r"(\w+)\s*:\s*'", sb))
            l_keys = set(re.findall(r"(\w+)\s*:\s*'", lb))
            if s_keys != SKILL_SLOTS:
                c7_ok = False
                c7_detail.append(f"class#{i} skills slots {sorted(s_keys)} != {sorted(SKILL_SLOTS)}")
            if l_keys != s_keys:
                c7_ok = False
                c7_detail.append(f"class#{i} skillLabels slots {sorted(l_keys)} != skills {sorted(s_keys)}")
            for nm in re.findall(r":\s*'([^']+)'", sb):
                skill_names.add(nm)
        missing_cd = sorted(n for n in skill_names if n not in cd_keys)
        if missing_cd:
            c7_ok = False
            c7_detail.append("no skillCdMax for: " + ", ".join(missing_cd))
    check("C7 character skills wired to cooldowns", c7_ok, "; ".join(c7_detail))

    # C8 -- GAMEPLAY_KEYS coverage (best-effort, WARN-only). Every keyboard-code
    # read via keys['<code>'] should be in the GAMEPLAY_KEYS set.
    gk_m = re.search(r"GAMEPLAY_KEYS\s*=\s*new\s+Set\(\[([^\]]*)\]", code)
    if gk_m:
        gk = set(re.findall(r"'([^']+)'", gk_m.group(1)))
        referenced = set(re.findall(r"keys\[\s*'([A-Za-z0-9]+)'\s*\]", code))
        kb_shape = re.compile(r"^(Key[A-Z]|Arrow(Up|Down|Left|Right)|Space|Digit[0-9])$")
        missing = sorted(k for k in referenced if kb_shape.match(k) and k not in gk)
        if missing:
            warn("C8 GAMEPLAY_KEYS coverage", "keys read but not in set: " + ", ".join(missing))
        else:
            check("C8 GAMEPLAY_KEYS covers all keys read", True)
    else:
        warn("C8 GAMEPLAY_KEYS coverage", "GAMEPLAY_KEYS set not found")

    return finish()


def finish():
    print()
    if _failures:
        print(f"RESULT: FAIL ({len(_failures)} failed, {len(_warnings)} warning(s))")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print(f"RESULT: PASS (all checks green, {len(_warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
