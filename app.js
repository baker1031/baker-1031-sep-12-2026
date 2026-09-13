/* The Agency — homepage recreation: interaction layer */
(function () {
  'use strict';

  /* ── header: solid + shrunken once past the fold, hides on scroll-down ── */
  var header = document.getElementById('site-header');
  var toTop  = document.getElementById('toTop');
  var last   = window.scrollY;

  function onScroll() {
    var y = window.scrollY;

    // solid + compact once the video is behind you; the bar itself stays put
    header.classList.toggle('stuck', y > 40);
    toTop.classList.toggle('on', y > 600);
    last = y;
  }
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  toTop.addEventListener('click', function (e) {
    e.preventDefault();
    scrollTo({ top: 0, behavior: 'smooth' });
  });

  /* ── mobile menu ──────────────────────────────────────────────────────── */
  var burger = document.getElementById('burger');
  var nav    = document.querySelector('header nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      burger.classList.toggle('on', open);
      burger.setAttribute('aria-expanded', String(open));
    });
  }

  /* ── regions carousel: snap-scroll one page at a time ─────────────────── */
  var track = document.getElementById('regionTrack');
  if (track) {
    var prev = document.querySelector('.caro-nav.prev');
    var next = document.querySelector('.caro-nav.next');

    function page() {
      var card = track.querySelector('.region');
      return card ? card.getBoundingClientRect().width : track.clientWidth / 3;
    }
    function sync() {
      var max = track.scrollWidth - track.clientWidth - 2;
      prev.classList.toggle('disabled', track.scrollLeft <= 2);
      next.classList.toggle('disabled', track.scrollLeft >= max);
    }
    prev.addEventListener('click', function () { track.scrollBy({ left: -page() * 3, behavior: 'smooth' }); });
    next.addEventListener('click', function () { track.scrollBy({ left:  page() * 3, behavior: 'smooth' }); });
    track.addEventListener('scroll', sync, { passive: true });
    addEventListener('resize', sync);
    sync();

    /* click-and-drag, like the original's .dragging behaviour */
    var down = false, startX = 0, startLeft = 0, moved = 0;
    track.addEventListener('pointerdown', function (e) {
      down = true; moved = 0;
      startX = e.clientX; startLeft = track.scrollLeft;
      track.classList.add('dragging');
      track.style.scrollSnapType = 'none';
      track.style.scrollBehavior = 'auto';
    });
    addEventListener('pointermove', function (e) {
      if (!down) return;
      var dx = e.clientX - startX;
      moved = Math.max(moved, Math.abs(dx));
      track.scrollLeft = startLeft - dx;
    });
    addEventListener('pointerup', function () {
      if (!down) return;
      down = false;
      track.classList.remove('dragging');
      track.style.scrollSnapType = '';
      track.style.scrollBehavior = '';
    });
    track.addEventListener('click', function (e) {
      if (moved > 6) { e.preventDefault(); e.stopPropagation(); }
    }, true);
  }

  /* ── scroll-driven reveal fallback (Safari / older engines) ───────────── */
  var supportsViewTimeline =
    CSS.supports && CSS.supports('animation-timeline', 'view()');

  if (!supportsViewTimeline && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.05 });

    document.querySelectorAll('.reveal, .press article, .journal article')
      .forEach(function (el) { el.classList.add('reveal'); io.observe(el); });
  }

  /* ── hero search tabs ─────────────────────────────────────────────────── */
  document.querySelectorAll('.hero .tabs a').forEach(function (tab) {
    tab.addEventListener('click', function (e) {
      e.preventDefault();
      document.querySelectorAll('.hero .tabs a').forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
    });
  });

  /* ── ripple on the gradient buttons (.a-b-1 .ripple) ──────────────────── */
  document.querySelectorAll('.btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      var r = btn.getBoundingClientRect();
      var s = document.createElement('span');
      s.className = 'ripple';
      s.style.cssText =
        'position:absolute;border-radius:50%;background:#fff;pointer-events:none;' +
        'transform:translate(-50%,-50%);left:' + (e.clientX - r.left) + 'px;top:' +
        (e.clientY - r.top) + 'px;animation:ripples .5s linear';
      btn.appendChild(s);
      setTimeout(function () { s.remove(); }, 520);
    });
  });
})();
