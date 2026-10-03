'use strict';
// Global namespace + tuning data.
window.S = {};

S.RING_R = 4.6;      // ring radius (centre crossing this = out)
S.DT = 1 / 120;      // fixed simulation step

// Four wrestlers. Differences are physical only: mass, force, speed, grip, balance.
S.ARCH = [
  {
    key: 'balanced', name: 'TAKAKAZE', kanji: '高風', title: 'BALANCED',
    blurb: 'Steady everywhere. No bad habits. Start here.',
    traits: ['Mass ●●●○○', 'Speed ●●●○○', 'Grip ●●●○○'],
    mass: 1.0, scale: 1.0, moveForce: 20, maxSpeed: 5.3, pushForce: 25, turnRate: 4.4,
    recovery: 1.05, grip: 1.08, stability: 1.0, power: 1.0, dashSpeed: 8.4, dashTime: 0.16, tech: 1.0,
    skin: 0xf3c7a2, skinShade: 0xc17a6c, belt: 0x2c3d93, beltShade: 0x151a4c, accent: '#5b8cff',
  },
  {
    key: 'heavy', name: 'IWAKURA', kanji: '岩倉', title: 'HEAVY',
    blurb: 'A boulder in a belt. Slow to start. Impossible to stop.',
    traits: ['Mass ●●●●●', 'Speed ●○○○○', 'Grip ●●●○○'],
    mass: 1.5, scale: 1.17, moveForce: 23, maxSpeed: 4.4, pushForce: 31, turnRate: 3.0,
    recovery: 0.66, grip: 1.05, stability: 1.3, power: 1.25, dashSpeed: 6.9, dashTime: 0.17, tech: 0.85,
    skin: 0xdfa47f, skinShade: 0x9c5a55, belt: 0x5d2a76, beltShade: 0x2a1238, accent: '#b763ff',
  },
  {
    key: 'fast', name: 'HAYATE', kanji: '疾風', title: 'FAST',
    blurb: 'Light feet, sharp angles. Loses every straight shoving match.',
    traits: ['Mass ●○○○○', 'Speed ●●●●●', 'Grip ●●○○○'],
    mass: 0.85, scale: 0.9, moveForce: 22, maxSpeed: 6.3, pushForce: 22, turnRate: 5.8,
    recovery: 1.3, grip: 0.95, stability: 1.0, power: 0.9, dashSpeed: 10.2, dashTime: 0.15, tech: 1.05,
    skin: 0xf7d3b6, skinShade: 0xcd8a78, belt: 0xd8402e, beltShade: 0x7a1a22, accent: '#ff5a3c',
  },
  {
    key: 'tech', name: 'KAGEROU', kanji: '陽炎', title: 'TECHNICAL',
    blurb: 'Weak hands, wicked grip. Throws and trips from anywhere.',
    traits: ['Mass ●●○○○', 'Speed ●●●○○', 'Grip ●●●●●'],
    mass: 0.95, scale: 0.97, moveForce: 19, maxSpeed: 5.3, pushForce: 20, turnRate: 4.8,
    recovery: 1.1, grip: 1.2, stability: 0.96, power: 0.82, dashSpeed: 8.8, dashTime: 0.16, tech: 1.22,
    skin: 0xebb994, skinShade: 0xad6f66, belt: 0x16877f, beltShade: 0x0b3e44, accent: '#2fd3c2',
  },
];

// Winning techniques: [kanji, romaji, english]
S.KIMARITE = {
  oshidashi:   ['押し出し', 'OSHIDASHI', 'Frontal push out'],
  oshitaoshi:  ['押し倒し', 'OSHITAOSHI', 'Frontal push down'],
  tsukidashi:  ['突き出し', 'TSUKIDASHI', 'Thrust out'],
  tsukitaoshi: ['突き倒し', 'TSUKITAOSHI', 'Thrust down'],
  tsukiotoshi: ['突き落とし', 'TSUKIOTOSHI', 'Side thrust down'],
  yorikiri:    ['寄り切り', 'YORIKIRI', 'Frontal force out'],
  yoritaoshi:  ['寄り倒し', 'YORITAOSHI', 'Frontal crush down'],
  hatakikomi:  ['叩き込み', 'HATAKIKOMI', 'Slap down'],
  hikiotoshi:  ['引き落とし', 'HIKIOTOSHI', 'Hand pull down'],
  uwatenage:   ['上手投げ', 'UWATENAGE', 'Overarm throw'],
  shitatenage: ['下手投げ', 'SHITATENAGE', 'Underarm throw'],
  kotenage:    ['小手投げ', 'KOTENAGE', 'Armlock throw'],
  tottari:     ['とったり', 'TOTTARI', 'Caught and spun'],
  katasukashi: ['肩透かし', 'KATASUKASHI', 'Spun past and down'],
  uchigake:    ['内掛け', 'UCHIGAKE', 'Inside leg trip'],
  sotogake:    ['外掛け', 'SOTOGAKE', 'Outside leg trip'],
  okuridashi:  ['送り出し', 'OKURIDASHI', 'Rear push out'],
  okuritaoshi: ['送り倒し', 'OKURITAOSHI', 'Rear push down'],
  utchari:     ['うっちゃり', 'UTCHARI', 'Backward pivot throw'],
  tsuridashi:  ['吊り出し', 'TSURIDASHI', 'Lift out'],
  tsuriotoshi: ['吊り落とし', 'TSURIOTOSHI', 'Lifting body slam'],
  isamiashi:   ['勇み足', 'ISAMIASHI', 'Ran out on his own'],
  fumidashi:   ['踏み出し', 'FUMIDASHI', 'Stepped out'],
  koshikudake: ['腰砕け', 'KOSHIKUDAKE', 'Collapsed'],
};

S.DIFFS = ['easy', 'normal', 'hard'];

// How each winning technique happens, in plain words (for the Move List)
S.BETS = [0, 10000, 50000, 100000, 250000, 500000, 1000000];
  S.BET_ODDS = { easy: 1, normal: 2, hard: 3 }; // a win pays the stake back plus this many times it
  S.HOWTO = [
  ['oshidashi', 'Push them out with J.'],
  ['tsukidashi', 'Slap them out with a fast J flurry.'],
  ['oshitaoshi', 'Shove someone who is off balance so they fall.'],
  ['tsukitaoshi', 'Slap them down while they are wobbling.'],
  ['tsukiotoshi', 'Hit them from the side so they topple.'],
  ['okuridashi', 'Get behind them and push them out.'],
  ['okuritaoshi', 'Get behind them and push them down.'],
  ['hatakikomi', 'As they charge, hold away and press J to slap them down.'],
  ['hikiotoshi', 'Step back or let go while they lean on you, so they fall forward.'],
  ['yorikiri', 'Grab with K and walk them out by holding toward them.'],
  ['yoritaoshi', 'Grab and drive them backwards until they fall.'],
  ['uwatenage', 'Hold K, point to swing them round you, let go to throw.'],
  ['shitatenage', 'Same swing throw, with an inside grip.'],
  ['kotenage', 'Same swing throw, with a weak arm grip.'],
  ['katasukashi', 'Hold K and point behind you: swing them all the way round.'],
  ['uchigake', 'Hold K, point at them, let go: hook their leg.'],
  ['sotogake', 'The same leg hook, from an outside grip.'],
  ['utchari', 'On the straw, swing them round and over the edge.'],
  ['tsuridashi', 'Tap K to lift them, then carry them out.'],
  ['tsuriotoshi', 'Lift them, then tap K again to slam them down.'],
  ['tottari', 'Tap K just as they crash into you to catch and spin them.'],
  ['isamiashi', 'They ran out by themselves. Sidestep a charge to make it happen.'],
  ['fumidashi', 'They stepped out on their own.'],
  ['koshikudake', 'They fell over on their own.'],
];
