/* Animated favicon for the Baker 1031 bar mark.
 *
 * Browsers do not animate a GIF favicon: only Firefox ever did, Chrome and Edge show the first
 * frame, and Safari does not animate favicons at all. The only technique that works across
 * browsers is to draw each frame yourself and swap the <link rel="icon"> element on a timer,
 * which is what this does.
 *
 * Geometry is taken from the real mark (assets/icons/favicon-512.png): three white bars on
 * #00A071, each 16% of the width, at 10% / 42% / 74% from the left, spanning 7.4% to 92.6%
 * vertically. The animation moves each bar's top edge only, so the bars keep their exact
 * width and position and the peak of the cycle is the static logo.
 *
 * It stays quiet when it should: no animation under prefers-reduced-motion, paused while the
 * tab is hidden, and if anything throws the static PNG/ICO favicons are left exactly as they
 * were. To turn it off, drop the <script> tag that loads this file.
 */
(function () {
  'use strict';

  var GREEN = '#00A071';
  var SIZE = 64;                 // drawn large; browsers downscale to 16/32 cleanly
  var BAR_X = [0.10, 0.42, 0.74];
  var BAR_W = 0.16;
  var TOP = 0.0738, BOTTOM = 0.9258;   // the static mark's bar extent
  var MIN_FRAC = 0.42;           // shortest a bar gets, as a fraction of its full height
  var STAGGER = 4;               // frames between one bar's dip and the next
  var DIP = 10;                  // frames a single bar takes to dip and come back
  var REST = 20;                 // frames held on the exact static mark between sweeps
  var FRAMES = (3 - 1) * STAGGER + DIP + REST;   // 38 frames, ~3s, 1.6s of it at rest
  var FRAME_MS = 80;             // ~12fps; plenty at 16px

  var link = null, original = [], frames = null, idx = 0, timer = null, started = false;

  /* One bar's height on a given frame. A bar sits at full height except during its own
     dip window, so the cycle begins and ends on the exact static mark and the wave reads
     as something passing through it rather than as a permanently restless icon. */
  function barHeight(frame, i, full) {
    var start = i * STAGGER;
    if (frame >= start && frame < start + DIP) {
      var u = (frame - start) / DIP;
      var d = (1 - Math.cos(2 * Math.PI * u)) / 2;             // 0 -> 1 -> 0, smooth
      return full * (1 - (1 - MIN_FRAC) * d);
    }
    return full;
  }

  function draw(frame) {
    var c = document.createElement('canvas');
    c.width = c.height = SIZE;
    var g = c.getContext('2d');
    if (!g) return null;
    g.fillStyle = GREEN;
    g.fillRect(0, 0, SIZE, SIZE);
    g.fillStyle = '#FFFFFF';
    var full = (BOTTOM - TOP) * SIZE;
    var base = BOTTOM * SIZE;
    for (var i = 0; i < BAR_X.length; i++) {
      var h = barHeight(frame, i, full);
      g.fillRect(Math.round(BAR_X[i] * SIZE), Math.round(base - h),
                 Math.round(BAR_W * SIZE), Math.round(h));
    }
    return c.toDataURL('image/png');
  }

  function build() {
    var out = [];
    for (var f = 0; f < FRAMES; f++) {
      var d = draw(f);
      if (!d) return null;
      out.push(d);
    }
    return out;
  }

  function show(href) {
    // Changing href alone is not reliably repainted, so the element is replaced each frame.
    var next = document.createElement('link');
    next.rel = 'icon';
    next.type = 'image/png';
    next.href = href;
    if (link && link.parentNode) link.parentNode.replaceChild(next, link);
    else document.head.appendChild(next);
    link = next;
  }

  function tick() {
    idx = (idx + 1) % frames.length;
    show(frames[idx]);
  }

  function play() {
    if (timer || !frames) return;
    timer = setInterval(tick, FRAME_MS);
  }

  function pause() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function restore() {
    pause();
    if (link && link.parentNode) link.parentNode.removeChild(link);
    link = null;
    for (var i = 0; i < original.length; i++) document.head.appendChild(original[i]);
    original = [];
    started = false;
  }

  function start() {
    if (started) return;
    try {
      if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      frames = build();
      if (!frames) return;
      started = true;
      // take the static icons out of the head so the browser cannot prefer one of them,
      // and keep them to put back if the animation is ever stopped
      var stat = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]');
      for (var i = 0; i < stat.length; i++) {
        original.push(stat[i]);
        stat[i].parentNode.removeChild(stat[i]);
      }
      show(frames[0]);
      if (!document.hidden) play();
    } catch (e) {
      // leave the static favicon alone
      try { restore(); } catch (e2) {}
    }
  }

  try {
    document.addEventListener('visibilitychange', function () {
      if (!started) return;
      document.hidden ? pause() : play();
    });
    window.addEventListener('pagehide', pause);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
  } catch (e) {}
})();
