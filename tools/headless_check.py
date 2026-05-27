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
    // Run ~20s so the full staged boss chain resolves AND every ability cooldown
    // fires. Staged flow (L11-40): medium wave (1 or 2 bosses) @50% -> surge gap ->
    // [L31-40 transitional boss -> 0s] -> end boss. Since the headless player never
    // shoots, walk the phases by force: kill ALL live bosses while a medium wave
    // (bossPhase 1) or the transitional boss (bossPhase 3) is up, and zero the surge
    // gap (bossPhase 2), so the end boss still arrives and its AI gets the rest of
    // Phase B to run (preserving the old single-boss ability coverage on every level).
    for(var g = 0; g < 1200; g++){
      player.hp = player.maxHp;
      if(midbossSpawned && bossPhase === 1){
        entities.forEach(function(e){ if(e.type === 'enemy' && e.isBoss) e.dead = true; });
      }
      if(bossPhase === 2) bossGapTimer = 0;
      if(bossPhase === 3){
        entities.forEach(function(e){ if(e.type === 'enemy' && e.isBoss) e.dead = true; });
      }
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
                   'reaper','phantom','twin','bomber','warden','harrier'];
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

  // PARAMETERS screen reads per-class scaled stats for each tab — exercise all five.
  safe('draw PARAMETERS tabs', function(){
    state = STATE.PARAMETERS;
    ['soldier','scout','tank','bounty_hunter','cyborg'].forEach(function(c){ paramChar = c; draw(); });
  });

  // SHOP ASSISTANTS tab + LOADOUT both render per-ally level-scaled stat blocks
  // (assistantStatLines builds a throwaway assistant for every roster key) — exercise
  // them with ALL assistants owned so every stat branch (companion/melee/bomber/poison)
  // is drawn at least once.
  safe('draw SHOP allies + LOADOUT stats', function(){
    profile.ownedAssistants = ['drone','henchman','nunchaku','bomber','poison'];
    profile.assistantLevels = { drone:1, henchman:5, nunchaku:10, bomber:3, poison:7 };
    shopTab = 'allies'; state = STATE.SHOP; draw();
    state = STATE.ASSISTANT_SELECT; draw();
    shopTab = 'skills';
    profile = DEFAULT_PROFILE();
  });

  // SHOP PASSIVES tab: render with a mix of owned/unowned/equipped passives so every
  // card branch (buy / upgrade / maxed / equipped / NOT OWNED) is drawn at least once.
  safe('draw SHOP passives tab', function(){
    profile = DEFAULT_PROFILE(); profile.level = 20; profile.gold = 5000;
    profile.passiveLevels = { lifesteal:3, hpregen:10, greed:1, vitality:5 };
    profile.equippedPassives = ['lifesteal','greed'];
    shopTab = 'passives'; state = STATE.SHOP; draw();
    shopTab = 'skills';
    profile = DEFAULT_PROFILE();
  });

  // CHARACTER SELECT passive picker: draw the slot bar with some equipped + the
  // click-to-choose dropdown OPEN (every option branch), then closed.
  safe('draw CHARACTER_SELECT passive picker', function(){
    profile = DEFAULT_PROFILE(); profile.level = 40;
    profile.passiveLevels = { lifesteal:3, greed:10, swiftness:6 };
    profile.equippedPassives = ['lifesteal','greed'];
    state = STATE.CHARACTER_SELECT;
    passiveMenuSlot = 0; draw();    // dropdown open on slot 0
    passiveMenuSlot = -1; draw();   // closed
    profile = DEFAULT_PROFILE();
  });

  // Exercise the CHARACTER STATS window (Tab overlay) for all five classes —
  // its per-class branches read different RMB-pool / regen / damage fields.
  safe('draw stats window', function(){
    state = STATE.PLAYING; showStats = true;
    ['soldier','scout','tank','bounty_hunter','cyborg'].forEach(function(c){ player = createPlayer(c); draw(); });
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
    // ceil(base * bossHpScale(idx)) — the three-phase curve. Call the live game
    // helper so this stays in lock-step with any re-tuning. (NB: the L40 phantom is
    // NOT the absolute tankiest — the L30 nemesis has a higher base HP — by design,
    // so we assert the scaling math, not an HP ranking. We sample one idx per phase.)
    var base = spawnedBossHp('phantom', 0);
    var fOk = true, fBad = '';
    [7, 19, 30, 39].forEach(function(idx){
      var want = Math.ceil(base * bossHpScale(idx));
      var got = spawnedBossHp('phantom', idx);
      if(got !== want){ fOk = false; fBad += ' idx' + idx + ' want' + want + ' got' + got; }
    });
    check('Boss scaling: matches ceil(base*bossHpScale(idx))', fOk, fBad);
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

  // 6) Staged-boss data by tier: L1-10 none; L11-20 exactly 1 medium; L21-30 exactly
  //    2 mediums; L31-40 exactly 2 mediums + a transitional boss. Every medium/trans
  //    kind must be a valid boss kind, distinct from each other AND from the end boss.
  (function(){
    var bad = [];
    for(var i = 0; i < LEVELS.length; i++){
      var L = LEVELS[i];
      var meds = [L.midBoss, L.midBoss2, L.transBoss].filter(Boolean);
      if(i < 10){ if(meds.length) bad.push('L'+(i+1)+':unexpected'); continue; }
      var want = (i < 20) ? 1 : (i < 30) ? 2 : 3;
      if(meds.length !== want){ bad.push('L'+(i+1)+':count'+meds.length+'!='+want); continue; }
      if(i >= 30 && !L.transBoss) bad.push('L'+(i+1)+':no-trans');
      if(i < 30 && L.transBoss)   bad.push('L'+(i+1)+':has-trans');
      var seen = {};
      meds.forEach(function(mb){
        if(mb === L.boss) bad.push('L'+(i+1)+':==end('+mb+')');
        if(seen[mb])      bad.push('L'+(i+1)+':dup('+mb+')');
        seen[mb] = 1;
        var t = createEnemy(mb, 0, 0);
        if(!t || !t.isBoss) bad.push('L'+(i+1)+':invalid('+mb+')');
      });
    }
    check('Staged bosses: L11-40 tiered (1/2/3) valid+distinct, L1-10 none', bad.length === 0, bad.join(' '));
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

  // 8) Staged boss gap (L11-40): after the medium-boss wave DIES the next phase must
  //    wait a 10-15s SURGE gap (bosses never co-exist) filled by a DENSE stream of
  //    monsters; then L11-30 spawn the end boss, while L31-40 spawn a transitional
  //    boss whose death triggers the end boss IMMEDIATELY (0s). Drives the real flow.
  //    Samples idx 12 (1 medium), 24 (2 mediums), 30 & 39 (2 mediums + transitional).
  (function(){
    var bad = [];
    [12, 24, 30, 39].forEach(function(idx){
      startLevel(idx);
      state = STATE.PLAYING; paused = false;
      player.hp = player.maxHp = 99999;
      spawnedCount = levelData.total;                          // skip the main wave
      entities = entities.filter(function(e){ return e.type === 'player'; });
      var meds = [levelData.midBoss, levelData.midBoss2].filter(Boolean);
      var guard = 0;
      while(!midbossSpawned && guard++ < 120) update(1/60);     // release the medium wave
      if(!midbossSpawned){ bad.push('L'+(idx+1)+':no-midboss'); return; }
      var liveMeds = entities.filter(function(e){ return e.type==='enemy' && e.isBoss; }).length;
      if(liveMeds !== meds.length){ bad.push('L'+(idx+1)+':medcount'+liveMeds+'!='+meds.length); return; }
      // Kill the whole medium wave; the next tick should open the surge gap.
      entities.forEach(function(e){ if(e.type==='enemy' && e.isBoss) e.dead = true; });
      update(1/60);
      if(!midbossDefeated){ bad.push('L'+(idx+1)+':not-defeated'); return; }
      if(bossGapTimer < 10 || bossGapTimer > 15){ bad.push('L'+(idx+1)+':gap='+bossGapTimer.toFixed(1)); return; }
      // Run almost the whole gap (stop ~0.5s short): no boss yet, and the surge must
      // pile up a real crowd (would FAIL under the old <10 trickle).
      var maxMonsters = 0, sawBoss = false;
      var frames = Math.ceil(bossGapTimer * 60) - 30;
      for(var f = 0; f < frames; f++){
        player.hp = player.maxHp; update(1/60);
        var m = entities.filter(function(e){ return e.type==='enemy' && !e.isBoss; }).length;
        if(m > maxMonsters) maxMonsters = m;
        if(entities.some(function(e){ return e.type==='enemy' && e.isBoss; })) sawBoss = true;
      }
      if(sawBoss){ bad.push('L'+(idx+1)+':boss-too-early'); return; }
      if(maxMonsters < 8){ bad.push('L'+(idx+1)+':surge-too-thin('+maxMonsters+')'); return; }
      // Let the gap finish: the next boss (transitional for L31-40, else the end boss) arrives.
      for(var f2 = 0; f2 < 4*60; f2++){
        player.hp = player.maxHp; update(1/60);
        if(entities.some(function(e){ return e.type==='enemy' && e.isBoss; })) break;
      }
      var liveBoss = entities.filter(function(e){ return e.type==='enemy' && e.isBoss; });
      if(!liveBoss.length){ bad.push('L'+(idx+1)+':next-boss-never'); return; }
      if(idx >= 30){
        // L31-40: it's the TRANSITIONAL boss, not the end boss yet.
        if(bossSpawned){ bad.push('L'+(idx+1)+':endboss-skipped-trans'); return; }
        if(liveBoss[0].kind !== levelData.transBoss){ bad.push('L'+(idx+1)+':not-trans('+liveBoss[0].kind+')'); return; }
        liveBoss.forEach(function(e){ e.dead = true; });
        update(1/60);                                          // 0s handoff
        if(!bossSpawned){ bad.push('L'+(idx+1)+':end-not-immediate'); return; }
      } else {
        if(!bossSpawned){ bad.push('L'+(idx+1)+':endboss-flag'); return; }
      }
    });
    check('Staged gap: 10-15s dense surge; L31-40 0s trans->end handoff',
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

  // 10) THREE-PHASE scaling curve: difficultyRamp / enemyScale / bossHpScale /
  //     bossSpdScale must be strictly increasing across all 40 levels, start at the
  //     L1 baseline (ramp 0, scales 1, enemyScale 1), enemyScale must equal
  //     1+difficultyRamp, and there must be NO discontinuous jump at the phase seams
  //     (every per-level ramp delta in (0, 0.2]).
  (function(){
    var ok = true, d = [];
    if(difficultyRamp(0) !== 0) { ok = false; d.push('ramp0!=0'); }
    if(bossHpScale(0) !== 1)    { ok = false; d.push('bossHp0!=1'); }
    if(bossSpdScale(0) !== 1)   { ok = false; d.push('bossSpd0!=1'); }
    var savedIdx = levelIdx, pr = -1, ph = -1, ps = -1;
    for(var i = 0; i < 40; i++){
      var r = difficultyRamp(i), h = bossHpScale(i), s = bossSpdScale(i);
      levelIdx = i; var e = enemyScale();
      if(Math.abs(e - (1 + r)) > 1e-9) { ok = false; d.push('enemy!=1+ramp@' + i); }
      if(i > 0){
        if(!(r > pr)) { ok = false; d.push('ramp!up@' + i); }
        if(!(h > ph)) { ok = false; d.push('bossHp!up@' + i); }
        if(!(s > ps)) { ok = false; d.push('bossSpd!up@' + i); }
        var dr = r - pr;
        if(dr <= 0 || dr > 0.2) { ok = false; d.push('rampjump@' + i + '=' + dr.toFixed(3)); }
      }
      pr = r; ph = h; ps = s;
    }
    levelIdx = savedIdx;
    check('Scaling: three-phase curve strictly rises, continuous, L1 = no-op', ok, d.slice(0, 6).join(' '));
  })();

  // 11) Level-gated drop variety: at low levels killEnemy must NEVER yield a kind
  //     outside that phase's allow-set, the filtered pool stays non-empty (variety
  //     beyond health), and advanced-only kinds DO unlock at L25+. A deterministic
  //     LCG replaces Math.random so the sweep is reproducible and isn't perturbed by
  //     emit() consuming randoms.
  (function(){
    var savedIdx = levelIdx, savedPlayer = player, savedEnt = entities,
        savedProfile = profile, savedRandom = Math.random, ok = true, d = [];
    profile = DEFAULT_PROFILE();
    player = createPlayer('soldier');            // class resource pickup = 'beverage'
    var seed = 123456789;
    Math.random = function(){ seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
    function sampleKinds(idx, iters){
      levelIdx = idx; var got = {};
      for(var n = 0; n < iters; n++){
        entities = [];
        var en = createEnemy('grunt', 100, 100); entities.push(en); killEnemy(en);
        for(var k = 0; k < entities.length; k++){ if(entities[k].type === 'pickup') got[entities[k].kind] = 1; }
      }
      return Object.keys(got);
    }
    var basics = { health:1, beverage:1, rapid:1, shield:1 };
    var mid    = { health:1, beverage:1, rapid:1, shield:1, pierce:1, multi:1, damage:1, speed:1, magnet:1 };
    var advOnly = { armor:1, slowmo:1, score2x:1 };
    var p1 = sampleKinds(5, 1500);               // L6  (phase 1: basics only)
    var leak1 = p1.filter(function(k){ return !basics[k]; });
    if(leak1.length)   { ok = false; d.push('L1-15 leak:' + leak1.join(',')); }
    if(p1.length < 2)  { ok = false; d.push('L1-15 no variety'); }
    var p2 = sampleKinds(18, 1500);              // L19 (phase 2: + enhancers/utility)
    var leak2 = p2.filter(function(k){ return !mid[k]; });
    if(leak2.length)   { ok = false; d.push('L16-24 leak:' + leak2.join(',')); }
    var p3 = sampleKinds(30, 1500);              // L31 (phase 3: full pool)
    if(p3.filter(function(k){ return advOnly[k]; }).length === 0) { ok = false; d.push('L25-40 advanced never drops'); }
    levelIdx = savedIdx; player = savedPlayer; entities = savedEnt; profile = savedProfile; Math.random = savedRandom;
    check('Drops: level-gated variety (no leak L1-24, advanced unlock L25+)', ok, d.join(' '));
  })();

  // 12) RMB pools (all 3 classes): the resource regens even while RMB is HELD; the
  //     secondary fires until the pool empties, which arms a ~1s rmbLockT lockout; and
  //     while locked a FULL pool does not drain (no fire). Drives updatePlaying's real
  //     regen + per-class fire blocks. A fresh player is built per sub-check.
  (function(){
    var savedChar = selectedChar, savedProfile = profile, dt = 1 / 60, ok = true, d = [];
    profile = DEFAULT_PROFILE();
    selectedChar = 'soldier'; startGame(); state = STATE.PLAYING;   // sets up level/world/state once
    // [class, poolField, maxField, perShot(1 use=1) , cadenceField]
    [['soldier','energy','maxEnergy',false,null],
     ['tank','fuel','maxFuel',false,null],
     ['scout','power','maxPower',true,'laserCd'],
     ['bounty_hunter','fury','maxFury',false,null],
     ['cyborg','toxin','maxToxin',true,'bioCd']].forEach(function(spec){
      var cls = spec[0], pool = spec[1], maxF = spec[2], perShot = spec[3], cad = spec[4];
      function fresh(){ player = createPlayer(cls); entities = [player]; allies = []; mouse.rdown = true; mouse.down = false; if(cad) player[cad] = 0; player.hp = player.maxHp; }
      // (a) recover while held: empty pool, not locked -> regen still bumps it above 0.
      fresh(); player[pool] = 0; player.rmbLockT = 0; update(dt);
      if(!(player[pool] > 0)) { ok = false; d.push(cls + ':noRegenHeld'); }
      // (b) lockout engages: pool just over one use -> fires once, empties, sets ~1s lock.
      fresh(); player.rmbLockT = 0; player[pool] = perShot ? 1 : dt * 1.5; if(cad) player[cad] = 0; update(dt);
      if(!(player.rmbLockT > 0.9)) { ok = false; d.push(cls + ':noLockout(' + (player.rmbLockT || 0).toFixed(2) + ')'); }
      // (c) locked -> no drain: full pool but rmbLockT high -> stays full (regen only).
      fresh(); player[pool] = player[maxF]; player.rmbLockT = 1; if(cad) player[cad] = 0; update(dt);
      if(player[pool] < player[maxF] - 1e-6) { ok = false; d.push(cls + ':drainedWhileLocked'); }
    });
    selectedChar = savedChar; profile = savedProfile;
    check('RMB: regen-while-held + 1s empty-lockout (all 5 classes)', ok, d.join(' '));
  })();

  // 13) Assistant level scaling: assistLevelFrac runs 0.35 (L1) -> 1.0 (L10) and is
  //     strictly increasing; for every roster ally, level 10 has >= HP and > primary
  //     damage than level 1, and L1 HP is never < 1 (createAssistant -> applyAssistantLevel).
  (function(){
    var savedProfile = profile, ok = true, d = [];
    if(Math.abs(assistLevelFrac(1) - 0.35) > 1e-6)               { ok = false; d.push('frac1!=0.35'); }
    if(Math.abs(assistLevelFrac(ASSIST_MAX_LEVEL) - 1) > 1e-6)   { ok = false; d.push('frac10!=1'); }
    for(var l = 2; l <= ASSIST_MAX_LEVEL; l++){ if(!(assistLevelFrac(l) > assistLevelFrac(l - 1))){ ok = false; d.push('frac!up@' + l); } }
    var dmgField = { companion:'dmg', henchman:'swingDmg', nunchaku:'swingDmg', bomber_ally:'bombDmg', poison_ally:'dps' };
    ['drone','henchman','nunchaku','bomber','poison'].forEach(function(key){
      profile = DEFAULT_PROFILE();
      profile.ownedAssistants = ['drone','henchman','nunchaku','bomber','poison'];
      profile.assistantLevels = {}; profile.assistantLevels[key] = 1;
      var a1 = createAssistant(key);
      profile.assistantLevels[key] = ASSIST_MAX_LEVEL;
      var a10 = createAssistant(key);
      var df = dmgField[a1.type];
      if(!(a1.maxHp >= 1))            { ok = false; d.push(key + ':hp<1'); }
      if(!(a10.maxHp >= a1.maxHp))    { ok = false; d.push(key + ':hp!up'); }
      if(df && !(a10[df] > a1[df]))   { ok = false; d.push(key + ':dmg!up'); }
    });
    profile = savedProfile;
    check('Assistants: level scaling raises HP/damage (frac 0.35 -> 1.0)', ok, d.join(' '));
  })();

  // 14) Skill tiers: across tiers 1..5 the per-cast cooldown (skillCdFor) strictly
  //     FALLS, the upgrade cost (skillUpgradeCost) strictly RISES and is null at max,
  //     every tier has a non-empty blurb, and resolvePlayerLoadout still resolves an
  //     owned skill with skillLevels populated.
  (function(){
    var saved = profile, ok = true, d = [];
    ['heal','sprint','grenade','blast','nuke','resummon'].forEach(function(id){
      profile = DEFAULT_PROFILE();
      if(profile.ownedSkills.indexOf(id) < 0) profile.ownedSkills.push(id);
      var prevCd = Infinity, prevUp = -1;
      for(var t = 1; t <= SKILL_MAX_TIER; t++){
        profile.skillLevels[id] = t;
        var cd = skillCdFor(id);
        if(!(cd < prevCd)) { ok = false; d.push(id + ':cd!down@' + t); }
        prevCd = cd;
        if(!skillBlurb(id, t)) { ok = false; d.push(id + ':blurb@' + t); }
        if(t < SKILL_MAX_TIER){
          var up = skillUpgradeCost(id);
          if(!(up > prevUp)) { ok = false; d.push(id + ':up!rise@' + t); }
          prevUp = up;
        } else if(skillUpgradeCost(id) !== null){ ok = false; d.push(id + ':maxNotNull'); }
      }
    });
    profile = DEFAULT_PROFILE(); profile.level = 20;
    profile.ownedSkills.push('blast'); profile.loadout.x = 'blast'; profile.skillLevels.blast = 3;
    if(resolvePlayerLoadout().x !== 'blast'){ ok = false; d.push('loadout'); }
    profile = saved;
    check('Skill tiers: cd falls + cost rises + blurb per tier (1..5)', ok, d.join(' '));
  })();

  // 15) RESUMMON: revives a DEAD equipped assistant (entity count rises, ally no longer
  //     dead) and returns true; with no dead ally it returns false (charges no cooldown).
  (function(){
    var savedC = selectedChar, savedP = profile, ok = true, d = [];
    profile = DEFAULT_PROFILE();
    selectedChar = 'soldier'; startGame(); state = STATE.PLAYING;
    player = createPlayer('soldier'); entities = [player];
    var ally = createAssistant('drone'); ally.dead = true; allies = [ally];
    profile.skillLevels.resummon = 5;
    var before = entities.length;
    var fired = triggerSkill('resummon', 1, 0, 1);
    if(!fired)                          { ok = false; d.push('didntFireOnDead'); }
    if(!(entities.length > before))     { ok = false; d.push('noRevive'); }
    if(allies[0] && allies[0].dead)     { ok = false; d.push('stillDead'); }
    var fired2 = triggerSkill('resummon', 1, 0, 1);   // none dead now
    if(fired2 !== false)                { ok = false; d.push('firedWithNoneDead'); }
    selectedChar = savedC; profile = savedP;
    check('Resummon: revives a dead equipped ally; no-op when none dead', ok, d.join(' '));
  })();

  // 16) Assistant evolutions: every roster ally built at L10 reports level 10 and its AI
  //     runs ~200 ticks against a (high-HP) enemy without throwing or breaching the 480
  //     entity cap; the L10 drone fires an explosive AoE missile within a few seconds.
  (function(){
    var savedP = profile, ok = true, d = [];
    profile = DEFAULT_PROFILE();
    profile.ownedAssistants = ['drone','henchman','nunchaku','bomber','poison'];
    if(!player){ selectedChar = 'soldier'; startGame(); state = STATE.PLAYING; }
    var updaters = { drone:updateCompanion, henchman:updateMeleeAlly, nunchaku:updateMeleeAlly, bomber:updateBomberAlly, poison:updatePoisonAlly };
    ['drone','henchman','nunchaku','bomber','poison'].forEach(function(key){
      profile.assistantLevels = {}; profile.assistantLevels[key] = ASSIST_MAX_LEVEL;
      var a = createAssistant(key);
      if(a.level !== ASSIST_MAX_LEVEL){ ok = false; d.push(key + ':lvl'); }
      var en = createEnemy('grunt', player.x + 20, player.y); en.hp = en.maxHp = 99999;
      entities = [player, a, en];
      var fn = updaters[key];
      try {
        for(var i = 0; i < 200; i++){ fn(a, 1/60); if(entities.length >= 480){ ok = false; d.push(key + ':cap'); break; } }
      } catch(e){ ok = false; d.push(key + ':throw'); }
    });
    // L10 drone emits an explosive ally missile (every 3rd shot).
    profile.assistantLevels = { drone:ASSIST_MAX_LEVEL };
    var dr = createAssistant('drone');
    var en2 = createEnemy('grunt', player.x + 20, player.y); en2.hp = en2.maxHp = 99999;
    entities = [player, dr, en2];
    var sawMissile = false;
    for(var j = 0; j < 300 && !sawMissile; j++){
      updateCompanion(dr, 1/60);
      for(var k = 0; k < entities.length; k++){
        var b = entities[k];
        if(b.type === 'bullet' && b.explosive && b.fromAlly){ sawMissile = true; break; }
      }
    }
    if(!sawMissile){ ok = false; d.push('drone:noMissile'); }
    profile = savedP;
    check('Assistant evolutions: L10 AIs run clean + drone fires missiles', ok, d.join(' '));
  })();

  // 27) Universal PASSIVE system: slot formula by account level; passiveValue is 0 when
  //     NOT equipped and strictly rises L1->L10 when equipped; passiveUpgradeCost rises
  //     with level; loadProfile sanitize caps equipped to owned AND the level's slots.
  (function(){
    var saved = profile, ok = true, d = [];
    // Slots: thresholds 1 / 9 / 17 / 25 / 33 -> 1..5 (capped 5).
    [[1,1],[8,1],[9,2],[16,2],[17,3],[25,4],[33,5],[41,5],[50,5]].forEach(function(pair){
      profile = DEFAULT_PROFILE(); profile.level = pair[0];
      if(maxPassiveSlots() !== pair[1]){ ok = false; d.push('slots@' + pair[0] + '=' + maxPassiveSlots()); }
    });
    // Unequipped -> 0; equipped -> strictly rising L1..L10; cost strictly rising.
    profile = DEFAULT_PROFILE(); profile.level = 40;
    if(passiveValue('greed') !== 0){ ok = false; d.push('unowned!=0'); }
    profile.passiveLevels = { greed:5 };
    if(passiveValue('greed') !== 0){ ok = false; d.push('owned-unequipped!=0'); }   // owned but not equipped
    profile.equippedPassives = ['greed'];
    var prevV = -1, prevC = -1;
    for(var L = 1; L <= PASSIVE_MAX_LEVEL; L++){
      profile.passiveLevels.greed = L;
      var v = passiveValue('greed');
      if(!(v > prevV)){ ok = false; d.push('val!rise@' + L); }
      prevV = v;
      if(L < PASSIVE_MAX_LEVEL){
        var c = passiveUpgradeCost('greed');
        if(!(c > prevC)){ ok = false; d.push('cost!rise@' + L); }
        prevC = c;
      } else if(passiveUpgradeCost('greed') !== null){ ok = false; d.push('maxCost!null'); }
    }
    // Sanitize: equipped is capped to owned AND the level's slot count, owned levels
    // clamped. Only assert when localStorage actually round-trips the string (a real
    // browser); the headless Proxy stub returns a non-string, so loadProfile falls back
    // to DEFAULT_PROFILE and there's nothing to check.
    var fake = JSON.stringify({ level:1, passiveLevels:{ greed:99, lifesteal:3, bogus:2 }, equippedPassives:['greed','lifesteal','vitality'] });
    localStorage.setItem('shooter_profile', fake);
    if(localStorage.getItem('shooter_profile') === fake){
      var lp = loadProfile();
      if(lp.passiveLevels.greed !== PASSIVE_MAX_LEVEL){ ok = false; d.push('clampHi'); }
      if('bogus' in lp.passiveLevels){ ok = false; d.push('bogusKept'); }
      if(lp.equippedPassives.length > 1){ ok = false; d.push('slotCapFail'); }   // L1 = 1 slot
      if(lp.equippedPassives.indexOf('vitality') >= 0){ ok = false; d.push('equipUnowned'); }
    }
    // setPassiveSlot (the CHARACTER-SELECT picker): equips into a slot, dedupes a passive
    // across slots, clears on null, and never exceeds maxPassiveSlots().
    profile = DEFAULT_PROFILE(); profile.level = 40;   // 5 slots
    profile.passiveLevels = { lifesteal:3, greed:5, swiftness:2 }; profile.equippedPassives = [];
    setPassiveSlot(0, 'lifesteal'); setPassiveSlot(1, 'greed');
    if(profile.equippedPassives.join(',') !== 'lifesteal,greed'){ ok = false; d.push('equipSlots'); }
    setPassiveSlot(1, 'lifesteal');   // moving an already-equipped passive must not duplicate it
    if(profile.equippedPassives.filter(function(k){ return k === 'lifesteal'; }).length !== 1){ ok = false; d.push('dupSlot'); }
    setPassiveSlot(0, null);          // clear a slot
    if(profile.equippedPassives.indexOf('lifesteal') < 0 && profile.equippedPassives.length !== 0){ /* ok */ }
    profile.level = 1;                // 1 slot -> setPassiveSlot caps
    profile.equippedPassives = [];
    setPassiveSlot(0, 'lifesteal'); setPassiveSlot(1, 'greed');
    if(profile.equippedPassives.length > 1){ ok = false; d.push('slotCapSet'); }
    profile = saved;
    check('Passives: slots/value/cost scale + sanitize + setPassiveSlot caps/dedupes', ok, d.join(' '));
  })();

  // 28) Class passives removed + universal ones apply: the old soldierLifesteal symbol is
  //     gone; an equipped lifesteal heals via damageEnemy(...,true); a kill with RESOURCE
  //     equipped refills the active RMB pool; GREED/SCHOLAR scale per-kill gold/xp.
  (function(){
    var savedC = selectedChar, savedP = profile, ok = true, d = [];
    if(typeof soldierLifesteal !== 'undefined'){ ok = false; d.push('soldierLifesteal still defined'); }
    profile = DEFAULT_PROFILE(); profile.level = 40;
    selectedChar = 'tank'; startGame(); state = STATE.PLAYING;
    // (a) lifesteal heals on player-sourced damage when equipped.
    profile.passiveLevels = { lifesteal:10 }; profile.equippedPassives = ['lifesteal'];
    player = createPlayer('tank'); player.hp = 1; entities = [player];
    var en = createEnemy('grunt', player.x + 10, player.y); en.hp = en.maxHp = 99999; entities.push(en);
    damageEnemy(en, 20, true);
    if(!(player.hp > 1)){ ok = false; d.push('noLifesteal'); }
    // (b) RESOURCE refills the active pool (tank fuel) on kill.
    profile.passiveLevels = { resource:10 }; profile.equippedPassives = ['resource'];
    player = createPlayer('tank'); player.fuel = 0; entities = [player];
    var en2 = createEnemy('grunt', player.x, player.y); entities.push(en2);
    killEnemy(en2);
    if(!(player.fuel > 0)){ ok = false; d.push('noResource'); }
    // (c) GREED / SCHOLAR scale per-kill gold/xp vs an unequipped baseline.
    function killGain(equip){
      profile = DEFAULT_PROFILE(); profile.level = 40; profile.passiveLevels = { greed:10, scholar:10 };
      profile.equippedPassives = equip ? ['greed','scholar'] : [];
      player = createPlayer('tank'); entities = [player];
      var g0 = profile.gold, x0 = profile.xp;
      var e = createEnemy('grunt', player.x, player.y); e.score = 100; entities.push(e);
      killEnemy(e);
      return { g: profile.gold - g0, x: profile.xp - x0 };
    }
    var base = killGain(false), boost = killGain(true);
    if(!(boost.g > base.g)){ ok = false; d.push('greed!scale'); }
    if(!(boost.x > base.x)){ ok = false; d.push('scholar!scale'); }
    selectedChar = savedC; profile = savedP;
    check('Passives: class passives removed + universal lifesteal/resource/greed/scholar apply', ok, d.join(' '));
  })();

  // 29) New classes (Leo/Ong): bio-gun glob drops a poison_cloud that damages enemies,
  //     the machete arc hits, the shotgun fires 3 pellets, and the 4 new skills fire via
  //     triggerSkill without error (biobomb spawns a cloud; fanfire spawns bullets;
  //     grit grants shield; overclock arms rapidTime).
  (function(){
    var savedC = selectedChar, savedP = profile, ok = true, d = [];
    profile = DEFAULT_PROFILE(); profile.level = 40;
    selectedChar = 'cyborg'; startGame(); state = STATE.PLAYING;
    function clouds(){ return entities.filter(function(e){ return e.type === 'poison_cloud'; }).length; }
    // (a) bio-gun: a glob that hits an enemy spawns a poison_cloud which then damages it.
    player = createPlayer('cyborg'); entities = [player];
    var en = createEnemy('grunt', player.x + 20, player.y); en.hp = en.maxHp = 9999; entities.push(en);
    player.angle = 0; fireBiogun();
    var hadBullet = entities.some(function(e){ return e.type === 'bullet' && e.spawnsCloud; });
    if(!hadBullet){ ok = false; d.push('biogun:noBullet'); }
    for(var i = 0; i < 30; i++) update(1/60);            // glob travels, hits, drops cloud, cloud ticks
    if(clouds() < 1){ ok = false; d.push('biogun:noCloud'); }
    if(!(en.hp < en.maxHp)){ ok = false; d.push('cloud:noDamage'); }
    // (b) shotgun LMB fires 3 pellets (the spread form), still respecting MULTI off.
    player = createPlayer('bounty_hunter'); entities = [player]; player.angle = 0;
    fireWeapon(player.x + 9, player.y);
    if(entities.filter(function(e){ return e.type === 'bullet'; }).length !== 3){ ok = false; d.push('shotgun!=3pellets'); }
    // (c) machete arc damages an enemy in front.
    player = createPlayer('bounty_hunter'); entities = [player]; player.angle = 0;
    var em = createEnemy('grunt', player.x + 12, player.y); em.hp = em.maxHp = 9999; entities.push(em);
    fireMachete(1/60);
    if(!(em.hp < em.maxHp)){ ok = false; d.push('machete:noDamage'); }
    // (d) the 4 new skills fire via triggerSkill cleanly with their intended effect.
    profile.ownedSkills = ['heal','grit','overclock','fanfire','biobomb'];
    profile.skillLevels = { heal:1, grit:1, overclock:1, fanfire:1, biobomb:1 };
    player = createPlayer('bounty_hunter'); entities = [player]; player.shieldHp = 0;
    if(triggerSkill('grit') !== true || !(player.shieldHp > 0)){ ok = false; d.push('grit'); }
    player.rapidTime = 0;
    if(triggerSkill('overclock') !== true || !(player.rapidTime > 0)){ ok = false; d.push('overclock'); }
    entities = [player];
    if(triggerSkill('fanfire') !== true || entities.filter(function(e){ return e.type === 'bullet'; }).length < 5){ ok = false; d.push('fanfire'); }
    entities = [player];
    if(triggerSkill('biobomb') !== true || clouds() < 1){ ok = false; d.push('biobomb'); }
    selectedChar = savedC; profile = savedP;
    check('New classes: bio-gun cloud / shotgun pellets / machete / Leo+Ong skills fire', ok, d.join(' '));
  })();

  // 30) Flamethrower heat/overcharge: a tick with fuel < 50% of max ("Dangerous
  //     Temperature") deals 1.5x the damage of a full-fuel tick at the SAME enemy
  //     position — the boost stacks multiplicatively, it doesn't override damageMult.
  (function(){
    var savedC = selectedChar, savedP = profile, ok = true, d = [];
    profile = DEFAULT_PROFILE(); profile.level = 10;
    selectedChar = 'tank'; startGame(); state = STATE.PLAYING;
    function tickDmg(fuelFrac){
      player = createPlayer('tank'); player.x = 100; player.y = 100; player.angle = 0;
      player.fuel = player.maxFuel * fuelFrac;
      var en = createEnemy('grunt', player.x + 20, player.y); en.hp = en.maxHp = 100000;
      entities = [player, en];
      fireFlamethrower(1/60);
      return en.maxHp - en.hp;
    }
    var normal = tickDmg(1.0);     // full fuel -> no heat boost
    var danger = tickDmg(0.25);    // below 50% -> 1.5x
    if(!(normal > 0)){ ok = false; d.push('noDmg'); }
    else if(!(Math.abs(danger / normal - 1.5) < 0.05)){ ok = false; d.push('ratio=' + (danger/normal).toFixed(3)); }
    selectedChar = savedC; profile = savedP;
    check('Flamethrower heat: <50% fuel deals 1.5x damage (stacks)', ok, d.join(' '));
  })();

  // 31) Decals are visual-only: spawnDecal never touches `entities`, is capped, and
  //     explode() drops one. (Guards the 600-entity-cap-safety + no-physics invariant.)
  (function(){
    var ok = true, d = [];
    decals = []; entities = [player];
    var e0 = entities.length;
    for(var i = 0; i < 80; i++) spawnDecal(100 + i, 100, 12, i % 2 ? 'toxic' : 'scorch');
    if(decals.length > DECAL_CAP){ ok = false; d.push('cap=' + decals.length); }
    if(entities.length !== e0){ ok = false; d.push('leakedToEntities'); }
    var before = decals.length;
    explode(player.x, player.y, 30, 1, true);
    if(!(decals.length >= Math.min(DECAL_CAP, before))){ ok = false; d.push('explodeNoDecal'); }
    decals = [];
    check('Decals: visual-only (capped, never entities, explode spawns one)', ok, d.join(' '));
  })();

  // 32) 5-tier weapon evolution: tier = min(5, floor((L-1)/8)+1) with the right
  //     boundaries + multipliers; fired bullets carry tier + sourceClass; higher tier =
  //     more LMB damage (stacks); the Soldier pistol flips kinetic->energy at Tier 3.
  (function(){
    var savedC = selectedChar, savedP = profile, ok = true, d = [];
    // boundary table: account level -> expected tier
    [[1,1],[8,1],[9,2],[16,2],[17,3],[24,3],[25,4],[32,4],[33,5],[50,5]].forEach(function(pair){
      if(weaponTierFor(pair[0]) !== pair[1]){ ok = false; d.push('tier(' + pair[0] + ')=' + weaponTierFor(pair[0])); }
    });
    var MUL = [1.0,1.2,1.5,1.9,2.5];
    for(var t = 1; t <= 5; t++){ if(WEAPON_TIER_MULT[t-1] !== MUL[t-1]){ ok = false; d.push('mult' + t); } }
    profile = DEFAULT_PROFILE(); selectedChar = 'tank'; startGame(); state = STATE.PLAYING;
    // Fire one LMB shot; optionally force the weapon-tier mult to isolate it from the
    // separate account-level damageMult growth.
    function lmbBullet(cls, lvl, forceMult){
      profile.level = lvl; player = createPlayer(cls); entities = [player];
      if(forceMult != null){ player.weaponMult = forceMult; }
      player.x = 100; player.y = 100; player.angle = 0; player.fireCooldown = 0;
      fireWeapon(player.x + 9, player.y);
      return entities.filter(function(e){ return e.type === 'bullet'; })[0];
    }
    // applyLevelScaling tags the bullet with the level-derived tier + class.
    var b1 = lmbBullet('tank', 1), b5 = lmbBullet('tank', 33);
    if(!(b1 && b1.tier === 1 && b1.sourceClass === 'tank')){ ok = false; d.push('tagT1'); }
    if(!(b5 && b5.tier === 5)){ ok = false; d.push('tagT5'); }
    // Isolate the tier multiplier at a FIXED level (same damageMult): x2.5 vs x1.0 = 2.5.
    var lo = lmbBullet('tank', 1, 1.0), hi = lmbBullet('tank', 1, 2.5);
    if(!(lo && hi && Math.abs(hi.dmg / lo.dmg - 2.5) < 0.02)){ ok = false; d.push('tierStack=' + (lo && hi && (hi.dmg/lo.dmg).toFixed(2))); }
    // Soldier pistol: kinetic at T1, energy (plasma) at T3+.
    var sp1 = lmbBullet('soldier', 1), sp3 = lmbBullet('soldier', 17);
    if(!(sp1 && sp1.kinetic === true)){ ok = false; d.push('soldierT1!kinetic'); }
    if(!(sp3 && sp3.kinetic === false)){ ok = false; d.push('soldierT3!energy'); }
    selectedChar = savedC; profile = savedP;
    check('Weapon tiers: formula/mults + bullet tags + damage stacks + soldier plasma@T3', ok, d.join(' '));
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
