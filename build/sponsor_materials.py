"""The Sponsor Provided Materials directory (/learn/).

Every entry is a document written and published by the investment sponsor named on it. Baker 1031 did
not write them and does not host them: the description on each row is an original one-line summary, and
the link goes to the sponsor's own page, so each document is read in the place and form its author
published it. Where a sponsor has no page for a piece, the row falls back to their library.

Data: build/sponsor-materials.json. Expanded into content/pages/learn/index.html at the marker
<!--sponsor-materials--> by build_pages.py.
"""
import html as _html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'sponsor-materials.json')

# Pieces the sponsor marked for professional or institutional use are not listed on an investor page.
PRO_ONLY = ('INVESTMENT PROFESSIONAL USE ONLY', 'FINANCIAL PROFESSIONAL USE ONLY', 'FOR INSTITUTIONAL USE ONLY')

TOPIC_ORDER = ['1031 Exchange', 'DST Structure', '721 Exchange / UPREIT', 'Opportunity Zones',
               'Tax Strategy', 'Retirement / Roth', 'Property Sectors', 'Credit', 'Market Research',
               'Firm Overview', 'Other']


def load():
    blob = json.load(open(DATA, encoding='utf-8'))
    rows = blob['documents'] if isinstance(blob, dict) else blob
    rows = [r for r in rows if not any(p in (r.get('restrictions') or '').upper() for p in PRO_ONLY)]
    return rows, (blob.get('hubs', {}) if isinstance(blob, dict) else {})


def _slug(s):
    return ''.join(c if c.isalnum() else '-' for c in s.lower()).strip('-')


def render(rows=None, hubs=None, indent='        '):
    if rows is None:
        rows, loaded_hubs = load()
        hubs = hubs if hubs is not None else loaded_hubs
    hubs = hubs or {}
    e = _html.escape
    by_topic = {}
    for r in rows:
        by_topic.setdefault(r['topic'], []).append(r)
    sponsors = sorted({r['sponsor'] for r in rows})
    i = indent
    out = []

    out.append(f'{i}<div class="sm-bar">')
    out.append(f'{i}  <label class="sm-field"><span>Sponsor</span>')
    out.append(f'{i}    <select id="sm-sponsor"><option value="">All sponsors</option>'
               + ''.join(f'<option>{e(s)}</option>' for s in sponsors) + '</select></label>')
    out.append(f'{i}  <label class="sm-field"><span>Topic</span>')
    out.append(f'{i}    <select id="sm-topic"><option value="">All topics</option>'
               + ''.join(f'<option>{e(t)}</option>' for t in TOPIC_ORDER if t in by_topic) + '</select></label>')
    out.append(f'{i}  <p class="sm-count" id="sm-count" role="status">{len(rows)} documents</p>')
    out.append(f'{i}</div>')

    for topic in TOPIC_ORDER:
        items = by_topic.get(topic)
        if not items:
            continue
        out.append(f'{i}<section class="sm-group" data-topic="{e(topic)}">')
        out.append(f'{i}  <h2 id="{_slug(topic)}">{e(topic)}</h2>')
        out.append(f'{i}  <ul class="sm-list">')
        for r in sorted(items, key=lambda x: (x['sponsor'], x['file'])):
            title = r['file'].rsplit('.', 1)[0].replace('_', ' ').replace(' _ ', ' — ').strip()
            title = title.replace(' (1)', '')
            url = r.get('url') or hubs.get(r['sponsor'], '')
            own_page = bool(r.get('url'))
            meta = [e(r['sponsor'])]
            if r.get('date'):
                meta.append(e(r['date']))
            if r.get('audience') == 'advisor':
                meta.append('written for advisors')
            out.append(f'{i}    <li class="sm-item" data-sponsor="{e(r["sponsor"])}" data-topic="{e(topic)}">')
            head = (f'<a href="{e(url)}" target="_blank" rel="noopener nofollow">{e(title)}</a>'
                    if url else e(title))
            out.append(f'{i}      <h3>{head}</h3>')
            out.append(f'{i}      <p class="sm-desc">{e(r["description"])}</p>')
            out.append(f'{i}      <p class="sm-meta"><span class="sm-sponsor">{meta[0]}</span>'
                       + ''.join(f'<span>{m}</span>' for m in meta[1:]) + '</p>')
            if url:
                label = (f'Read on {e(r["sponsor"])}&rsquo;s site' if own_page
                         else f'Find it in {e(r["sponsor"])}&rsquo;s library')
                out.append(f'{i}      <a class="sm-get" href="{e(url)}" target="_blank" rel="noopener nofollow">{label} &rarr;</a>')
            else:
                out.append(f'{i}      <a class="sm-get" href="mailto:invest@baker1031.com?subject=Document%20request">Ask me for a copy &rarr;</a>')
            out.append(f'{i}    </li>')
        out.append(f'{i}  </ul>')
        out.append(f'{i}</section>')
    return '\n'.join(out)


SCRIPT = '''<script>
(function(){
  var sp = document.getElementById('sm-sponsor'), tp = document.getElementById('sm-topic'),
      count = document.getElementById('sm-count');
  if(!sp || !tp) return;
  var items = [].slice.call(document.querySelectorAll('.sm-item')),
      groups = [].slice.call(document.querySelectorAll('.sm-group'));
  function apply(){
    var s = sp.value, t = tp.value, n = 0;
    items.forEach(function(el){
      var ok = (!s || el.getAttribute('data-sponsor') === s) && (!t || el.getAttribute('data-topic') === t);
      el.hidden = !ok; if(ok) n++;
    });
    groups.forEach(function(g){
      g.hidden = !g.querySelector('.sm-item:not([hidden])');
    });
    count.textContent = n + (n === 1 ? ' document' : ' documents');
  }
  // ?sponsor= / ?topic= preselect the filters, so a link elsewhere on the site can point at one slice
  try {
    var q = new URLSearchParams(window.location.search);
    function preset(sel, want){
      if(!want) return;
      var hit = [].slice.call(sel.options).filter(function(o){
        return o.value && o.value.toLowerCase() === want.toLowerCase(); })[0];
      if(hit) sel.value = hit.value;
    }
    preset(sp, q.get('sponsor')); preset(tp, q.get('topic'));
  } catch(e){}
  sp.addEventListener('change', apply); tp.addEventListener('change', apply);
  apply();
})();
</script>'''
