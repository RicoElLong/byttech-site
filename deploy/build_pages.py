"""Build review or production pages without publishing or inventing owner details."""
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / 'web'
DOCUMENTS = ('index', 'privacy', 'consent', 'legal', 'work-order')
PUBLIC_PHONE = '+79053031551'


def inline(text):
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{m[2]}">{m[1]}</a>', text)
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def markdown(text):
    """Render the small, trusted editorial Markdown subset used by articles.json."""
    output = []
    for block in text.split('\n\n'):
        if block.startswith('### '):
            output.append('<h2>' + inline(block[4:]) + '</h2>')
        elif block.startswith('> '):
            output.append('<blockquote><p>' + inline(block[2:]) + '</p></blockquote>')
        elif block.startswith('- '):
            output.append('<ul>' + ''.join('<li>' + inline(line[2:]) + '</li>' for line in block.splitlines()) + '</ul>')
        elif re.match(r'1\. ', block):
            output.append('<ol>' + ''.join('<li>' + inline(re.sub(r'^\d+\. ', '', line)) + '</li>' for line in block.splitlines()) + '</ol>')
        else:
            output.append('<p>' + inline(block) + '</p>')
    return '\n'.join(output)


def build(destination: Path, *, production=False):
    if destination.exists():
        raise ValueError('Use a new output directory.')
    base = os.getenv('SITE_URL', '').rstrip('/')
    if base:
        parsed = urlsplit(base)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
            raise ValueError('SITE_URL must be a confirmed HTTPS site URL (optional subdirectory).')
    if production and not base:
        raise ValueError('Confirmed SITE_URL is required for production canonical and sitemap.')
    endpoint = os.getenv('REQUEST_API_URL', '').strip()
    approved = os.getenv('WEB_DOCUMENTS_CONFIRMED') == '1'
    fields = {f'OWNER_{key}': os.getenv(f'OWNER_{key}', '').strip() for key in ('NAME','INN','ADDRESS','PHONE','EMAIL')}
    fields['OWNER_PHONE'] = fields['OWNER_PHONE'] or PUBLIC_PHONE
    if not re.fullmatch(r'\+7\d{10}', fields['OWNER_PHONE']):
        raise ValueError('OWNER_PHONE must use +7XXXXXXXXXX.')
    if endpoint:
        api = urlsplit(endpoint)
        if api.scheme != 'https' or not api.hostname or api.username or api.path != '/api/requests' or api.query or api.fragment:
            raise ValueError('REQUEST_API_URL must end with /api/requests over HTTPS.')
        if not approved or any(not v for v in fields.values()):
            raise ValueError('API requires confirmed documents and complete owner details.')
        if not re.fullmatch(r'\d{12}', fields['OWNER_INN']) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', fields['OWNER_EMAIL']):
            raise ValueError('Check OWNER_INN and OWNER_EMAIL.')
    has_email = bool(fields['OWNER_EMAIL'])
    has_owner = all(fields.values())
    fields['OWNER_PHONE_E164'] = fields['OWNER_PHONE']
    for key in fields:
        if not fields[key]:
            fields[key] = 'Будет указан до включения приёма заявок'
    home = (WEB_ROOT / 'index.html').read_text()
    if not has_owner:
        home = re.sub(r'<p class="footer-legal">.*?</p>', '<p class="footer-legal">Приём заявок на сайте отключён. Реквизиты и документы ожидают подтверждения.</p>', home, flags=re.S)
    if endpoint:
        home = home.replace('data-api="" data-config=""', f'data-api="{escape(endpoint, quote=True)}" data-config="{escape(endpoint.rsplit("/",1)[0] + "/requests/config", quote=True)}"')
    style = re.search(r'<style>.*?</style>', home, re.S)[0]
    header = re.search(r'<header\b.*?</header>', home, re.S)[0]
    footer = re.search(r'<footer\b.*?</footer>', home, re.S)[0]
    scripts = '\n'.join(re.findall(r'<script>.*?</script>', home, re.S))
    # Article navigation is absolute within the site, never relative to the article.
    article_header = re.sub(r'href="#([^\"]*)"', r'href="/#\1"', header).replace('href="/articles/"', 'href="/articles/" aria-current="page"')
    article_footer = re.sub(r'href="#([^\"]*)"', r'href="/#\1"', footer)
    articles = json.loads((ROOT / 'content/articles.json').read_text())
    extra = '<style>.article-content{max-width:820px;margin:40px auto;padding:0 20px 40px;overflow-wrap:anywhere}.article-content h1{font-size:clamp(28px,4vw,44px);line-height:1.2;margin:24px 0}.article-content h2{font-size:25px;margin:32px 0 16px}.article-content p,.article-content ul,.article-content ol{margin:16px 0}.article-content ul,.article-content ol{padding-left:25px}.article-content a:not(.btn){color:var(--blue-dark);text-decoration:underline}.article-content blockquote{border-left:4px solid var(--blue);padding-left:20px}.article-cards{display:grid;gap:20px}.article-card{padding:24px;border:1px solid var(--border);border-radius:16px}.article-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:32px}.article-actions .btn{white-space:normal}[aria-current=page]{text-decoration:underline}@media(max-width:600px){.article-actions .btn{width:100%}}</style>'
    def page(title, description, body):
        return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description,quote=True)}">{style}{extra}</head><body>{article_header}<main class="article-content">{body}</main>{article_footer}{scripts}</body></html>'
    output = {'index.html':home, 'request-form.js':(WEB_ROOT / 'request-form.js').read_text()}
    for name in DOCUMENTS[1:]:
        output[name+'.html'] = (WEB_ROOT / (name+'.html')).read_text()
    cards = ''.join(f'<article class="article-card"><h2><a href="/articles/{a["slug"]}/">{escape(a["heading"])}</a></h2><p>{escape(a["description"])}</p></article>' for a in articles)
    output['articles/index.html'] = page('Статьи о ремонте стиральных машин | БытТех','Как разобраться в поломке стиральной машины, выбрать мастера и заранее уточнить стоимость ремонта','<h1>Статьи о ремонте стиральных машин</h1><div class="article-cards">'+cards+'</div>')
    for a in articles:
        related = ''.join(f'<li><a href="/articles/{other["slug"]}/">{escape(other["heading"])}</a></li>' for other in articles if other['slug'] != a['slug'])
        body = f'<a href="/articles/">← Все статьи</a><article><h1>{escape(a["heading"])}</h1>{markdown(a["body"])}</article><div class="article-actions"><a class="btn btn-outline" href="/#prices">Посмотреть цены</a><a class="btn btn-primary" href="/#quiz">Вызвать мастера в Самаре</a></div><nav aria-label="Связанные материалы"><h2>Читайте также</h2><ul>{related}</ul></nav>'
        output[f'articles/{a["slug"]}/index.html'] = page(a['title'],a['description'],body)
    def site_link(match, depth):
        attr,path,fragment = match.groups()
        if path in ('/privacy','/consent','/legal','/work-order'):
            path += '.html'
        return f'{attr}="' + ('../'*depth or './') + path.lstrip('/') + (fragment or '') + '"'
    urls=[]
    for filename,source in list(output.items()):
        if not filename.endswith('.html'): continue
        if not has_email:
            source = re.sub(r'<a href="mailto:[^"]*">.*?</a>', 'Email будет указан до включения приёма заявок', source)
        path = '/' if filename=='index.html' else '/' + filename.removesuffix('index.html')
        if base:
            canonical=base+path
            source=source.replace('</head>',f'<link rel="canonical" href="{escape(canonical,quote=True)}"></head>')
            urls.append(canonical)
        source=re.sub(r'\{\{(OWNER_[A-Z_0-9]+)\}\}',lambda m:escape(fields[m[1]],quote=True),source)
        source=re.sub(r'\b(href|src)="(/(?!/)[^"#]*)(#[^"]*)?"',lambda m:site_link(m,len(Path(filename).parts)-1),source)
        output[filename]=source
    if base:
        output['sitemap.xml']='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(u)+'</loc></url>' for u in urls)+'</urlset>'
    output['robots.txt']='User-agent: *\nAllow: /\n'+(f'Sitemap: {base}/sitemap.xml\n' if base else '')
    output['404.html']='<!doctype html><html lang="ru"><meta charset="utf-8"><title>Страница не найдена | БытТех</title><h1>Страница не найдена</h1><a href="'+(base or '/')+'/articles/">Все статьи</a></html>'
    destination.mkdir(parents=True)
    for filename,source in output.items():
        target=destination/filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',nargs='?',type=Path,default=Path('_site'))
    parser.add_argument('--production',action='store_true')
    args=parser.parse_args()
    build(args.destination,production=args.production)
