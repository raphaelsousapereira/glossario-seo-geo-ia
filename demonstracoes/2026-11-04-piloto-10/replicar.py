#!/usr/bin/env python3
"""Reavalia as capturas históricas, sem rede e sem executar seus scripts HTML.

Baixe evidencias.json, coletar.py e replicar.py para a mesma pasta.
Execute: python3 replicar.py
O JSON inclui exemplos redigidos, claramente identificados. Não contém runs de LLM.
"""
import base64,gzip,hashlib,io,json,tarfile,tempfile
from pathlib import Path,PurePosixPath
from coletar import analyse

ROOT=Path(__file__).resolve().parent
dataset=json.loads((ROOT/'evidencias.json').read_text())
archive=base64.b64decode(dataset['snapshot_archive']['data'],validate=True)
assert hashlib.sha256(archive).hexdigest()==dataset['snapshot_archive']['sha256']
assert len(archive)<10_000_000
pages={}
with tempfile.TemporaryDirectory() as directory:
    destination=Path(directory)
    total=0
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
        unpacked=stream.read(25_000_001)
    assert len(unpacked)<=25_000_000
    with tarfile.open(fileobj=io.BytesIO(unpacked),mode='r:') as tar:
        members=tar.getmembers()
        assert len(members)==dataset['snapshot_archive']['files']
        for member in members:
            p=PurePosixPath(member.name)
            assert member.isfile() and not p.is_absolute() and '..' not in p.parts
            assert p.parts[0] in {'raw','rendered'} and p.suffix=='.html'
            total+=member.size
            assert total<25_000_000
            target=destination.joinpath(*p.parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    for capture in dataset['captures']:
        path=destination/capture['file']
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==capture['sha256'],capture['id']
        assert capture['http_status']==200,capture['id']
        pages[capture['id']]=analyse(raw.decode('utf-8','replace'))
    literal_spans=0
    fixtures=[]
    for case in dataset['fixtures']['cases']:
        source=pages[case['source_id']]['visible_text']
        for criterion in case['criteria']:
            assert criterion['source'] in source,(case['page_id'],criterion['source'])
            literal_spans+=1
        fixtures.append({'page_id':case['page_id'],'criteria':len(case['criteria']),
            'good_preserved':sum(x['good']=='Preservado' for x in case['criteria']),
            'bad_preserved':sum(x['bad']=='Preservado' for x in case['criteria']),
            'bad_omitted':sum(x['bad']=='Omitido' for x in case['criteria']),
            'bad_contradicted':sum(x['bad']=='Contradito' for x in case['criteria'])})
    render=[]
    for identifier,item in dataset['rendering'].items():
        data=(destination/item['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['sha256']
        a=analyse(data.decode('utf-8','replace'))
        raw=pages[int(identifier)]
        assert a['answer']==raw['answer'] and bool(a['answer'])
        assert a['answer_in_visible_text'] and a['author_in_visible_text'] and a['concept_in_visible_text']
        render.append({'page_id':int(identifier),'same_answer':True,'selected_signals_in_text':3})
    hierarchy=[]
    for page in dataset['urls']['pilot']:
        forward=page['link'] in pages[819]['hrefs']
        reverse=pages[page['id']]['hub_link']
        assert forward and reverse,page['id']
        hierarchy.append({'page_id':page['id'],'hub_to_page':forward,'page_to_hub':reverse})
    print(json.dumps({'verified_captures':len(pages),'literal_evidence_spans':literal_spans,
        'rendering':render,'hierarchy':hierarchy,'controlled_annotations':fixtures,
        'llm_runs':0,'causal_effect_tested':False},ensure_ascii=False,indent=2))
