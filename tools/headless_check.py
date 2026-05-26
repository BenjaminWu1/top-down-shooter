#!/usr/bin/env python3
"""Headless runtime smoke-test for index.html.

Unlike validate.py (a pure-stdlib STATIC linter), this actually EXECUTES the
game's JavaScript in a V8 engine with the browser APIs (canvas / DOM / audio /
localStorage / requestAnimationFrame) replaced by a universal no-op stub. It
then drives the real game loop across all 40 levels, force-spawns every mid-boss
and end boss, and directly exercises the boss-ability helpers + maybeElite — so
runtime errors that the in-game try/catch normally swallows (ReferenceError,
TypeError, etc.) surface here as failures.

Requires a JS engine binding:  pip install py_mini_racer
Run:  python tools/headless_check.py   (exits non-zero on any caught error)

It cannot see pixels — visual/aesthetic issues still need a browser reload —
but it proves the code paths run without throwing.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "..", "index.html")

try:
    from py_mini_racer import MiniRacer
except ImportError:
    print("ERROR: needs py_mini_racer  ->  pip install py_mini_racer", file=sys.stderr)
    sys.exit(2)

# --- Browser/host stubs. A single universal Proxy answers any property as a
#     callable, chainable no-op, and numeric-ish props as 0, so we never have to
#     enumerate the canvas/audio API. AudioContext is a real ctor so `new` works.
STUBS = r"""
'use strict';
var __errs = [];
function __makeStub(){
  var fn = function(){ return P; };
  var NUM = {width:1,height:1,currentTime:0,sampleRate:44100,length:0,top:0,left:0,
             right:0,bottom:0,x:0,y:0,value:0,devicePixelRatio:1,innerWidth:960,
             innerHeight:540,clientWidth:960,clientHeight:540,tabIndex:0,scrollX:0,scrollY:0};
  var P = new Proxy(fn, {
    get: function(t, prop){
      if(prop === Symbol.toPrimitive) return function(){ return 0; };
      if(prop === 'toString') return function(){ return ''; };
      if(Object.prototype.hasOwnProperty.call(NUM, prop)) return NUM[prop];
      return P;
    },
    set: function(){ return true; },
    apply: function(){ return P; },
    construct: function(){ return P; }
  });
  return P;
}
var window = globalThis;
var document = __makeStub();
var navigator = __makeStub();
var localStorage = __makeStub();
var performance = { now: function(){ return 0; } };
function requestAnimationFrame(){ return 0; }   // no-op: do NOT auto-run loop()
function setTimeout(){ return 0; }              // browser timers V8 lacks (used by audio)
function clearTimeout(){ return 0; }
function setInterval(){ return 0; }
function clearInterval(){ return 0; }
function addEventListener(){}
function AudioContext(){ return __makeStub(); }
var webkitAudioContext = AudioContext;
var console = {
  log: function(){},
  warn: function(){},
  error: function(){ __errs.push(Array.prototype.join.call(arguments, ' ')); },
  info: function(){}
};
"""

DRIVER = r"""
(function(){
  var report = { errors: [], levels: [], notes: [] };
  function safe(label, fn){
    try { fn(); } catch(e){ report.errors.push(label + ' :: ' + (e && e.stack ? e.stack : e)); }
  }

  // Make audio calls harmless (initAudio normally fires on first click).
  safe('initAudio', function(){ if(typeof initAudio === 'function') initAudio(); });

  // Choose a class + loadout and start a run. Reset the meta-progression profile to a
  // clean default so the run is deterministic and independent of any (stubbed) storage.
  if(typeof DEFAULT_PROFILE === 'function'){ profile = DEFAULT_PROFILE(); }
  selectedChar = 'soldier';
  selectedAssistants = ['drone', 'henchman'];
  safe('startGame', function(){ startGame(); });

  for(var idx = 0; idx < LEVELS.length; idx++){
    safe('startLevel ' + idx, function(){ startLevel(idx); });
    // Phase A: let the wave spawn + all regular/elite AIs run for a while.
    for(var f = 0; f < 150; f++){
      player.hp = player.maxHp;                 // keep alive so state stays PLAYING
      safe('updA L' + idx, function(){ update(1/60); });
      safe('drawA L' + idx, function(){ draw(); });
    }
    // Phase B: force the boss gate — mark the wave fully spawned and clear the
    // living regulars so aliveRegular hits 0 and the boss(es) arrive.
    spawnedCount = levelData.total;
    entities = entities.filter(function(e){ return e.type !== 'enemy' || e.isBoss; });
    // Run ~13s so the mid-boss (50% gate) + end boss spawn AND every ability
    // cooldown (gas 5.5s, exploders 5s, heal 6s, invuln 8s, clone 9s) fires.
    // L31-40 new flow: the end boss is gated behind the mid-boss DYING + a 15-30s
    // gap. Since the headless player never shoots, kill the mid-boss once it's up
    // and zero the gap each frame so the end boss arrives early and its AI still
    // gets the rest of Phase B to run (preserving the old single-boss coverage).
    for(var g = 0; g < 800; g++){
      player.hp = player.maxHp;
      if(levelData.midBoss && midbossSpawned && !midbossDefeated){
        entities.forEach(function(e){ if(e.type === 'enemy' && e.kind === levelData.midBoss) e.dead = true; });
      }
      if(levelData.midBoss && midbossDefeated) bossGapTimer = 0;
      safe('updB L' + idx, function(){ update(1/60); });
      safe('drawB L' + idx, function(){ draw(); });
    }
    report.levels.push({
      idx: idx, boss: levelData.boss, midBoss: levelData.midBoss || null,
      bossSpawned: bossSpawned, midbossSpawned: midbossSpawned,
      entities: entities.length, groundFields: groundFields.length
    });
  }

  // Directly exercise every boss-ability helper on every boss kind (incl. the
  // mid-boss kinds twin/bomber), plus damageEnemy through an active shield, and
  // maybeElite on every regular kind — independent of whether the AI happened
  // to trigger them above.
  var bossKinds = ['bruiser','sniper','splitter','summoner','overlord','nemesis',
                   'reaper','phantom','twin','bomber'];
  levelIdx = 39;
  bossKinds.forEach(function(k){
    safe('abilities ' + k, function(){
      var b = createEnemy(k, 200, 200); b.isBoss = true;
      bossInvuln(b, 0.016);
      b.invulnT = 1.0;
      damageEnemy(b, 5, true);            // must be absorbed, not crash
      b.invulnT = 0;
      bossSummonExploders(b, 99, 3);
      bossSpawnClone(b);
      bossGasBomb(b, 99);
      bossHeal(b, 99);
    });
  });
  var regularKinds = ['grunt','runner','tank','shooter','charger','exploder','swarmer'];
  regularKinds.forEach(function(k){
    safe('maybeElite ' + k, function(){
      var e = createEnemy(k, 100, 100);
      for(var i = 0; i < 50; i++) maybeElite(createEnemy(k, 100, 100));
    });
  });

  // Exercise every draw state (menus / select / overlays) for draw-time errors.
  ['MENU','HOWTO','CHARACTER_SELECT','ASSISTANT_SELECT','SHOP','PARAMETERS','PLAYING',
   'LEVEL_COMPLETE','GAME_OVER','VICTORY'].forEach(function(s){
    if(STATE[s] === undefined){ report.notes.push('no STATE.' + s); return; }
    safe('draw ' + s, function(){ state = STATE[s]; draw(); });
  });

  // PARAMETERS screen reads per-class scaled stats for each tab — exercise all three.
  safe('draw PARAMETERS tabs', function(){
    state = STATE.PARAMETERS;
    ['soldier','scout','tank'].forEach(function(c){ paramChar = c; draw(); });
  });

  // Exercise the CHARACTER STATS window (Tab overlay) for all three classes —
  // its per-class branches read different RMB-pool / regen / damage fields.
  safe('draw stats window', function(){
    state = STATE.PLAYING; showStats = true;
    ['soldier','scout','tank'].forEach(function(c){ player = createPlayer(c); draw(); });
    showStats = false;
  });

  report.consoleErrors = __errs.slice(0, 40);
  return JSON.stringify(report);
})();
"""

# --- Gameplay-BALANCE assertions, computed against the real loaded game data /
#     functions (so they can't drift from the code). Returns [{name,pass,detail}].
DRIVER_BALANCE = r"""
(function(){
  var R = [];
  function check(name, pass, detail){ R.push({name:name, pass:!!pass, detail:detail||''}); }

  // 1) Difficulty curve: total non-decreasing, spawn rate non-increasing across all 40.
  (function(){
    var okT = true, okR = true, badT = '', badR = '';
    for(var i = 1; i < LEVELS.length; i++){
      if(LEVELS[i].total < LEVELS[i-1].total){ okT = false; badT = 'L'+(i+1); }
      if(LEVELS[i].rate  > LEVELS[i-1].rate ){ okR = false; badR = 'L'+(i+1); }
    }
    check('Difficulty curve: enemy total never drops', okT, badT && ('drop at '+badT));
    check('Difficulty curve: spawn rate never rises', okR, badR && ('rise at '+badR));
  })();

  // 2) Mix reachability: every kind listed in every level's mix is actually rolled
  //    by pickWeighted (catches the "weights past cumulative 1.0 are unreachable" bug
  //    class empirically, not just by the static sum).
  (function(){
    var bad = [];
    for(var i = 0; i < LEVELS.length; i++){
      var counts = {};
      LEVELS[i].mix.forEach(function(m){ counts[m[0]] = 0; });
      for(var s = 0; s < 5000; s++){ var k = pickWeighted(LEVELS[i].mix); if(k in counts) counts[k]++; }
      var unreached = Object.keys(counts).filter(function(k){ return counts[k] === 0; });
      if(unreached.length) bad.push('L'+(i+1)+':'+unreached.join('/'));
    }
    check('Mix reachability: every mix kind gets rolled', bad.length === 0, bad.join(' '));
  })();

  // 3) Boss scaling: within each 5-level tier (same boss AI) the spawned boss maxHp
  //    strictly increases, and the L40 boss is the tankiest of all (spawnBoss scaling).
  function spawnedBossHp(kind, idx){
    startLevel(idx);
    entities = entities.filter(function(e){ return e.type === 'player'; });
    spawnBoss(kind);
    var b = entities[entities.length - 1];
    return b ? b.maxHp : -1;
  }
  (function(){
    var tierBad = '', tierOk = true, hps = [];
    for(var i = 0; i < LEVELS.length; i++){
      var hp = spawnedBossHp(LEVELS[i].boss, i);
      hps.push(hp);
      // within-tier (same boss kind as previous level) must strictly increase
      if(i > 0 && LEVELS[i].boss === LEVELS[i-1].boss && hp <= hps[i-1]){ tierOk = false; tierBad = 'L'+(i+1); }
    }
    check('Boss scaling: HP strictly rises within each tier', tierOk, tierBad && ('flat/low at '+tierBad));
    // The spawned maxHp must match the documented spawnBoss formula
    // ceil(base * (1 + idx*0.07)). (NB: the L40 phantom is NOT the absolute
    // tankiest — the L30 nemesis has a higher base HP — by design, so we assert
    // the scaling math, not an HP ranking.)
    var base = spawnedBossHp('phantom', 0);
    var fOk = true, fBad = '';
    [10, 20, 39].forEach(function(idx){
      var want = Math.ceil(base * (1 + idx * 0.07));
      var got = spawnedBossHp('phantom', idx);
      if(got !== want){ fOk = false; fBad += ' idx' + idx + ' want' + want + ' got' + got; }
    });
    check('Boss scaling: matches ceil(base*(1+idx*0.07))', fOk, fBad);
  })();

  // 4) Enemy scaling: a tank grunt is tankier at L40 than at L1 (enemyScale).
  (function(){
    levelIdx = 0;  var lo = createEnemy('tank', 0, 0).maxHp;
    levelIdx = 39; var hi = createEnemy('tank', 0, 0).maxHp;
    check('Enemy scaling: regular HP rises with level', hi > lo, 'L1='+lo+' L40='+hi);
  })();

  // 5) Elite scaling: maybeElite triples HP, enlarges, quadruples score, slows.
  (function(){
    var orig = Math.random; Math.random = function(){ return 0; };  // force promotion
    levelIdx = 39;
    var base = createEnemy('tank', 0, 0);
    var e = createEnemy('tank', 0, 0); maybeElite(e);
    Math.random = orig;
    var ok = e.elite === true
          && e.maxHp === Math.ceil(base.maxHp * 3)
          && e.radius === Math.round(base.radius * 1.6)
          && e.score === base.score * 4
          && Math.abs(e.speed - base.speed * 0.9) < 1e-6;
    check('Elite scaling: 3x HP / 1.6x size / 4x score / slower', ok,
          'elite='+e.elite+' hp '+base.maxHp+'->'+e.maxHp+' r '+base.radius+'->'+e.radius);
  })();

  // 6) Mid-boss data: L31-40 each have a midBoss that is a valid boss kind and
  //    DIFFERS from the end boss; L1-30 have none.
  (function(){
    var bad = [];
    for(var i = 0; i < LEVELS.length; i++){
      var mb = LEVELS[i].midBoss;
      if(i >= 30){
        if(!mb) bad.push('L'+(i+1)+':missing');
        else if(mb === LEVELS[i].boss) bad.push('L'+(i+1)+':==end');
        else { var t = createEnemy(mb, 0, 0); if(!t || !t.isBoss) bad.push('L'+(i+1)+':invalid('+mb+')'); }
      } else if(mb){ bad.push('L'+(i+1)+':unexpected'); }
    }
    check('Mid-boss: L31-40 valid+distinct, L1-30 none', bad.length === 0, bad.join(' '));
  })();

  // 7) Boss-ability LEVEL GATING: each ability must NOT fire one level below its
  //    documented threshold and MUST fire at/above it. Runs the real AI ~12s.
  function runAI(aiFn, kind, idx, damage){
    startLevel(idx);
    entities = entities.filter(function(e){ return e.type === 'player'; });
    groundFields = [];
    player.hp = player.maxHp = 99999; player.invuln = 0;
    var b = createEnemy(kind, worldW/2 - 40, worldH/2);
    b.isBoss = true; b.maxHp = 100000; b.hp = damage ? 50000 : 100000;
    b.phase = 0; b.phaseT = 0; b.fireCooldown = 0;
    entities.push(b);
    var seenInvuln = false;
    for(var f = 0; f < 720; f++){           // ~12s > every ability cooldown
      player.hp = player.maxHp;
      aiFn(b, 1/60);
      if(b.invulnT > 0) seenInvuln = true;
    }
    return { invuln: seenInvuln, heal: b.hp > 50000,
             gas: groundFields.length > 0,
             clone: entities.some(function(e){ return e.isClone; }),
             exploder: entities.some(function(e){ return e.kind === 'exploder'; }) };
  }
  var gates = [
    ['Overlord invuln @L22',    updateOverlord, 'overlord', 20, 21, 'invuln',   false],
    ['Overlord heal @L24',      updateOverlord, 'overlord', 22, 23, 'heal',     true ],
    ['Nemesis gas @L27',        updateNemesis,  'nemesis',  25, 26, 'gas',      false],
    ['Nemesis exploders @L29',  updateNemesis,  'nemesis',  27, 28, 'exploder', false],
    ['Reaper gas @L31',         updateReaper,   'reaper',   29, 30, 'gas',      false],
    ['Reaper clones @L33',      updateReaper,   'reaper',   31, 32, 'clone',    false],
    ['Phantom gas @L37',        updatePhantom,  'phantom',  35, 36, 'gas',      false],
    ['Phantom heal @L38',       updatePhantom,  'phantom',  36, 37, 'heal',     true ],
    ['Phantom exploders @L39',  updatePhantom,  'phantom',  37, 38, 'exploder', false]
  ];
  gates.forEach(function(g){
    var below = runAI(g[1], g[2], g[3], g[6])[g[5]];
    var above = runAI(g[1], g[2], g[4], g[6])[g[5]];
    check(g[0] + ' (off below, on at/above)', below === false && above === true,
          'below='+below+' above='+above);
  });

  // 8) L31-40 boss gap: after the mid-boss DIES the end boss must wait a 15-30s
  //    gap (the two bosses never co-exist), and a trickle of monsters must appear
  //    during that gap so the arena is never empty. Drives the real spawn flow.
  (function(){
    var bad = [];
    [30, 39].forEach(function(idx){
      startLevel(idx);
      state = STATE.PLAYING; paused = false;
      player.hp = player.maxHp = 99999;
      spawnedCount = levelData.total;                          // skip the main wave
      entities = entities.filter(function(e){ return e.type === 'player'; });
      var guard = 0;
      while(!midbossSpawned && guard++ < 120) update(1/60);     // release the mid-boss
      if(!midbossSpawned){ bad.push('L'+(idx+1)+':no-midboss'); return; }
      // Kill the mid-boss; the next tick should open the gap.
      entities.forEach(function(e){ if(e.type==='enemy' && e.kind===levelData.midBoss) e.dead = true; });
      update(1/60);
      if(!midbossDefeated){ bad.push('L'+(idx+1)+':not-defeated'); return; }
      if(bossGapTimer < 15 || bossGapTimer > 30){ bad.push('L'+(idx+1)+':gap='+bossGapTimer.toFixed(1)); return; }
      // 14s in (< the 15s minimum gap): end boss must NOT be up yet; monsters appear.
      var sawMonster = false;
      for(var f = 0; f < 14*60; f++){
        player.hp = player.maxHp;
        update(1/60);
        if(entities.some(function(e){ return e.type==='enemy' && !e.isBoss; })) sawMonster = true;
      }
      if(bossSpawned){ bad.push('L'+(idx+1)+':boss-too-early'); return; }
      if(!sawMonster){ bad.push('L'+(idx+1)+':no-gap-monsters'); return; }
      // Let the rest of the gap (<=30s) elapse: the end boss must then arrive.
      for(var f2 = 0; f2 < 18*60 && !bossSpawned; f2++){ player.hp = player.maxHp; update(1/60); }
      if(!bossSpawned) bad.push('L'+(idx+1)+':boss-never');
    });
    check('Boss gap: end boss waits 15-30s after mid-boss + monsters fill gap',
          bad.length === 0, bad.join(' '));
  })();

  // 9) Meta-progression: XP curve rises; level scaling raises dmg/maxHp, lowers
  //    fireRate, grows the RMB pool (short at L1); slot gating; loadout ownership.
  (function(){
    var saved = profile, ok = true, d = [];
    for(var l = 1; l < 20; l++){ if(xpToNext(l + 1) <= xpToNext(l)){ ok = false; d.push('xp@' + l); break; } }
    profile = DEFAULT_PROFILE();            var p1  = createPlayer('tank');
    profile = DEFAULT_PROFILE(); profile.level = 20; var p20 = createPlayer('tank');
    if(!(p20.damageMult > p1.damageMult)) { ok = false; d.push('dmg'); }
    if(!(p20.maxHp > p1.maxHp))           { ok = false; d.push('hp'); }
    if(!(p20.fireRate < p1.fireRate))     { ok = false; d.push('fire'); }
    if(!(p20.maxFuel > p1.maxFuel))       { ok = false; d.push('rmbGrow'); }
    if(!(p1.maxFuel < 12))                { ok = false; d.push('rmbShort'); }
    profile = DEFAULT_PROFILE(); profile.level = 1;  if(unlockedSlots() !== 0) { ok = false; d.push('slot1'); }
    profile.level = 5;  if(unlockedSlots() !== 1) { ok = false; d.push('slot5'); }
    profile.level = 20; if(unlockedSlots() !== 4) { ok = false; d.push('slot20'); }
    profile = DEFAULT_PROFILE(); profile.level = 20; profile.loadout.x = 'nuke';   // not owned yet
    var lo = resolvePlayerLoadout(); if(lo.x !== null) { ok = false; d.push('unowned'); }
    profile.ownedSkills.push('nuke'); lo = resolvePlayerLoadout();
    if(lo.x !== 'nuke') { ok = false; d.push('owned'); }
    if(lo.f !== 'heal') { ok = false; d.push('healDefault'); }
    profile = saved;
    check('Meta: XP curve + level scaling + slot gating + loadout ownership', ok, d.join(' '));
  })();

  return JSON.stringify(R);
})();
"""


def main():
    src = open(INDEX, encoding="utf-8").read()
    m = re.search(r"<script>(.*)</script>", src, re.S)
    if not m:
        print("ERROR: no <script> block found in index.html", file=sys.stderr)
        return 2
    game_js = m.group(1)

    ctx = MiniRacer()
    ctx.eval(STUBS)
    # The game script starts with its own 'use strict'; that's fine to re-declare.
    ctx.eval(game_js)
    import json
    raw = ctx.eval(DRIVER)
    report = json.loads(raw)
    balance = json.loads(ctx.eval(DRIVER_BALANCE))

    errors = report.get("errors", [])
    console_errors = report.get("consoleErrors", [])
    levels = report.get("levels", [])

    print("Headless runtime check of index.html (V8 + stubbed canvas/DOM)\n")
    print("== Part 1: runtime smoke-test (all 40 levels) ==")
    # Per-level boss-spawn sanity.
    bad_boss = [L for L in levels if not L["bossSpawned"]]
    bad_mid = [L for L in levels if L["midBoss"] and not L["midbossSpawned"]]
    print("Levels simulated:        {}".format(len(levels)))
    print("End boss spawned in all:  {}".format("YES" if not bad_boss else "NO -> " + str([L["idx"]+1 for L in bad_boss])))
    print("Mid-boss spawned (31-40): {}".format("YES" if not bad_mid else "NO -> " + str([L["idx"]+1 for L in bad_mid])))
    max_ent = max((L["entities"] for L in levels), default=0)
    print("Peak entity count:        {}  (600-prune threshold)".format(max_ent))
    if report.get("notes"):
        print("Notes:", report["notes"])

    if console_errors:
        print("\nconsole.error output ({}):".format(len(console_errors)))
        for e in console_errors[:20]:
            print("  !", e[:200])

    if errors:
        print("\nTHROWN ERRORS ({}):".format(len(errors)))
        # De-dupe by first line so 800-frame loops don't print 800 copies.
        seen = set()
        for e in errors:
            key = e.split("\n")[0]
            if key in seen:
                continue
            seen.add(key)
            print("  X", e[:300])

    # Balance assertions.
    print("\n== Part 2: gameplay-balance assertions ==")
    bal_fail = [b for b in balance if not b["pass"]]
    for b in balance:
        print("  [{}] {}{}".format(
            "PASS" if b["pass"] else "FAIL", b["name"],
            "" if b["pass"] else "  -> " + b["detail"]))

    runtime_ok = not errors and not bad_boss and not bad_mid
    print()
    if not runtime_ok:
        reason = "thrown errors" if errors else "a boss never spawned"
        print("RESULT: FAIL (runtime: {})".format(reason))
        return 1
    if bal_fail:
        print("RESULT: FAIL ({} balance assertion(s) failed)".format(len(bal_fail)))
        return 1

    print("RESULT: PASS ({} levels ran clean; {} balance assertions all green)".format(
        len(levels), len(balance)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
