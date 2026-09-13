/*
  Baker 1031 — the four interactive tools on /learn/mineral-rights-1031-guide/.

  The guide shipped the markup and 47 element ids for these tools but no script
  (build.js strips <script> from article markdown), so every one of them was
  inert: an empty quiz body, a permanently disabled button, verdict panels
  reading "—". Everything below restates what the article already says in
  sections 02, 03, 04, 06 and 07 -- the classification table is the article's
  own table -- rather than adding any new position on the tax treatment.

  Educational only. Nothing here is a legal or tax determination.
*/
(function () {
  'use strict';
  if (!document.getElementById('tool-qual')) return;   // not this page

  var $ = function (id) { return document.getElementById(id); };
  var on = function (el, ev, fn) { if (el) el.addEventListener(ev, fn); };

  // ---------------------------------------------------------------- tool 1
  // Section 03's table, verbatim, plus section 04's duration override.
  var INTEREST = {
    mineralfee: { name: 'Mineral fee',              base: 'yes',   note: 'You own the minerals themselves, which is a fee interest in real property.' },
    royalty:    { name: 'Royalty interest',         base: 'yes',   note: 'A royalty that runs with the reserve is real property under <em>Crichton</em>.' },
    orri:       { name: 'Overriding royalty (ORRI)',base: 'yes',   note: 'An ORRI qualifies when it lasts the life of the lease it is carved from.' },
    working:    { name: 'Working interest',         base: 'yes',   note: 'An operating interest in the minerals — real property, and it carries the costs.' },
    npi:        { name: 'Net profits interest',     base: 'maybe', note: 'Usually qualifies, but an NPI is structure-sensitive: how it is drafted decides it.' },
    term:       { name: 'Term / carved-out royalty',base: 'no',    note: 'Limited to a set number of years or barrels, so it fails the duration test.' },
    prodpay:    { name: 'Production payment',       base: 'no',    note: 'An assignment of future income, not an interest in land (<em>P.G. Lake</em>).' }
  };

  var VERDICT = {
    yes:   { cls: 'ok',   head: 'Likely qualifies as real property' },
    maybe: { cls: 'warn', head: 'Depends on how it is drafted' },
    no:    { cls: 'bad',  head: 'Likely does not qualify' }
  };

  var dur = 'perp';

  function qualify() {
    var kind = INTEREST[$('mInterest').value];
    var invest = $('mInvest').checked;
    var v = kind.base;
    var why = kind.note;

    // Section 04: duration overrides the label, in one direction only.
    if (dur === 'term' && v !== 'no') {
      v = 'no';
      why = kind.name + ' normally qualifies, but a <strong>fixed term or quantity</strong> ' +
            'fails the durability test — the federal duration rule overrides the state-law label.';
    } else if (dur === 'perp' && v === 'no') {
      why = kind.note + ' Calling it perpetual does not cure that: the interest still ends ' +
            'when the stated term or quantity is met.';
    }

    // Section 02: held for investment or business is a threshold requirement.
    if (!invest && v !== 'no') {
      v = 'no';
      why = 'Section 1031 reaches only real property <strong>held for investment or use in a ' +
            'trade or business</strong>. Property held as dealer inventory is excluded whatever ' +
            'its duration.';
    }

    var box = $('mVerdict');
    box.className = 'vbox ' + VERDICT[v].cls;
    $('mVh').textContent = VERDICT[v].head;
    $('mVp').innerHTML = why + ' <span class="vcav">Your facts and state law control; confirm with ' +
      'a qualified intermediary and tax counsel.</span>';
  }

  on($('mInterest'), 'change', qualify);
  on($('mInvest'), 'change', qualify);
  var durBtns = document.querySelectorAll('#mDur button');
  Array.prototype.forEach.call(durBtns, function (b) {
    b.addEventListener('click', function () {
      Array.prototype.forEach.call(durBtns, function (x) { x.classList.remove('on'); });
      b.classList.add('on');
      dur = b.getAttribute('data-d');
      qualify();
    });
  });

  // ---------------------------------------------------------------- tool 2
  // Section 06: real property is broadly like-kind to real property; the hard
  // stops are the interests that are not real property, on either side.
  var SIDE = {
    perp:    { name: 'a perpetual mineral or royalty interest', real: true },
    working: { name: 'a working interest',                      real: true },
    fee:     { name: 'fee real estate',                         real: true },
    dst:     { name: 'a DST interest',                          real: true },
    term:    { name: 'a term or carved-out royalty',            real: false },
    prodpay: { name: 'a production payment',                    real: false }
  };

  function match() {
    var f = SIDE[$('mFrom').value], t = SIDE[$('mTo').value];
    var box = $('mMatch');
    if (f.real && t.real) {
      box.className = 'vbox ok';
      $('mMh').textContent = 'Like-kind';
      $('mMp').innerHTML = 'Both sides are real property, and after 2017 real property is broadly ' +
        'like-kind to other real property — so ' + f.name + ' can be exchanged for ' + t.name + '. ' +
        '<span class="vcav">Deadlines, debt replacement and the qualified-intermediary rules still apply.</span>';
      return;
    }
    var bad = !f.real && !t.real ? 'Neither side is real property'
            : !f.real ? 'The relinquished side is not real property'
            : 'The replacement side is not real property';
    box.className = 'vbox bad';
    $('mMh').textContent = 'Not like-kind';
    $('mMp').innerHTML = bad + '. ' + (!f.real ? f.name.charAt(0).toUpperCase() + f.name.slice(1)
      : t.name.charAt(0).toUpperCase() + t.name.slice(1)) +
      ' is an income right rather than an interest in land, so it breaks the like-kind chain. ' +
      '<span class="vcav">A pairing that fails here is a taxable sale, not a deferred exchange.</span>';
  }
  on($('mFrom'), 'change', match);
  on($('mTo'), 'change', match);

  // ---------------------------------------------------------------- tool 3
  var CHECKS = [
    ['A qualified intermediary is engaged <strong>before</strong> the sale closes',
     'The QI has to be in place at closing. Engaging one afterwards cannot be fixed retroactively.'],
    ['You never take receipt of, or control over, the proceeds',
     'Actual or constructive receipt of the money ends the exchange, however briefly it is held.'],
    ['The interest you are selling is real property held for investment or business',
     'Sections 02 to 04 above: a perpetual interest qualifies, a term interest or production payment does not.'],
    ['Replacement property is identified in writing within 45 days',
     'Unambiguous description, signed, delivered to the QI. The clock starts the day the sale closes.'],
    ['The replacement closes within 180 days of the sale',
     'Or by your tax-return due date including extensions, whichever comes first.'],
    ['You replace equal or greater value, and equal or greater debt',
     'Anything you take out in cash or relieved debt is boot, and boot is taxable up to your gain.']
  ];

  var chk = $('mChk');
  if (chk) {
    chk.innerHTML = CHECKS.map(function (c, i) {
      return '<label class="ckrow"><input type="checkbox" id="mC' + i + '">' +
             '<span class="ckt"><b>' + c[0] + '</b><em>' + c[1] + '</em></span></label>';
    }).join('');
  }

  function fmtDate(d) {
    return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }

  function deadlines() {
    var raw = $('mSaleDate').value;
    if (!raw) { $('m45').textContent = '—'; $('m180').textContent = '—'; return; }
    var parts = raw.split('-');
    var base = new Date(Date.UTC(+parts[0], +parts[1] - 1, +parts[2]));
    var d45 = new Date(base.getTime()); d45.setUTCDate(d45.getUTCDate() + 45);
    var d180 = new Date(base.getTime()); d180.setUTCDate(d180.getUTCDate() + 180);
    $('m45').textContent = fmtDate(d45);
    $('m180').textContent = fmtDate(d180);

    var today = new Date();
    var days = Math.floor((d45 - today) / 86400000);
    var flag = $('mFlag');
    if (days < 0) {
      flag.className = 'flag bad';
      flag.innerHTML = 'The 45-day identification window closed on ' + fmtDate(d45) + '.';
    } else if (days <= 14) {
      flag.className = 'flag warn';
      flag.innerHTML = days + (days === 1 ? ' day' : ' days') + ' left to identify. ' +
        'Mineral replacements can take longer than that to underwrite — line up backups now.';
    } else {
      flag.className = 'flag';
      flag.innerHTML = days + ' days until the identification deadline. Both dates count ' +
        '<strong>calendar</strong> days, including weekends and holidays, with no extension for either.';
    }
  }

  function score() {
    var n = 0;
    for (var i = 0; i < CHECKS.length; i++) { if ($('mC' + i) && $('mC' + i).checked) n++; }
    $('mScore').textContent = n;
    var v = $('mVerd'), s = $('mVerdSub');
    if (n === CHECKS.length) {
      v.textContent = 'All six conditions met';
      s.textContent = 'The structure looks sound. Confirm the specifics with your QI and tax counsel.';
    } else if (n >= 4) {
      v.textContent = 'Close, but not there yet';
      s.textContent = 'Any single unmet condition can make the whole exchange taxable.';
    } else if (n > 0) {
      v.textContent = 'Significant gaps';
      s.textContent = 'Work through the unchecked items before you commit to a closing date.';
    } else {
      v.textContent = 'Check the conditions';
      s.textContent = 'Your exchange readiness updates live.';
    }
  }

  on($('mSaleDate'), 'change', function () { deadlines(); });
  on($('mSaleDate'), 'input', function () { deadlines(); });
  on(chk, 'change', score);

  // ---------------------------------------------------------------- tool 4
  var QUESTIONS = [
    { q: 'How would you describe your mineral income today?',
      a: [['Steady and material to me', 'keep'],
          ['Declining or unpredictable', 'exchange'],
          ['Somewhere in between', 'split']] },
    { q: 'How much do you want to be involved in managing it?',
      a: [['I follow my wells and enjoy it', 'keep'],
          ['I would rather someone else handled it', 'exchange'],
          ['Less than now, but not nothing', 'split']] },
    { q: 'What matters more over the next ten years?',
      a: [['Upside if commodity prices run', 'keep'],
          ['Predictable income I can plan around', 'exchange'],
          ['Both, in some proportion', 'split']] },
    { q: 'Will heirs eventually divide this position?',
      a: [['Not a concern', 'keep'],
          ['Yes, and dividing minerals worries me', 'exchange'],
          ['Possibly, some of it', 'split']] }
  ];

  var PATHS = {
    keep: { name: 'Keep the minerals',
      why: 'Your answers point to an interest that is still doing its job. Minerals are among the ' +
           'highest-yielding interests available, and nothing here suggests a reason to trade that ' +
           'away. A 1031 is a tool, not an obligation.',
      trade: 'What you keep: the yield and the commodity upside. What you keep too: the depletion ' +
             'curve, the price swings, and the administration.' },
    exchange: { name: 'Exchange into real estate',
      why: 'Your answers describe the position minerals are usually exchanged out of — income that ' +
           'declines and swings, management you would rather not do, and an asset that is awkward to ' +
           'divide. A qualifying interest can go into a DST or net-lease portfolio with the gain deferred.',
      trade: 'What you gain: predictability, professional management, and an asset that divides ' +
             'cleanly. What you give up: the commodity upside and day-to-day control.' },
    split: { name: 'Exchange part, keep the rest',
      why: 'Your answers pull in both directions, which is the common case — and it does not have to ' +
           'be all-or-nothing. Exchanging part of a mineral position into a DST while keeping the ' +
           'rest is a well-worn play.',
      trade: 'What you gain: a floor of predictable income without giving up the upside entirely. ' +
             'What it costs: two positions to track instead of one, and the exchanged portion still ' +
             'has to clear the 45- and 180-day deadlines.' }
  };

  var answers = [];

  var qbody = $('mQuizBody');
  if (qbody) {
    qbody.innerHTML = QUESTIONS.map(function (item, qi) {
      return '<div class="qblock"><div class="qq">' + (qi + 1) + '. ' + item.q + '</div><div class="qa">' +
        item.a.map(function (opt, ai) {
          return '<button type="button" class="qopt" data-q="' + qi + '" data-a="' + ai + '">' +
                 opt[0] + '</button>';
        }).join('') + '</div></div>';
    }).join('');
  }

  function refreshQuiz() {
    $('mQuizGo').disabled = answers.filter(Boolean).length !== QUESTIONS.length;
  }

  on(qbody, 'click', function (e) {
    var b = e.target.closest ? e.target.closest('.qopt') : null;
    if (!b) return;
    var qi = +b.getAttribute('data-q'), ai = +b.getAttribute('data-a');
    Array.prototype.forEach.call(qbody.querySelectorAll('.qopt[data-q="' + qi + '"]'), function (x) {
      x.classList.remove('on');
    });
    b.classList.add('on');
    answers[qi] = QUESTIONS[qi].a[ai][1];
    refreshQuiz();
  });

  on($('mQuizGo'), 'click', function () {
    var tally = { keep: 0, exchange: 0, split: 0 };
    answers.forEach(function (k) { if (k) tally[k]++; });
    // A split answer leans both ways, so it counts toward each pure path too --
    // otherwise four mixed answers would produce a tie at zero.
    var lean = { keep: tally.keep + tally.split * 0.5,
                 exchange: tally.exchange + tally.split * 0.5,
                 split: tally.split + Math.min(tally.keep, tally.exchange) };
    var best = Object.keys(lean).reduce(function (a, b) { return lean[b] > lean[a] ? b : a; });
    var path = PATHS[best];
    var total = lean.keep + lean.exchange + lean.split || 1;

    $('mRName').textContent = path.name;
    $('mRWhy').textContent = path.why;
    $('mRBars').innerHTML = ['keep', 'split', 'exchange'].map(function (k) {
      var pct = Math.round(lean[k] / total * 100);
      return '<div class="rbar"><span class="rl">' + PATHS[k].name + '</span>' +
             '<span class="rt"><i style="width:' + pct + '%"></i></span>' +
             '<span class="rv">' + pct + '%</span></div>';
    }).join('');
    $('mRTrade').textContent = path.trade;
    $('mQuizResult').classList.add('show');
    $('mQuizResult').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  on($('mQuizReset'), 'click', function () {
    answers = [];
    Array.prototype.forEach.call(qbody.querySelectorAll('.qopt'), function (x) { x.classList.remove('on'); });
    $('mQuizResult').classList.remove('show');
    refreshQuiz();
  });

  // ---------------------------------------------------------------- start
  qualify();
  match();
  deadlines();
  score();
  refreshQuiz();
})();
