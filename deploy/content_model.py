"""Public site content: lossless template parsing, extraction and safe rendering."""
from copy import deepcopy
from html import escape, unescape
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlsplit

VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}


class Node:
    def __init__(self, tag='', attrs=(), start='', end=''):
        self.tag, self.attrs, self.start, self.end = tag, dict(attrs), start, end
        self.children = []

    def render(self):
        return self.start + ''.join(c.render() if isinstance(c, Node) else c for c in self.children) + self.end

    def all(self, tag=None, cls=None, id=None):
        found=[]
        for node in self.children:
            if not isinstance(node, Node): continue
            if (tag is None or node.tag==tag) and (cls is None or cls in node.attrs.get('class','').split()) and (id is None or node.attrs.get('id')==id):
                found.append(node)
            found.extend(node.all(tag,cls,id))
        return found

    def one(self, tag=None, cls=None, id=None):
        return self.all(tag,cls,id)[0]

    def text(self):
        return unescape(re.sub('<[^>]*>', '', ''.join(c.render() if isinstance(c,Node) else c for c in self.children))).strip()

    def set_text(self, text):
        if ' '.join(self.text().split()) != ' '.join(text.split()):
            self.children=[escape(text)]


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.root=Node(); self.stack=[self.root]; self.feed(source)

    def handle_starttag(self, tag, attrs):
        node=Node(tag,attrs,self.get_starttag_text());self.stack[-1].children.append(node)
        if tag not in VOID:self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag,attrs,self.get_starttag_text()))

    def handle_endtag(self, tag):
        if len(self.stack)>1 and self.stack[-1].tag==tag:
            self.stack.pop().end=f'</{tag}>'
        else:self.stack[-1].children.append(f'</{tag}>')

    def handle_data(self, data):self.stack[-1].children.append(data)
    def handle_entityref(self, name):self.handle_data('&'+name+';')
    def handle_charref(self, name):self.handle_data('&#'+name+';')
    def handle_comment(self, text):self.handle_data('<!--'+text+'-->')
    def handle_decl(self, decl):self.handle_data('<!'+decl+'>')


SECTIONS={'services':'services','principles':'honesty','discounts':'discounts','why':'features','tags':'complaints','steps':'how','important':'important','districts':'districts','cta':'order'}
LISTS={'services.items':('services-grid','service-row','h3','service-price'),
       'hero.features':('hero-proof','hero-proof-card','strong','small'),
       'pricing.items':('price-grid','price-card','h3','price-val'),
       'principles.items':('features','feature','h3','p'),
       'discounts.items':('discounts','discount-card','h3','p'),
       'why.items':('features','feature','h3','p'),
       'steps.items':('steps','step','h3','p'),
       'important.items':('warnings','warning',None,'p'),
       'tags.items':('pills','pill',None,None),
       'districts.items':('districts','district',None,None)}


def scope(root, section):
    if section=='hero':return root.one(cls='hero')
    if section=='pricing':return root.one(id='services')
    return root.one(id=SECTIONS[section])


def field(node, selector):
    return node.one(tag=selector) if selector in ('h3','p','strong','small') else node.one(cls=selector)


def extract(source):
    root=Document(source).root
    data={'global':{'phone':'+7 (905) 303-15-51','phoneRaw':'+79053031551',
        'hours':root.one(cls='header-hours').text().replace('20:00звонки','20:00 — звонки').replace('22:00по','22:00 по'),'city':'Самара',
        'ctaButton':root.one(cls='header-cta').text(),
        'seoTitle':root.one('title').text(),
        'seoDescription':next(n.attrs['content'] for n in root.all('meta') if n.attrs.get('name')=='description'),
        'ogTitle':'','ogDescription':''},
        'hero':{'title':root.one('h1').text(),'subtitle':root.one(cls='hero-lead').text()},
        'form':{'disabledNotice':root.one(id='intakeStatus').text(),
            'steps':[n.one('h3').text() for n in root.all(cls='quiz-step')[:3]],
            'successTitle':root.one(cls='quiz-success').one('h3').text(),
            'successText':root.one(cls='quiz-success').one('p').text()},
        'pricing':{'title':root.one(cls='service-subhead').one('h2').text(),
            'subtitle':root.one(cls='service-subhead').one('p').text(),
            'footnotes':[n.text() for n in root.one(cls='price-note').all('li')]}}
    for key in SECTIONS:
        block=scope(root,key);data[key]={'title':block.one('h2').text()}
        if key in ('principles','discounts'):data[key]['subtitle']=block.one(cls='section-head').one('p').text()
    data['discounts']['footnote']=scope(root,'discounts').all('p')[-1].text()
    data['cta']['text']=scope(root,'cta').one('p').text()
    data['cta']['maxInstruction']=root.one(id='maxHelp').text()
    for path,(container,cls,title,text) in LISTS.items():
        key,name=path.split('.');rows=[]
        for node in scope(root,key).one(cls=container).all(cls=cls):
            if text is None:rows.append(node.text());continue
            row={'text':field(node,text).text()}
            if title:row['title']=field(node,title).text()
            if key=='services':row['problem']=node.one('a').attrs['data-service-problem']
            if key=='pricing':row={'name':row.pop('title'),'price':row.pop('text')}
            if key=='discounts':row['percent']=node.one(cls='pct').text()
            if key=='important':row['icon']=node.one(cls='warning-icon').text()
            rows.append(row)
        data[key][name]=rows
    return data


def validate(data, shape):
    """A strict public-content schema; import cannot carry leads or executable HTML."""
    def visit(value, example, path):
        if isinstance(example,dict):
            if not isinstance(value,dict) or set(value)!=set(example):raise ValueError(f'{path}: unexpected or missing fields')
            return {k:visit(value[k],v,path+'.'+k) for k,v in example.items()}
        if isinstance(example,list):
            if not isinstance(value,list) or len(value)>100:raise ValueError(f'{path}: invalid list')
            return [visit(v,example[0],path+'[]') for v in value]
        if not isinstance(value,str) or len(value)>20000 or '\x00' in value:raise ValueError(f'{path}: invalid text')
        return value
    result=visit(data,shape,'content')
    if not re.fullmatch(r'\+7[0-9]{10}',result['global']['phoneRaw']):raise ValueError('phoneRaw must use +7XXXXXXXXXX')
    allowed_problems={'Не сливает воду','Не набирает воду','Не отжимает','Не крутится барабан','Не включается','Не греет воду','Протекает','Шумит / вибрирует','Не открывается дверца','Показывает ошибку','Выбивает автомат','Другое / не знаю'}
    if any(row['problem'] not in allowed_problems for row in result['services']['items']):raise ValueError('Unknown form problem')
    if len(result['form']['steps'])!=3:raise ValueError('The request form must retain three steps')
    if not result['global']['seoTitle'].strip() or not result['hero']['title'].strip():raise ValueError('Title and H1 are required')
    return result


def render_home(source,data):
    root=Document(source).root
    root.one('title').set_text(data['global']['seoTitle'])
    for node in root.all('meta'):
        if node.attrs.get('name')=='description':node.start='<meta name="description" content="'+escape(data['global']['seoDescription'],quote=True)+'">'
    for key in ('ogTitle','ogDescription'):
        if data['global'][key]:root.one('head').children.append('<meta property="og:'+('title' if key=='ogTitle' else 'description')+'" content="'+escape(data['global'][key],quote=True)+'">')
    root.one('h1').set_text(data['hero']['title'])
    root.one(cls='hero-lead').set_text(data['hero']['subtitle'])
    root.one(cls='header-cta').set_text(data['global']['ctaButton'])
    hours=root.one(cls='header-hours')
    hours_text=data['global']['hours']
    if ' — ' in hours_text:
        first,last=hours_text.split(' — ',1);hours.children=['<strong>'+escape(first)+'</strong>','<span>'+escape(last)+'</span>']
    elif ' по ' in hours_text:
        first,last=hours_text.split(' по ',1);hours.children=['<strong>'+escape(first)+'</strong>',escape('по '+last)]
    else:hours.set_text(hours_text)
    root.one(cls='hero-badge').set_text('Ремонт стиральных машин · '+data['global']['city'])
    root.one(id='intakeStatus').set_text(data['form']['disabledNotice'])
    for node,text in zip(root.all(cls='quiz-step')[:3],data['form']['steps']):node.one('h3').set_text(text)
    root.one(cls='quiz-success').one('h3').set_text(data['form']['successTitle'])
    root.one(cls='quiz-success').one('p').set_text(data['form']['successText'])
    root.one(id='maxHelp').set_text(data['cta']['maxInstruction'])
    for key in SECTIONS:
        block=scope(root,key);block.one('h2').set_text(data[key]['title'])
        if 'subtitle' in data[key]:block.one(cls='section-head').one('p').set_text(data[key]['subtitle'])
    root.one(cls='service-subhead').one('h2').set_text(data['pricing']['title'])
    root.one(cls='service-subhead').one('p').set_text(data['pricing']['subtitle'])
    scope(root,'discounts').all('p')[-1].set_text(data['discounts']['footnote'])
    scope(root,'cta').one('p').set_text(data['cta']['text'])
    for path,(container,cls,title,text) in LISTS.items():
        key,name=path.split('.');parent=scope(root,key).one(cls=container);templates=parent.all(cls=cls);nodes=[]
        for i,row in enumerate(data[key][name]):
            template=templates[min(i,len(templates)-1)]
            if key=='services':
                template=next((n for n in templates if n.one('a').attrs.get('data-service-problem')==row['problem']),template)
            node=deepcopy(template)
            if text is None:node.set_text(row)
            else:
                if title:field(node,title).set_text(row['name' if key=='pricing' else 'title'])
                field(node,text).set_text(row['price' if key=='pricing' else 'text'])
                if key=='pricing':
                    price_node=node.one(cls='price-val')
                    price_class='price-val free' if row['price'].strip().lower()=='бесплатно' else 'price-val'
                    price_node.start=re.sub(r'class="[^"]*"','class="'+price_class+'"',price_node.start)
                if key=='discounts':node.one(cls='pct').set_text(row['percent'])
                if key=='important':node.one(cls='warning-icon').set_text(row['icon'])
                if key=='steps':node.one(cls='step-num').set_text(str(i+1).zfill(2))
            nodes.append(node)
        parent.children=nodes
    root.one(cls='price-note').one('ul').children=['<li>'+escape(v)+'</li>' for v in data['pricing']['footnotes']]
    return root.render()


def validate_reviews(reviews):
    if not isinstance(reviews, list) or len(reviews) > 30:
        raise ValueError('reviews.json must contain at most 30 reviews')
    for review in reviews:
        if not isinstance(review, dict) or set(review) != {'name', 'text', 'date', 'sourceUrl', 'permission'}:
            raise ValueError('Review requires name, text, date, sourceUrl and permission')
        name, quote, date, url = (review[key] for key in ('name', 'text', 'date', 'sourceUrl'))
        if review['permission'] is not True or any(not isinstance(v, str) or not v.strip() for v in (name, quote, date, url)):
            raise ValueError('Publish only nonempty reviews with recorded permission')
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or len(url) > 2048:
            raise ValueError('Review source must be a public HTTPS URL')
        if len(name) > 100 or len(quote) > 1200 or len(date) > 40:
            raise ValueError('Review field too long')
    return reviews


def validate_bundle(bundle, root):
    if not isinstance(bundle,dict) or set(bundle)-{'reviews'}!={'version','site','articles'} or type(bundle['version']) is not int or bundle['version']!=1:
        raise ValueError('Expected a version 1 public content export')
    shape=extract((root/'web/index.html').read_text())
    site=validate(bundle['site'],shape)
    article_shape=json.loads((root/'content/articles.json').read_text())[0]
    articles=bundle['articles']
    if not isinstance(articles,list) or not 1<=len(articles)<=100:raise ValueError('Expected 1–100 articles')
    seen=set()
    for article in articles:
        if not isinstance(article,dict) or set(article)!=set(article_shape):raise ValueError('Invalid article fields')
        if any(not isinstance(v,str) or not v.strip() or len(v)>100000 for v in article.values()):raise ValueError('Invalid article text')
        slug=article['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug) or slug in seen or slug=='index':raise ValueError('Invalid or duplicate article URL')
        seen.add(slug)
        for url in re.findall(r'\]\(([^)]+)\)',article['body']):
            if not (url.startswith('https://') or re.fullmatch(r'/articles/[a-z0-9-]+/',url) or url in ('/#quiz','/#prices')):
                raise ValueError('Article links must use HTTPS or known site routes')
        for slug_link in re.findall(r'\]\(/articles/([a-z0-9-]+)/\)',article['body']):
            if slug_link not in {a['slug'] for a in articles}:raise ValueError('Article references a missing publication')
    reviews = bundle['reviews'] if 'reviews' in bundle else json.loads((root/'content/reviews.json').read_text(encoding='utf-8'))
    return {'version':1,'site':site,'articles':articles,'reviews':validate_reviews(reviews)}


def load_bundle(root, path=None):
    if path:
        if path.stat().st_size>2_000_000:raise ValueError('Content export is too large')
        bundle=json.loads(path.read_text(encoding='utf-8'))
    else:
        bundle={'version':1,'site':json.loads((root/'content/site.json').read_text()),
                'articles':json.loads((root/'content/articles.json').read_text())}
    return validate_bundle(bundle,root)
