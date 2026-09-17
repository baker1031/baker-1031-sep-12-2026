"""Shared <head> metadata + structured data for every page: title, description, canonical, robots preview controls,
Open Graph / Twitter cards, icons, and the site-wide Organization / Person / WebSite graph (referenced by @id from
article, breadcrumb and page markup elsewhere). One place to edit; every builder calls head()."""
import json, html as _html

SITE = 'https://baker1031.com'
NAME = 'Baker 1031 Investments'
OG_IMAGE = SITE + '/assets/media/og-card.png'
ORG_ID, PERSON_ID, SITE_ID = SITE + '/#org', SITE + '/#jerry', SITE + '/#website'
BLURB = ('Founded by Jerry Baker, Baker 1031 Investments is a real estate securities brokerage specializing in 1031 exchange '
         'investment solutions. Clients work directly with Jerry to evaluate investments based on their income needs, long-term '
         'goals, and exchange requirements. The firm has offices in San Francisco and Los Angeles, California.')

def esc(s): return _html.escape(str(s if s is not None else ''), quote=True)

ICONS = '''<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" sizes="48x48" href="/assets/icons/favicon-48.png">
<link rel="icon" type="image/png" sizes="96x96" href="/assets/icons/favicon-96.png">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/icons/favicon-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#00A071">'''

def organization():
    return {
        '@type': ['Organization', 'FinancialService'], '@id': ORG_ID, 'name': NAME, 'alternateName': 'Baker 1031',
        'url': SITE + '/', 'logo': {'@type': 'ImageObject', 'url': SITE + '/assets/media/logo.png'}, 'image': OG_IMAGE,
        'description': BLURB, 'founder': {'@id': PERSON_ID}, 'employee': {'@id': PERSON_ID},
        'telephone': '+1-415-965-0552', 'email': 'invest@baker1031.com', 'areaServed': 'US',
        'knowsAbout': ['1031 exchange', 'Delaware Statutory Trust (DST)', '721 exchange (UPREIT)', 'Opportunity Zone funds',
                       'Oil and gas royalties', 'Real estate investment trusts (REITs)', 'Real estate credit'],
        'address': [
            {'@type': 'PostalAddress', 'streetAddress': '1700 Montgomery St, Ste 108', 'addressLocality': 'San Francisco', 'addressRegion': 'CA', 'postalCode': '94111', 'addressCountry': 'US'},
            {'@type': 'PostalAddress', 'streetAddress': '2100 E Grand Ave, 1st Floor', 'addressLocality': 'El Segundo', 'addressRegion': 'CA', 'postalCode': '90245', 'addressCountry': 'US'}],
        'contactPoint': [
            {'@type': 'ContactPoint', 'telephone': '+1-415-965-0552', 'contactType': 'sales', 'areaServed': 'US', 'availableLanguage': 'English'},
            {'@type': 'ContactPoint', 'telephone': '+1-310-896-4227', 'contactType': 'sales', 'areaServed': 'US', 'availableLanguage': 'English'}],
        'memberOf': {'@type': 'Organization', 'name': 'Aurora Securities, Inc.', 'url': 'https://brokercheck.finra.org/firm/summary/46147'},
    }

def person():
    return {
        '@type': 'Person', '@id': PERSON_ID, 'name': 'Jerry Baker', 'alternateName': 'Gerald F. Baker, III',
        'jobTitle': 'Founder', 'worksFor': {'@id': ORG_ID}, 'url': SITE + '/learn/jerry-baker-bio/',
        'image': SITE + '/assets/media/jerry-baker.jpg', 'email': 'invest@baker1031.com',
        'sameAs': ['https://brokercheck.finra.org/individual/summary/7537416'],
        'knowsAbout': ['1031 exchange', 'Delaware Statutory Trusts', '721 exchange', 'Opportunity Zone funds', 'Real estate private equity'],
    }

def website():
    return {'@type': 'WebSite', '@id': SITE_ID, 'name': NAME, 'alternateName': 'Baker 1031', 'url': SITE + '/', 'publisher': {'@id': ORG_ID}, 'inLanguage': 'en-US'}

def webpage(url, name, desc, extra=None, page_type='WebPage'):
    d = {'@type': page_type, '@id': url + '#webpage', 'url': url, 'name': name, 'description': desc,
         'isPartOf': {'@id': SITE_ID}, 'about': {'@id': ORG_ID}, 'inLanguage': 'en-US'}
    if extra: d.update(extra)
    return d

def breadcrumbs(items):
    """items: [(name, url), ...] from Home outward."""
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, **({'item': u} if u else {})} for i, (n, u) in enumerate(items)]}

def jsonld(graph):
    return '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('</', '<\\/') + '</script>'

def head(*, title, desc, canonical, og_type='website', image=OG_IMAGE, image_alt='Baker 1031 Investments', noindex=False, graph=None, robots_extra=''):
    """Everything that belongs in <head> after charset/viewport: title, description, canonical, robots, OG/Twitter, icons, JSON-LD."""
    robots = 'noindex' if noindex else 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
    parts = [
        f'<title>{esc(title)}</title>',
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{esc(canonical)}">',
        f'<meta name="robots" content="{robots}{robots_extra}">',
        '<meta property="og:type" content="' + og_type + '">',
        f'<meta property="og:site_name" content="{NAME}">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{esc(canonical)}">',
        f'<meta property="og:image" content="{esc(image)}">',
        '<meta property="og:image:width" content="1200">' if image == OG_IMAGE else '',
        '<meta property="og:image:height" content="630">' if image == OG_IMAGE else '',
        f'<meta property="og:image:alt" content="{esc(image_alt)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{esc(image)}">',
        ICONS,
    ]
    if graph: parts.append(jsonld(graph))
    return '\n'.join(p for p in parts if p)
