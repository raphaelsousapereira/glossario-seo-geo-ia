#!/usr/bin/env python3
"""Coleta documental pública. Não consulta LLMs nem mede ganho de citação.

python coletar.py            # nova coleta HTTP, com data própria
python coletar.py --offline  # reavalia os arquivos preservados
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
SKIP = {'script','style','noscript','template','head'}
BLOCK = {'address','article','aside','blockquote','div','dl','fieldset','footer','form','h1','h2','h3','h4','h5','h6','header','hr','main','nav','ol','p','pre','section','table','ul'}

class Node:
    def __init__(self, tag='root', attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or []), []
    def text(self):
        if self.tag in SKIP:
            return ''
        return ' '.join(x if isinstance(x,str) else x.text() for x in self.children)
    def nodes(self):
        yield self
        for c in self.children:
            if isinstance(c,Node):
                yield from c.nodes()

class DOM(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        # WordPress wpautop pode deixar <p> antes de <main>/<section>.
        # O navegador fecha esse parágrafo implicitamente ao abrir o bloco.
        if tag in BLOCK:
            for i in range(len(self.stack)-1,0,-1):
                if self.stack[i].tag == 'p':
                    del self.stack[i:]
                    break
        node = Node(tag,attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag,attrs))
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        self.stack[-1].children.append(data)
    def by_class(self, value):
        return [n for n in self.root.nodes() if value in n.attrs.get('class','').split()]

def norm(value):
    return re.sub(r'\s+',' ',value).strip()

def analyse(html):
    dom = DOM(html)
    labs = dom.by_class('lab')
    body = labs[0] if labs else dom.root
    abstract = dom.by_class('lab-abstract')
    concepts = dom.by_class('rsp-conceito-autoral')
    visible = norm(body.text())
    answer = norm(abstract[0].text()) if abstract else ''
    hrefs = [n.attrs.get('href','') for n in body.nodes() if n.tag == 'a']
    faqs = []
    json_errors = []
    for n in dom.root.nodes():
        if n.tag=='script' and n.attrs.get('type')=='application/ld+json':
            raw=''.join(c for c in n.children if isinstance(c,str))
            try:
                obj=json.loads(raw)
                if obj.get('@type')=='FAQPage':
                    for q in obj.get('mainEntity',[]):
                        faqs.append(norm(q.get('acceptedAnswer',{}).get('text','')))
            except Exception as exc:
                json_errors.append(str(exc))
    return {
        'answer':answer,'visible_words':len(visible.split()),
        'answer_in_visible_text':bool(answer) and answer in visible,
        'author_in_visible_text':'Raphael Sousa Pereira' in visible,
        'concept_in_visible_text':bool(concepts) and bool(norm(concepts[0].text())),
        'main_image_count':sum(n.tag=='img' for n in body.nodes()),
        'hub_link':'https://raphaelsousapereira.com.br/perguntas/' in hrefs,
        'hrefs':hrefs,'faq_answer_matches':bool(answer) and answer in faqs,
        'json_errors':json_errors,'visible_text':visible,
    }

def fetch(item):
    identifier=str(item['id'])
    dest=ROOT/'raw'/f'{identifier}.html'
    at=dt.datetime.now(dt.timezone.utc).isoformat()
    headers={'User-Agent':'Raphael-Research-Demo/1.0','Accept':'text/html','Accept-Language':'pt-BR'}
    result={'id':item['id'],'url':item['link'],'collected_at_utc':at,'request_headers':headers}
    try:
        with urllib.request.urlopen(urllib.request.Request(item['link'],headers=headers),timeout=30) as response:
            data=response.read()
            result.update(http_status=response.status,content_type=response.headers.get('Content-Type',''))
    except urllib.error.HTTPError as exc:
        data=exc.read()
        result.update(http_status=exc.code,error=str(exc))
    except Exception as exc:
        return dict(result,error=str(exc),http_status=None)
    dest.write_bytes(data)
    result.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),file=f'raw/{identifier}.html')
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--offline',action='store_true')
    args=ap.parse_args()
    urls=(json.loads((ROOT/'urls.json').read_text()) if (ROOT/'urls.json').exists()
          else json.loads((ROOT/'evidencias.json').read_text())['urls'])
    (ROOT/'raw').mkdir(exist_ok=True)
    unique={x['id']:x for group in urls.values() for x in group}
    if args.offline:
        captures=json.loads((ROOT/'captures.json').read_text())
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            captures=list(executor.map(fetch,unique.values()))
        (ROOT/'captures.json').write_text(json.dumps(captures,ensure_ascii=False,indent=2))
    byid={x['id']:x for x in captures}
    pages={}
    for identifier,item in unique.items():
        c=byid[identifier]
        p=ROOT/'raw'/f'{identifier}.html'
        pages[str(identifier)]=dict(c,analysis=analyse(p.read_text(errors='replace')) if p.exists() and c['http_status']==200 else None)
    rendering={}
    for identifier in [902,903,905]:
        f=ROOT/'rendered'/f'{identifier}-full.html'
        if not f.exists():
            continue
        html=f.read_text()
        a=analyse(html)
        initial=pages[str(identifier)]['analysis']
        rendering[str(identifier)]={
            'file':str(f.relative_to(ROOT)),
            'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
            'answer':a['answer'],
            'same_answer_initial_and_inspection':bool(initial) and initial['answer']==a['answer'],
            'answer_in_extracted_text':a['answer_in_visible_text'],
            'author_in_extracted_text':a['author_in_visible_text'],
            'concept_in_extracted_text':a['concept_in_visible_text'],
        }
    hub=pages['819']['analysis']
    hierarchy=[]
    for p in urls['pilot']:
        a=pages[str(p['id'])]['analysis']
        hierarchy.append({'id':p['id'],'url':p['link'],'wordpress_parent':p['parent'],
            'hub_links_to_page':bool(hub) and p['link'] in hub['hrefs'],
            'page_links_to_hub':bool(a) and a['hub_link']})
    result={
        'protocol':'RSP-DOC-DEMO-2026-11-04-v1','author':'Raphael Sousa Pereira',
        'scope':'Coleta documental; não é benchmark de respostas de LLMs.',
        'pages':pages,'rendering':rendering,'hierarchy':hierarchy,
        'pilot_ids':[x['id'] for x in urls['pilot']],
        'comparison_ids':[x['id'] for x in urls['control']],
        'llm_runs':[],
    }
    (ROOT/'observations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'captured':len(captures),'http_200':sum(x.get('http_status')==200 for x in captures),
      'errors':[{'id':x['id'],'error':x.get('error')} for x in captures if x.get('http_status')!=200],
      'rendering':rendering,'hierarchy':hierarchy},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
