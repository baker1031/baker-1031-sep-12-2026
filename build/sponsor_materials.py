"""The Sponsor Provided Materials directory (/learn/).

Every entry is a document written and published by the investment sponsor named on it. Baker 1031 did
not write them and does not republish their contents: the description on each row is an original
one-line summary, and the document itself is sent on request.

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
               'Tax Strategy', 'Retirement / Roth', 'Property Sectors', 'Market Research',
               'Firm Overview', 'Other']


def load():
    rows = json.load(open(DATA, encoding='utf-8'))
    return [r for r in rows if not any(p in (r.get('restrictions') or '').upper() for p in PRO_ONLY)]


def _slug(s):
    return ''.join(c if c.isalnum() else '-' for c in s.lower()).strip('-')


def render(rows=None, indent='        '):
    rows = rows if rows is not None else load()
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
            subject = 'Document request: ' + title[:80]
            meta = [e(r['sponsor'])]
            if r.get('date'):
                meta.append(e(r['date']))
            if r.get('audience') == 'advisor':
                meta.append('written for advisors')
            out.append(f'{i}    <li class="sm-item" data-sponsor="{e(r["sponsor"])}" data-topic="{e(topic)}">')
            out.append(f'{i}      <h3>{e(title)}</h3>')
            out.append(f'{i}      <p class="sm-desc">{e(r["description"])}</p>')
            out.append(f'{i}      <p class="sm-meta"><span class="sm-sponsor">{meta[0]}</span>'
                       + ''.join(f'<span>{m}</span>' for m in meta[1:]) + '</p>')
            out.append(f'{i}      <a class="sm-get" href="mailto:invest@baker1031.com?subject='
                       + _html.escape(subject.replace(" ", "%20"), quote=True) + '">Request a copy &rarr;</a>')
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
  sp.addEventListener('change', apply); tp.addEventListener('change', apply);
})();
</script>'''
