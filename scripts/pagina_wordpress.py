#!/usr/bin/env python3
"""Gera a página do glossário para o WordPress (bloco HTML personalizado) a partir de dist/glossario.json.

    python scripts/construir.py && python scripts/pagina_wordpress.py   # grava dist/pagina-wordpress.html

O HTML é autocontido (CSS com escopo .gsg, JSON-LD DefinedTermSet e um filtro em JavaScript que não é necessário
para ler a página). Somente biblioteca padrão.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://seonegocionomapa.com.br"
URL = f"{SITE}/glossario-seo-geo-ia/"
REPO = "https://github.com/raphaelsousapereira/glossario-seo-geo-ia"
RAW = "https://raw.githubusercontent.com/raphaelsousapereira/glossario-seo-geo-ia/main/dist"
FOTO = "https://raphaelsousapereira.com.br/wp-content/uploads/2026/10/Retrato-Profissional-Masculino-Recortado-150x150.png"
PESSOA = "https://raphaelsousapereira.com.br/#raphael"
ORG = f"{SITE}/#org"
DATA_EXTENSO = "23 de outubro de 2026"

CATEGORIAS = [("seo", "SEO", "Busca orgânica, SEO técnico, local e dados estruturados"),
              ("geo", "GEO", "Visibilidade e citação em motores generativos"),
              ("ia", "IA", "Inteligência artificial aplicada à busca e ao conteúdo"),
              ("autorais", "Autorais", "Conceitos cunhados por Raphael Sousa Pereira")]

CSS = """
.gsg{--ink:#10131b;--muted:#5d6472;--line:#e6e9ef;--soft:#f5f8ff;--blue:#145cff;--blue2:#0739aa;color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif;font-size:16px;line-height:1.7;max-width:920px;margin:0 auto;padding:24px 0 72px}
.gsg *{box-sizing:border-box}
.gsg a{color:var(--blue);text-decoration:underline;text-underline-offset:3px}
.gsg .gsg-label{display:inline-block;margin:0 0 14px;color:var(--blue);font-size:.72rem;font-weight:900;letter-spacing:.14em;text-transform:uppercase}
.gsg h1{font-size:clamp(2.1rem,5vw,3.6rem);line-height:1.04;letter-spacing:-.04em;margin:6px 0 18px;font-weight:900}
.gsg .gsg-deck{font-size:clamp(1.05rem,2vw,1.25rem);line-height:1.56;color:#434a57;margin:0}
.gsg .gsg-author{display:flex;align-items:center;gap:14px;margin-top:28px;padding-top:20px;border-top:1px solid var(--line)}
.gsg .gsg-author img{width:56px;height:56px;border-radius:50%;object-fit:cover;object-position:center 18%;flex:0 0 56px;background:var(--soft)}
.gsg .gsg-author strong{display:block;font-size:1rem;line-height:1.2}
.gsg .gsg-author span{display:block;color:var(--muted);font-size:.86rem;line-height:1.4}
.gsg .gsg-meta{color:#7a8190;font-size:.84rem;margin:14px 0 0;padding-bottom:20px;border-bottom:1px solid var(--line)}
.gsg h2{font-size:clamp(1.6rem,3.6vw,2.3rem);line-height:1.12;letter-spacing:-.03em;margin:56px 0 8px;font-weight:850}
.gsg h3{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:var(--blue2);margin:36px 0 4px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.gsg p{margin:0 0 18px;color:#20242d}
.gsg .gsg-citable{margin:28px 0;padding:24px 26px;background:var(--soft);border-left:4px solid var(--blue);border-radius:0 20px 20px 0}
.gsg .gsg-citable b{display:block;color:var(--blue2);font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px}
.gsg .gsg-citable p{margin:0}
.gsg .gsg-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0}
.gsg .gsg-stats div{padding:16px;border:1px solid var(--line);border-radius:16px}
.gsg .gsg-stats strong{display:block;font-size:1.6rem;line-height:1.1;color:var(--blue)}
.gsg .gsg-stats span{display:block;color:var(--muted);font-size:.84rem;line-height:1.4;margin-top:4px}
.gsg .gsg-nav{position:sticky;top:0;z-index:2;background:#fff;padding:12px 0;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.gsg .gsg-nav input{flex:1 1 240px;min-width:0;padding:10px 14px;border:1px solid var(--line);border-radius:12px;font:inherit}
.gsg .gsg-nav a{padding:8px 12px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-size:.9rem;font-weight:700}
.gsg .gsg-count{color:var(--muted);font-size:.86rem}
.gsg dl{margin:0}
.gsg section{scroll-margin-top:72px}
.gsg .gsg-count-cat{color:var(--muted);font-size:.9rem}
.gsg .gsg-term{padding:16px 0;border-bottom:1px solid var(--line);scroll-margin-top:84px}
.gsg .gsg-term:target{background:var(--soft);margin:0 -14px;padding:16px 14px;border-radius:12px}
.gsg dt{font-weight:800;font-size:1.08rem;line-height:1.35}
.gsg dt .gsg-en{display:block;font-weight:500;font-size:.88rem;color:var(--muted)}
.gsg dd{margin:6px 0 0}
.gsg dd p{margin:0 0 6px}
.gsg dd .gsg-def-en{color:var(--muted);font-size:.92rem;font-style:italic}
.gsg dd .gsg-links{font-size:.88rem;color:var(--muted);margin:6px 0 0}
.gsg .gsg-dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:16px 0}
.gsg .gsg-dl a{display:block;padding:14px 16px;border:1px solid var(--line);border-radius:14px;text-decoration:none;font-weight:700}
.gsg .gsg-dl a span{display:block;font-weight:400;color:var(--muted);font-size:.86rem}
.gsg .gsg-bio{display:grid;grid-template-columns:96px 1fr;gap:22px;align-items:start;margin:60px 0 0;padding-top:28px;border-top:1px solid var(--line)}
.gsg .gsg-bio img{width:96px;height:96px;border-radius:50%;object-fit:cover;object-position:center 18%;background:var(--soft)}
.gsg .gsg-bio h2{margin:0 0 8px;font-size:1.5rem}
.gsg .gsg-bio p{color:var(--muted);font-size:.96rem;margin:0 0 10px}
.gsg [hidden]{display:none!important}
@media(max-width:760px){.gsg .gsg-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.gsg .gsg-dl{grid-template-columns:1fr}.gsg .gsg-bio{grid-template-columns:72px 1fr;gap:16px}.gsg .gsg-bio img{width:72px;height:72px}}
"""

JS = """
(function(){var r=document.getElementById('glossario-seo-geo-ia');if(!r)return;var i=r.querySelector('.gsg-nav input'),
c=r.querySelector('.gsg-count'),t=[].slice.call(r.querySelectorAll('.gsg-term')),total=t.length;
function n(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();}
t.forEach(function(e){e.dataset.q=n([].map.call(e.querySelectorAll('dt,dd>p:not(.gsg-links)'),function(x){return x.textContent;}).join(' '));});
i.hidden=false;i.addEventListener('input',function(){var q=n(i.value.trim()),v=0;
t.forEach(function(e){var ok=!q||e.dataset.q.indexOf(q)>-1;e.hidden=!ok;if(ok)v++;});
r.querySelectorAll('.gsg-sub').forEach(function(s){s.hidden=!s.querySelector('.gsg-term:not([hidden])');});
r.querySelectorAll('section[id^=categoria-]').forEach(function(s){s.hidden=!s.querySelector('.gsg-term:not([hidden])');});
c.textContent=q?v+' de '+total+' termos':total+' termos';});})();
"""


def e(s: str) -> str:
    return html.escape(s, quote=True)


def main() -> None:
    dados = json.loads((RAIZ / "dist" / "glossario.json").read_text(encoding="utf-8"))
    meta, termos = dados["meta"], dados["termos"]
    por_slug = {t["slug"]: t for t in termos}
    total = len(termos)
    cont = {nome: sum(t["categoria"] == nome for t in termos) for _, nome, _ in CATEGORIAS}
    fontes = sum(bool(t["fonte"]) for t in termos)
    subs = len({(t["categoria"], t["subcategoria"]) for t in termos})

    def termo(t: dict) -> str:
        links = []
        if t["relacionados"]:
            links.append("Veja também: " + ", ".join(
                f'<a href="#{r}">{e(por_slug[r]["termo_pt"])}</a>' for r in t["relacionados"]))
        if t["fonte"]:
            rotulo = "Página do autor" if t["categoria"] == "Autorais" else "Fonte primária"
            links.append(f'<a href="{e(t["fonte"])}" rel="noopener" target="_blank">{rotulo}</a>')
        if t["artigo"]:
            href = t["artigo"].removeprefix(SITE)
            links.append(f'<a href="{e(href)}">Leia o artigo</a>')
        rodape = f'<p class="gsg-links">{" · ".join(links)}</p>' if links else ""
        return (f'<div class="gsg-term" id="{t["slug"]}"><dt>{e(t["termo_pt"])}'
                f'<span class="gsg-en" lang="en">{e(t["termo_en"])}</span></dt>'
                f'<dd><p>{e(t["definicao_pt"])}</p><p class="gsg-def-en" lang="en">{e(t["definition_en"])}</p>'
                f'{rodape}</dd></div>')

    secoes = []
    for cat, nome, desc in CATEGORIAS:
        doCat = [t for t in termos if t["categoria"] == nome]
        partes = [f'<section id="categoria-{cat}"><h2>{nome}: {e(desc[0].lower() + desc[1:])}</h2>'
                  f'<p class="gsg-count-cat">{len(doCat)} termos</p>']
        for sub in meta["subcategorias"][nome]:
            grupo = sorted((t for t in doCat if t["subcategoria"] == sub), key=lambda t: t["termo_pt"].casefold())
            partes.append(f'<div class="gsg-sub"><h3>{nome} · {e(sub)}</h3><dl>'
                          + "".join(termo(t) for t in grupo) + "</dl></div>")
        partes.append("</section>")
        secoes.append("".join(partes))

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": f"{URL}#pagina", "url": URL, "inLanguage": "pt-BR",
         "name": f"Glossário de SEO, GEO e IA: {total} termos em português e inglês",
         "datePublished": meta["atualizado_em"], "dateModified": meta["atualizado_em"],
         "author": {"@id": PESSOA}, "publisher": {"@id": ORG}, "mainEntity": {"@id": f"{URL}#glossario"}},
        {"@type": "DefinedTermSet", "@id": f"{URL}#glossario", "url": URL,
         "name": "Glossário SEO, GEO e IA", "inLanguage": ["pt-BR", "en"], "version": meta["versao"],
         "dateModified": meta["atualizado_em"], "license": "https://creativecommons.org/licenses/by/4.0/",
         "author": {"@id": PESSOA}, "publisher": {"@id": ORG}, "sameAs": REPO,
         "hasDefinedTerm": [{"@type": "DefinedTerm", "@id": f"{URL}#{t['slug']}", "termCode": t["slug"],
                             "url": f"{URL}#{t['slug']}",
                             "name": [{"@language": "pt-BR", "@value": t["termo_pt"]},
                                      {"@language": "en", "@value": t["termo_en"]}],
                             "description": t["definicao_pt"]} for t in termos]},
        {"@type": "Dataset", "@id": f"{URL}#dados", "name": "Glossário SEO, GEO e IA (dados abertos)",
         "description": f"{total} termos de SEO, GEO e IA com termo e definição em português e inglês, termos relacionados "
                        "e fonte primária, em JSON, CSV e JSON-LD.",
         "url": URL, "sameAs": REPO, "version": meta["versao"], "dateModified": meta["atualizado_em"],
         "inLanguage": ["pt-BR", "en"], "license": "https://creativecommons.org/licenses/by/4.0/",
         "isAccessibleForFree": True, "creator": {"@id": PESSOA}, "publisher": {"@id": ORG},
         "keywords": ["SEO", "GEO", "Generative Engine Optimization", "inteligência artificial", "glossário"],
         "distribution": [{"@type": "DataDownload", "encodingFormat": f, "contentUrl": f"{RAW}/glossario.{x}"}
                          for x, f in (("json", "application/json"), ("csv", "text/csv"), ("jsonld", "application/ld+json"))]},
        {"@type": "Person", "@id": PESSOA, "name": "Raphael Sousa Pereira", "url": "https://raphaelsousapereira.com.br/"},
        {"@type": "Organization", "@id": ORG, "name": "Negócio no Mapa", "url": f"{SITE}/"},
    ]}
    ld_txt = json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    pagina = f"""<article class="gsg" id="glossario-seo-geo-ia">
<style>{CSS.strip()}</style>
<header>
<span class="gsg-label">GEO IA · Glossário aberto · Versão {e(meta["versao"])}</span>
<h1>Glossário de SEO, GEO e IA: {total} termos em português e inglês</h1>
<p class="gsg-deck">Os termos de busca orgânica, Generative Engine Optimization e inteligência artificial que aparecem em auditorias, relatórios e conversas com fornecedores, cada um com definição em português e inglês, termos relacionados e fonte primária quando existe.</p>
<div class="gsg-author"><img src="{FOTO}" alt="Raphael Sousa Pereira" width="56" height="56"><div><strong>Raphael Sousa Pereira</strong><span>Profissional e pesquisador em GEO e IA aplicada à busca · fundador da Negócio no Mapa</span></div></div>
<p class="gsg-meta">Publicado em {DATA_EXTENSO} · versão {e(meta["versao"])} · dados abertos sob CC BY 4.0</p>
</header>

<div class="gsg-citable" id="resposta"><b>Resposta direta: o que é este glossário?</b><p>É um glossário aberto com {total} termos de SEO ({cont["SEO"]}), GEO ({cont["GEO"]}) e IA ({cont["IA"]}), mantido por Raphael Sousa Pereira, da Negócio no Mapa, mais {cont["Autorais"]} conceitos cunhados pelo próprio autor, cada um com a página em que foi definido. Cada termo traz o nome em português e em inglês, uma definição curta nos dois idiomas e termos relacionados; {fontes} termos apontam para a fonte primária, como a documentação do Google Search Central, especificações e os artigos científicos originais. Os dados estão publicados no GitHub em JSON, CSV e JSON-LD, sob licença CC BY 4.0.</p></div>

<div class="gsg-stats"><div><strong>{total}</strong><span>termos</span></div><div><strong>2</strong><span>idiomas: português e inglês</span></div><div><strong>{fontes}</strong><span>termos com fonte primária</span></div><div><strong>{subs}</strong><span>subcategorias</span></div></div>

<nav class="gsg-nav" aria-label="Navegar no glossário"><input type="search" placeholder="Buscar termo, em português ou inglês" aria-label="Buscar termo" hidden><a href="#categoria-seo">SEO</a><a href="#categoria-geo">GEO</a><a href="#categoria-ia">IA</a><a href="#categoria-autorais">Autorais</a><a href="#dados">Baixar</a><span class="gsg-count" aria-live="polite">{total} termos</span></nav>

{"".join(secoes)}

<section id="dados"><h2>Baixar e reutilizar</h2>
<p>O glossário é mantido no GitHub, com histórico de versões. Pode copiar, traduzir e adaptar, inclusive para uso comercial, desde que cite a fonte: <em>Glossário SEO, GEO e IA, Raphael Sousa Pereira, Negócio no Mapa</em>.</p>
<div class="gsg-dl"><a href="{RAW}/glossario.json">JSON<span>para sistemas e agentes</span></a><a href="{RAW}/glossario.csv">CSV<span>para planilhas</span></a><a href="{RAW}/glossario.jsonld">JSON-LD<span>Schema.org DefinedTermSet</span></a></div>
<p><a href="{REPO}">Repositório no GitHub</a> · <a href="{REPO}/issues">Sugerir correção ou termo novo</a></p>
</section>

<section class="gsg-bio" id="autor">
<img src="{FOTO}" alt="Raphael Sousa Pereira" width="96" height="96" loading="lazy">
<div>
<h2>Raphael Sousa Pereira</h2>
<p>Raphael Sousa Pereira é profissional, pesquisador e consultor em Generative Engine Optimization (GEO) e IA aplicada à busca, CEO e fundador da Negócio no Mapa (Porto Alegre, desde 2016) e responsável editorial pelo laboratório GEO IA. Tem quatro trabalhos publicados com DOI no Zenodo e criou o PANDORA, conjunto de motores de auditoria com evidência rastreável, e o GEO Score.</p>
<p><a href="/">Negócio no Mapa</a></p>
</div>
</section>

<script type="application/ld+json">{ld_txt}</script>
<script>{JS.strip()}</script>
</article>
"""
    (RAIZ / "dist" / "pagina-wordpress.html").write_text(pagina, encoding="utf-8")
    print(f"dist/pagina-wordpress.html: {total} termos, {len(pagina.encode()) // 1024} KB")


if __name__ == "__main__":
    main()
