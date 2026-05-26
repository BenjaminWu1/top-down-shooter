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

  // Choose a class + loadout and start a run.
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
    for(var g = 0; g < 800; g++){
      player.hp = player.maxHp;
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
  ['MENU','HOWTO','CHARACTER_SELECT','ASSISTANT_SELECT','PLAYING',
   'LEVEL_COMPLETE','GAME_OVER','VICTORY'].forEach(function(s){
    if(STATE[s] === undefined){ report.notes.push('no STATE.' + s); return; }
    safe('draw ' + s, function(){ state = STATE[s]; draw(); });
  });

  report.consoleErrors = __errs.slice(0, 40);
  return JSON.stringify(report);
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

    errors = report.get("errors", [])
    console_errors = report.get("consoleErrors", [])
    levels = report.get("levels", [])

    print("Headless runtime check of index.html (V8 + stubbed canvas/DOM)\n")
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
        print("\nRESULT: FAIL")
        return 1

    if bad_boss or bad_mid:
        print("\nRESULT: FAIL (a boss never spawned)")
        return 1

    print("\nRESULT: PASS (ran all 40 levels + all boss abilities, no exceptions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
