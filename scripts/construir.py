#!/usr/bin/env python3
"""Valida os termos em termos/*.txt e gera o glossário em JSON, CSV, JSON-LD e Markdown.

    python scripts/construir.py            # valida e grava os arquivos gerados
    python scripts/construir.py --check    # só confere: falha se algo estiver inválido ou desatualizado

Somente biblioteca padrão (Python 3.10 ou mais novo).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TERMOS = RAIZ / "termos"
VERSAO = "1.0.0"
DATA = "2026-10-23"
SITE = "https://seonegocionomapa.com.br"
REPO = "https://github.com/raphaelsousapereira/glossario-seo-geo-ia"
AUTOR = {
    "@type": "Person",
    "@id": "https://raphaelsousapereira.com.br/#raphael",
    "name": "Raphael Sousa Pereira",
    "description": "Profissional, pesquisador e consultor em Generative Engine Optimization (GEO) e IA aplicada à busca, "
                   "CEO e fundador da Negócio no Mapa.",
    "worksFor": {"@type": "Organization", "name": "Negócio no Mapa", "url": SITE},
}
CATEGORIAS = [("seo", "SEO", "Busca orgânica, SEO técnico, local e dados estruturados"),
              ("geo", "GEO", "Visibilidade e citação em motores generativos"),
              ("ia", "IA", "Inteligência artificial aplicada à busca e ao conteúdo")]
CAMPOS = ["slug", "termo_en", "termo_pt", "definicao_pt", "definition_en", "relacionados", "fonte"]
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
URL = re.compile(r"^https?://[^\s|]+$")


def ler() -> tuple[list[dict], list[str]]:
    termos, erros = [], []
    for cat, nome, _ in CATEGORIAS:
        sub = None
        for n, linha in enumerate((TERMOS / f"{cat}.txt").read_text(encoding="utf-8").splitlines(), 1):
            onde = f"termos/{cat}.txt:{n}"
            if linha.startswith("## "):
                sub = linha[3:].strip()
                continue
            if not linha.strip() or linha.startswith("#"):
                continue
            partes = [p.strip() for p in (linha.rstrip() + " ").split(" | ")]
            if len(partes) == 6:
                partes.append("")
            if len(partes) != 7:
                erros.append(f"{onde}: esperava 7 campos, achei {len(partes)}")
                continue
            t = dict(zip(CAMPOS, partes))
            t["relacionados"] = [r.strip() for r in t["relacionados"].split(",") if r.strip()]
            t["categoria"], t["subcategoria"], t["_onde"] = nome, sub, onde
            if not sub:
                erros.append(f"{onde}: termo fora de subcategoria")
            if not SLUG.match(t["slug"]):
                erros.append(f"{onde}: slug inválido {t['slug']!r}")
            for campo in ("termo_en", "termo_pt", "definicao_pt", "definition_en"):
                if not t[campo]:
                    erros.append(f"{onde}: {campo} vazio")
            for campo in ("definicao_pt", "definition_en"):
                if t[campo] and not t[campo].endswith((".", ")")):
                    erros.append(f"{onde}: {campo} deve terminar com ponto")
            if t["fonte"] and not URL.match(t["fonte"]):
                erros.append(f"{onde}: fonte não é URL: {t['fonte']!r}")
            termos.append(t)
    vistos: dict[str, str] = {}
    for t in termos:
        if t["slug"] in vistos:
            erros.append(f"{t['_onde']}: slug repetido {t['slug']!r} (já em {vistos[t['slug']]})")
        vistos.setdefault(t["slug"], t["_onde"])
    for t in termos:
        for r in t["relacionados"]:
            if r == t["slug"]:
                erros.append(f"{t['_onde']}: {r!r} relaciona a si mesmo")
            elif r not in vistos:
                erros.append(f"{t['_onde']}: relacionado inexistente {r!r}")
    return termos, erros


def publico(t: dict) -> dict:
    return {k: t[k] for k in ("slug", "categoria", "subcategoria", "termo_en", "termo_pt",
                              "definicao_pt", "definition_en", "relacionados", "fonte")}


def gerar(termos: list[dict]) -> dict[str, str]:
    ordenados = sorted(termos, key=lambda t: t["termo_pt"].casefold())
    por_slug = {t["slug"]: t for t in termos}
    saida = {}

    meta = {"nome": "Glossário SEO, GEO e IA", "versao": VERSAO, "atualizado_em": DATA, "total": len(termos),
            "idiomas": ["pt-BR", "en"], "licenca": "CC BY 4.0", "autor": AUTOR["name"], "site": SITE, "repositorio": REPO}
    saida["dist/glossario.json"] = json.dumps({"meta": meta, "termos": [publico(t) for t in ordenados]},
                                              ensure_ascii=False, indent=2) + "\n"

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["slug", "categoria", "subcategoria", "termo_en", "termo_pt", "definicao_pt", "definition_en",
                "relacionados", "fonte"])
    for t in ordenados:
        p = publico(t)
        w.writerow([*(p[k] for k in ("slug", "categoria", "subcategoria", "termo_en", "termo_pt",
                                     "definicao_pt", "definition_en")), ";".join(p["relacionados"]), p["fonte"]])
    saida["dist/glossario.csv"] = buf.getvalue()

    set_id = f"{REPO}#glossario"
    termos_ld = []
    for t in ordenados:
        no = {"@type": "DefinedTerm", "@id": f"{REPO}#{t['slug']}", "termCode": t["slug"],
              "name": [{"@language": "pt-BR", "@value": t["termo_pt"]}, {"@language": "en", "@value": t["termo_en"]}],
              "description": [{"@language": "pt-BR", "@value": t["definicao_pt"]},
                              {"@language": "en", "@value": t["definition_en"]}],
              "inDefinedTermSet": {"@id": set_id}}
        if t["fonte"]:
            no["subjectOf"] = t["fonte"]
        termos_ld.append(no)
    ld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "@id": set_id,
          "name": "Glossário SEO, GEO e IA", "inLanguage": ["pt-BR", "en"], "version": VERSAO, "dateModified": DATA,
          "license": "https://creativecommons.org/licenses/by/4.0/", "url": REPO, "author": AUTOR,
          "hasDefinedTerm": termos_ld}
    saida["dist/glossario.jsonld"] = json.dumps(ld, ensure_ascii=False, indent=2) + "\n"

    def bloco(t: dict) -> list[str]:
        linhas = [f'#### {t["termo_pt"]}', "", f'<a id="{t["slug"]}"></a>**EN:** {t["termo_en"]}', "",
                  t["definicao_pt"], "", f'> *{t["definition_en"]}*', ""]
        extra = []
        if t["relacionados"]:
            extra.append("Veja também: " + ", ".join(f'[{por_slug[r]["termo_pt"]}](#{r})' for r in t["relacionados"]))
        if t["fonte"]:
            extra.append(f'Fonte: <{t["fonte"]}>')
        if extra:
            linhas += [" · ".join(extra), ""]
        return linhas

    md = [f"# Glossário SEO, GEO e IA — {len(termos)} termos", "",
          f"Versão {VERSAO} · atualizado em {DATA} · português do Brasil e inglês · "
          f"[CC BY 4.0](LICENSE) · {AUTOR['name']}, [Negócio no Mapa]({SITE})", "",
          "Arquivo gerado por `scripts/construir.py` a partir de `termos/`. Não edite à mão.", ""]
    for cat, nome, desc in CATEGORIAS:
        doCat = [t for t in termos if t["categoria"] == nome]
        md += [f"- [{nome}](#categoria-{cat}) — {desc} ({len(doCat)} termos)"]
    md.append("")
    for cat, nome, desc in CATEGORIAS:
        md += [f'<a id="categoria-{cat}"></a>', f"## {nome} — {desc}", ""]
        subs = list(dict.fromkeys(t["subcategoria"] for t in termos if t["categoria"] == nome))
        for sub in subs:
            grupo = sorted((t for t in termos if t["categoria"] == nome and t["subcategoria"] == sub),
                           key=lambda t: t["termo_pt"].casefold())
            md += [f"### {nome} · {sub}", ""]
            for t in grupo:
                md += bloco(t)
    saida["GLOSSARIO.md"] = "\n".join(md).rstrip() + "\n"

    indice = ["# Índice A–Z", "", f"{len(termos)} termos em ordem alfabética do termo em português.", "",
              "| Termo (pt-BR) | Term (en) | Categoria |", "|---|---|---|"]
    for t in ordenados:
        indice.append(f'| [{t["termo_pt"]}](GLOSSARIO.md#{t["slug"]}) | {t["termo_en"]} | {t["categoria"]} |')
    saida["INDICE.md"] = "\n".join(indice) + "\n"
    return saida


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="não grava; falha se algo estiver inválido ou desatualizado")
    args = ap.parse_args()
    termos, erros = ler()
    if erros:
        print("\n".join(erros), file=sys.stderr)
        print(f"{len(erros)} erro(s).", file=sys.stderr)
        return 1
    saida = gerar(termos)
    desatualizados = []
    for caminho, conteudo in saida.items():
        alvo = RAIZ / caminho
        atual = alvo.read_text(encoding="utf-8") if alvo.exists() else None
        if atual != conteudo:
            desatualizados.append(caminho)
            if not args.check:
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_text(conteudo, encoding="utf-8")
    contagem = {n: sum(t["categoria"] == n for t in termos) for _, n, _ in CATEGORIAS}
    fontes = sum(bool(t["fonte"]) for t in termos)
    print(f"{len(termos)} termos {contagem}, {fontes} com fonte.")
    if args.check and desatualizados:
        print("Desatualizados (rode scripts/construir.py): " + ", ".join(desatualizados), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
