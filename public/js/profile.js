'use strict';
// Player profile: Yen wallet, cosmetics catalog, owned items, loadout, names, session record.
(function () {
  const K = 'kumite.profile';

  // ------------------------------------------------------------------ catalog
  // pat: pattern name used by S.patTex (render) and S.patCss (UI)
  S.CAT = [
    { key: 'banner', label: 'BANNER', items: [
      { id: 'bn_ink', name: 'Ink', price: 0, c1: '#170c12', c2: '#e2322b', pat: 'solid' },
      { id: 'bn_wave', name: 'Indigo Wave', price: 150000, c1: '#1d2b6b', c2: '#e9e2cf', pat: 'wave' },
      { id: 'bn_sakura', name: 'Sakura', price: 200000, c1: '#f2a7c0', c2: '#ffffff', pat: 'dots' },
      { id: 'bn_koi', name: 'Golden Koi', price: 300000, c1: '#b8862c', c2: '#ffe28a', pat: 'scales' },
      { id: 'bn_bolt', name: 'Thunder', price: 350000, c1: '#151515', c2: '#ffd23a', pat: 'bolt' },
      { id: 'bn_neon', name: 'Neon Grid', price: 500000, c1: '#0b0f1e', c2: '#2fd3c2', pat: 'grid' },
    ] },
    { key: 'headband', label: 'HEADBAND', items: [
      { id: 'hb_none', name: 'None', price: 0 },
      { id: 'hb_white', name: 'Rising Sun', price: 50000, c1: '#f6f2ea', c2: '#e2322b', pat: 'sun' },
      { id: 'hb_red', name: 'Crimson', price: 50000, c1: '#c8231d', c2: '#7a1010', pat: 'solid' },
      { id: 'hb_check', name: 'Checker', price: 120000, c1: '#1b1b1b', c2: '#2fa98f', pat: 'check' },
      { id: 'hb_gold', name: 'Gold Stripe', price: 150000, c1: '#1a1218', c2: '#f0c35a', pat: 'stripe' },
      { id: 'hb_bolt', name: 'Lightning', price: 220000, c1: '#2b2f9a', c2: '#ffe14a', pat: 'bolt' },
    ] },
    { key: 'mask', label: 'MASK', items: [
      { id: 'mk_none', name: 'None', price: 0 },
      { id: 'mk_menpo', name: 'Samurai Half-Mask', price: 180000, kind: 'menpo' },
      { id: 'mk_kitsune', name: 'Kitsune', price: 250000, kind: 'kitsune' },
      { id: 'mk_oni', name: 'Oni', price: 300000, kind: 'oni' },
      { id: 'mk_tengu', name: 'Tengu', price: 300000, kind: 'tengu' },
      { id: 'mk_hannya', name: 'Hannya', price: 400000, kind: 'hannya' },
      { id: 'mk_visor', name: 'Cyber Visor', price: 600000, kind: 'visor' },
    ] },
    { key: 'mawashi', label: 'MAWASHI', items: [
      { id: 'mw_default', name: 'Stable Colours', price: 0 },
      { id: 'mw_black', name: 'Black Silk', price: 80000, c1: '#151218', c2: '#3a3040', pat: 'solid' },
      { id: 'mw_gold', name: 'Champion Gold', price: 250000, c1: '#d6a53a', c2: '#fff0b0', pat: 'stripe' },
      { id: 'mw_sakura', name: 'Sakura', price: 200000, c1: '#f0a0bd', c2: '#ffffff', pat: 'dots' },
      { id: 'mw_tiger', name: 'Tiger', price: 300000, c1: '#f08a1c', c2: '#1a1010', pat: 'tiger' },
      { id: 'mw_wave', name: 'Great Wave', price: 300000, c1: '#1d3b7a', c2: '#e9e2cf', pat: 'wave' },
      { id: 'mw_neon', name: 'Neon', price: 450000, c1: '#0d1530', c2: '#2fd3c2', pat: 'grid' },
    ] },
    { key: 'headwear', label: 'HEADWEAR', items: [
      { id: 'hw_none', name: 'None', price: 0 },
      { id: 'hw_kasa', name: 'Straw Hat', price: 120000, kind: 'kasa' },
      { id: 'hw_horns', name: 'Oni Horns', price: 200000, kind: 'horns' },
      { id: 'hw_kabuto', name: 'Kabuto Crest', price: 300000, kind: 'kabuto' },
      { id: 'hw_crown', name: 'Crown', price: 400000, kind: 'crown' },
      { id: 'hw_halo', name: 'Neon Halo', price: 500000, kind: 'halo' },
    ] },
    { key: 'jacket', label: 'JACKET', items: [
      { id: 'jk_none', name: 'None', price: 0 },
      { id: 'jk_crimson', name: 'Crimson Haori', price: 150000, c1: '#9c1c1c', c2: '#f0c35a', pat: 'stripe' },
      { id: 'jk_crane', name: 'White Crane', price: 220000, c1: '#efe9dc', c2: '#c8231d', pat: 'sun' },
      { id: 'jk_wave', name: 'Great Wave', price: 280000, c1: '#1d3b7a', c2: '#e9e2cf', pat: 'wave' },
      { id: 'jk_dragon', name: 'Black Dragon', price: 400000, c1: '#141014', c2: '#d6a53a', pat: 'scales' },
      { id: 'jk_cyber', name: 'Cyber Haori', price: 550000, c1: '#0b0f1e', c2: '#ff3a6a', pat: 'grid' },
    ] },
    { key: 'taunt', label: 'TAUNTS', note: 'Owned taunts go on the arrow keys at the face-off.', items: [
      { id: 'ta_flex', name: 'Double Flex', price: 60000, pose: 'flex' },
      { id: 'ta_point', name: 'Point', price: 60000, pose: 'point' },
      { id: 'ta_drum', name: 'Belly Drum', price: 90000, pose: 'drum' },
      { id: 'ta_hype', name: 'Hype the Crowd', price: 90000, pose: 'hype' },
      { id: 'ta_bow', name: 'Deep Bow', price: 60000, pose: 'bow' },
      { id: 'ta_neck', name: 'Neck Crack', price: 80000, pose: 'neck' },
      { id: 'ta_cry', name: 'War Cry', price: 120000, pose: 'cry' },
      { id: 'ta_shimmy', name: 'Shimmy', price: 150000, pose: 'shimmy' },
    ] },
    { key: 'throw', label: 'CROWD THROWS', note: 'What the crowd throws into the ring when you win.', items: [
      { id: 'th_zabuton', name: 'Cushions', price: 0, kind: 'zabuton' },
      { id: 'th_flowers', name: 'Flowers', price: 100000, kind: 'flowers' },
      { id: 'th_petals', name: 'Sakura Petals', price: 150000, kind: 'petals' },
      { id: 'th_confetti', name: 'Confetti', price: 150000, kind: 'confetti' },
      { id: 'th_coins', name: 'Gold Coins', price: 300000, kind: 'coins' },
    ] },
    { key: 'victory', label: 'VICTORY POSE', items: [
      { id: 'vp_tegatana', name: 'Tegatana Salute', price: 0, pose: 'tegatana' },
      { id: 'vp_fist', name: 'Fist Raised', price: 80000, pose: 'fist' },
      { id: 'vp_bow', name: 'Respectful Bow', price: 80000, pose: 'bow' },
      { id: 'vp_flex', name: 'Flex', price: 120000, pose: 'flex' },
      { id: 'vp_shiko', name: 'Victory Stomp', price: 150000, pose: 'shiko' },
      { id: 'vp_crossed', name: 'Arms Crossed', price: 120000, pose: 'crossed' },
      { id: 'vp_cool', name: 'Walk Away', price: 200000, pose: 'cool' },
    ] },
  ];
  // prices: every paid item costs between 10 and 500 match wins (a win pays ¥100,000).
  // The catalogue above keeps its relative order; this spreads it over that range on a curve.
  (function () {
    const paid = []; for (const c of S.CAT) for (const it of c.items) if (it.price > 0) paid.push(it);
    const lo = Math.min(...paid.map((i) => i.price)), hi = Math.max(...paid.map((i) => i.price));
    const NICE = [10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250, 300, 400, 500];
    for (const it of paid) {
      const k = (Math.log(it.price) - Math.log(lo)) / (Math.log(hi) - Math.log(lo) || 1);
      const wins = 10 * Math.pow(50, k);
      it.wins = NICE.reduce((b, n) => (Math.abs(n - wins) < Math.abs(b - wins) ? n : b), 10);
      it.price = it.wins * 100000;
    }
  })();
  S.item = (id) => { for (const c of S.CAT) for (const it of c.items) if (it.id === id) return it; return null; };
  S.catOf = (key) => S.CAT.find((c) => c.key === key);

  const DEF_EQ = { banner: 'bn_ink', headband: 'hb_none', mask: 'mk_none', mawashi: 'mw_default', headwear: 'hw_none', jacket: 'jk_none', throw: 'th_zabuton', victory: 'vp_tegatana', taunts: [null, null, null, null] };

  class Profile {
    constructor() {
      this.yen = 0; this.owned = {}; this.eq = JSON.parse(JSON.stringify(DEF_EQ));
      this.names = ['PLAYER 1', 'PLAYER 2']; this.rules = 'pure'; this.landed = {}; this.bet = 0; this.binds = {}; this.streak = 0; this.bestStreak = 0; this.stage = 'dohyo';
      this.session = {}; // "A|B" -> [winsA, winsB], lives only while the game is open
      try {
        const d = JSON.parse(localStorage.getItem(K) || '{}');
        if (typeof d.yen === 'number') this.yen = d.yen;
        Object.assign(this.owned, d.owned || {});
        Object.assign(this.eq, d.eq || {});
        if (d.names) this.names = d.names;
        if (d.rules) this.rules = d.rules;
        if (d.bet) this.bet = d.bet;
        if (d.binds) this.binds = d.binds;
        this.streak = d.streak || 0; this.bestStreak = d.bestStreak || 0; if (d.stage) this.stage = d.stage;
        if (d.landed) this.landed = d.landed;
        if (d.pid) this.pid = d.pid;
        // Tuna was taken out of the shop: refund anyone who bought it
        if (this.owned.th_fish) { delete this.owned.th_fish; this.yen += 250000; }
        if (this.eq.throw === 'th_fish') this.eq.throw = DEF_EQ.throw;
      } catch (e) { /* storage blocked */ }
      for (const c of S.CAT) for (const it of c.items) if (it.price === 0) this.owned[it.id] = true;
      // anonymous id for online ratings (no account needed); kept in this browser
      if (!this.pid) { this.pid = 'p' + Math.random().toString(36).slice(2, 12) + Date.now().toString(36); this.save(); }
    }
    save() { try { localStorage.setItem(K, JSON.stringify({ yen: this.yen, owned: this.owned, eq: this.eq, names: this.names, rules: this.rules, landed: this.landed, bet: this.bet, binds: this.binds, streak: this.streak, bestStreak: this.bestStreak, stage: this.stage, pid: this.pid })); } catch (e) { /* ignore */ } }
    has(id) { return !!this.owned[id]; }
    buy(id) {
      const it = S.item(id); if (!it || this.has(id) || this.yen < it.price) return false;
      this.yen -= it.price; this.owned[id] = true; this.save(); return true;
    }
    equip(cat, id) {
      if (!this.has(id)) return false;
      if (cat === 'taunt') {
        const t = this.eq.taunts, at = t.indexOf(id);
        if (at >= 0) { t[at] = null; } // toggle off
        else { const free = t.indexOf(null); t[free >= 0 ? free : 0] = id; }
      } else this.eq[cat] = id;
      this.save(); return true;
    }
    earn(n) { this.yen += n; this.save(); }
    // betting on a CPU match: the stake goes in at the start, a win pays it back plus the odds
    betNow() { return Math.max(0, Math.min(this.bet || 0, this.yen)); }
    land(km) { this.landed[km] = (this.landed[km] || 0) + 1; this.save(); }
    record(a, b) { const k = a + '|' + b; if (!this.session[k]) this.session[k] = [0, 0]; return this.session[k]; }
    loadout() { return JSON.parse(JSON.stringify(this.eq)); }
    // CPU dresses up with random gear
    randomLoadout() {
      const pick = (key) => { const it = S.catOf(key).items; return it[(Math.random() * it.length) | 0].id; };
      const o = {};
      for (const k of ['banner', 'headband', 'mask', 'mawashi', 'headwear', 'jacket', 'throw', 'victory']) o[k] = Math.random() < 0.55 ? pick(k) : DEF_EQ[k];
      const tl = S.catOf('taunt').items;
      o.taunts = [0, 1, 2, 3].map(() => (Math.random() < 0.5 ? tl[(Math.random() * tl.length) | 0].id : null));
      return o;
    }
  }
  S.DEF_EQ = DEF_EQ;
  S.profile = new Profile();
  S.fmtYen = (n) => '¥' + Math.round(n).toLocaleString('en-US');
})();
