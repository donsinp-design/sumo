'use strict';
// Procedural audio: no files. Thumps, slaps, taiko, wooden clappers, crowd.
(function () {
  class Audio {
    constructor() { this.ctx = null; this.muted = false; this.excite = 0; }
    init() {
      if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      const c = this.ctx = new AC();
      this.master = c.createGain(); this.master.gain.value = 0.85;
      const comp = c.createDynamicsCompressor();
      comp.threshold.value = -14; comp.ratio.value = 4;
      this.master.connect(comp); comp.connect(c.destination);
      // noise buffer
      const len = c.sampleRate * 2, buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
      let b0 = 0, b1 = 0, b2 = 0;
      for (let i = 0; i < len; i++) {
        const wht = Math.random() * 2 - 1;
        b0 = 0.99765 * b0 + wht * 0.099; b1 = 0.963 * b1 + wht * 0.2965; b2 = 0.57 * b2 + wht * 1.0526;
        d[i] = (b0 + b1 + b2 + wht * 0.1848) * 0.2;
      }
      this.noise = buf;
      // crowd bus (no constant bed: the crowd only reacts to moments)
      this.crowdBus = c.createGain(); this.crowdBus.gain.value = 0.9;
      const cl = c.createBiquadFilter(); cl.type = 'lowpass'; cl.frequency.value = 3200;
      this.crowdBus.connect(cl); cl.connect(this.master);
      // feet scraping on clay
      const s2 = c.createBufferSource(); s2.buffer = buf; s2.loop = true; s2.playbackRate.value = 1.3;
      const lp = c.createBiquadFilter(); lp.type = 'bandpass'; lp.frequency.value = 2400; lp.Q.value = 1.2;
      this.slideGain = c.createGain(); this.slideGain.gain.value = 0;
      s2.connect(lp); lp.connect(this.slideGain); this.slideGain.connect(this.master); s2.start();
    }
    get ok() { return !!this.ctx && !this.muted; }
    env(g, t, a, peak, dec) {
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(peak, t + a);
      g.gain.exponentialRampToValueAtTime(0.0001, t + a + dec);
    }
    noiseHit(t, type, freq, q, peak, dec, rate) {
      const c = this.ctx, s = c.createBufferSource(); s.buffer = this.noise; s.playbackRate.value = rate || 1;
      const f = c.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q || 1;
      const g = c.createGain(); this.env(g, t, 0.003, peak, dec);
      s.connect(f); f.connect(g); g.connect(this.master);
      s.start(t, Math.random() * 1.5); s.stop(t + dec + 0.1);
      return f;
    }
    tone(t, type, f0, f1, peak, dec) {
      const c = this.ctx, o = c.createOscillator(); o.type = type;
      o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dec);
      const g = c.createGain(); this.env(g, t, 0.004, peak, dec);
      o.connect(g); g.connect(this.master); o.start(t); o.stop(t + dec + 0.1);
    }
    thump(power) {
      if (!this.ok) return; const t = this.ctx.currentTime, p = Math.min(1, power / 10);
      this.tone(t, 'sine', 110 + p * 30, 38, 0.5 + p * 0.6, 0.18 + p * 0.25);
      this.noiseHit(t, 'lowpass', 500 + p * 900, 0.7, 0.35 + p * 0.5, 0.12 + p * 0.15);
      this.noiseHit(t, 'bandpass', 2400, 1.2, 0.15 * p, 0.05);
    }
    slap(power) {
      if (!this.ok) return; const t = this.ctx.currentTime, p = Math.min(1, power / 5);
      this.noiseHit(t, 'highpass', 1400, 0.7, 0.35 + p * 0.35, 0.05 + p * 0.03);
      this.noiseHit(t, 'bandpass', 3200, 2, 0.2, 0.03);
      this.tone(t, 'sine', 220, 90, 0.15 * p, 0.06);
    }
    whoosh(len) {
      if (!this.ok) return; const t = this.ctx.currentTime, d = len || 0.25;
      const f = this.noiseHit(t, 'bandpass', 400, 1.4, 0.18, d);
      f.frequency.setValueAtTime(350, t); f.frequency.exponentialRampToValueAtTime(1800, t + d);
    }
    scuff() { if (!this.ok) return; this.noiseHit(this.ctx.currentTime, 'bandpass', 1100, 0.9, 0.12, 0.09, 0.8); }
    grab() {
      if (!this.ok) return; const t = this.ctx.currentTime;
      this.noiseHit(t, 'lowpass', 900, 0.8, 0.35, 0.09);
      this.tone(t, 'sine', 140, 70, 0.25, 0.1);
    }
    taiko() {
      if (!this.ok) return; const t = this.ctx.currentTime;
      this.tone(t, 'sine', 95, 48, 0.9, 0.55);
      this.tone(t, 'triangle', 180, 80, 0.2, 0.2);
      this.noiseHit(t, 'lowpass', 300, 0.6, 0.5, 0.25);
    }
    // hyoshigi: one sharp strike of the wooden clappers, right on the start call
    hyoshigi() {
      if (!this.ok) return; const t = this.ctx.currentTime;
      this.noiseHit(t, 'bandpass', 2600, 16, 1.0, 0.06);
      this.noiseHit(t, 'bandpass', 1500, 10, 0.6, 0.05);
      this.tone(t, 'square', 2100, 2000, 0.07, 0.03);
    }
    clack() {
      if (!this.ok) return; const t = this.ctx.currentTime;
      for (const dt of [0, 0.13]) {
        this.noiseHit(t + dt, 'bandpass', 2300, 14, 0.9, 0.08);
        this.tone(t + dt, 'square', 1750, 1700, 0.05, 0.04);
      }
    }
    // crowd reaction: many short 'voice' grains (vowel-ish band-passed noise) instead of a wash
    cheer(amount, dur) {
      if (!this.ok) return;
      const c = this.ctx, t0 = c.currentTime, d = dur || 1.2;
      const n = Math.round(10 + amount * 70);
      for (let i = 0; i < n; i++) {
        const st = t0 + Math.pow(Math.random(), 1.6) * d;
        const len = 0.08 + Math.random() * 0.28;
        const s = c.createBufferSource(); s.buffer = this.noise; s.playbackRate.value = 0.8 + Math.random() * 0.5;
        const f = c.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 5 + Math.random() * 6;
        const f0 = 380 + Math.random() * 1300;
        f.frequency.setValueAtTime(f0, st); f.frequency.linearRampToValueAtTime(f0 * (0.85 + Math.random() * 0.4), st + len);
        const g = c.createGain();
        const fall = 1 - (st - t0) / (d * 1.2);
        const pk = (0.04 + Math.random() * 0.08) * (0.4 + amount) * Math.max(0.15, fall);
        g.gain.setValueAtTime(0.0001, st); g.gain.exponentialRampToValueAtTime(pk, st + len * 0.3); g.gain.exponentialRampToValueAtTime(0.0001, st + len);
        s.connect(f); f.connect(g); g.connect(this.crowdBus);
        s.start(st, Math.random() * 1.5); s.stop(st + len + 0.05);
      }
    }
    swell(amount, dur) { this.cheer(amount, dur); }
    roar() { this.cheer(1.2, 2.6); }
    clap() {
      if (!this.ok) return; const t = this.ctx.currentTime;
      this.noiseHit(t, 'bandpass', 1500, 1.4, 0.9, 0.06);
      this.noiseHit(t, 'highpass', 2500, 0.8, 0.35, 0.04);
      this.noiseHit(t + 0.045, 'bandpass', 1300, 1, 0.12, 0.12);
    }
    slide(level) {
      if (!this.ctx) return; const g = this.slideGain.gain;
      g.setTargetAtTime(this.muted ? 0 : Math.min(0.12, level * 0.05), this.ctx.currentTime, 0.04);
    }
    blip(hi) { if (!this.ok) return; this.tone(this.ctx.currentTime, 'triangle', hi ? 880 : 520, hi ? 1320 : 480, 0.12, 0.07); }
  }
  S.Audio = Audio;
})();
