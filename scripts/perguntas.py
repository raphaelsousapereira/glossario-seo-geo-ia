#!/usr/bin/env python3
"""Valida as perguntas em perguntas/*.txt e gera dist/perguntas.json, dist/perguntas-faq.jsonld e PERGUNTAS.md.

    python scripts/perguntas.py            # valida e grava os arquivos gerados
    python scripts/perguntas.py --check    # só confere: falha se algo estiver inválido ou desatualizado

Regras: id único em formato de slug; pergunta terminada em "?"; resposta curta de 60 a 360 caracteres e completa de
200 a 1400; termos relacionados existentes no glossário; fonte obrigatória e já presente no glossário (fonte ou artigo
de algum termo), para que nenhuma resposta cite um endereço inventado; nível iniciante ou avançado.
Somente biblioteca padrão (Python 3.10 ou mais novo).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir as G  # noqa: E402  (mesma versão, autor e termos do glossário)

PERGUNTAS = G.RAIZ / "perguntas"
GRUPOS = [("geo", "GEO", "Perguntas sobre visibilidade e citação em motores generativos")]
CHAVES = {"P": "pergunta", "C": "resposta_curta", "R": "resposta", "T": "relacionados", "F": "fonte", "N": "nivel"}
NIVEIS = {"iniciante", "avancado"}
NOTA_IA = ("Respostas redigidas com assistência de IA a partir das definições do glossário e revisadas por "
           "Raphael Sousa Pereira antes da publicação.")


def ler(termos: list[dict]) -> tuple[list[dict], list[str]]:
    slugs = {t["slug"] for t in termos}
    fontes = {u for t in termos for u in (t.get("fonte"), t.get("artigo")) if u}
    itens, erros, vistos = [], [], set()
    for arquivo, grupo, _ in GRUPOS:
        caminho = PERGUNTAS / f"{arquivo}.txt"
        sub, atual = None, None
        linhas = caminho.read_text(encoding="utf-8").splitlines() + [""]

        def fechar(item, onde):
            if item is None:
                return
            falta = [k for k in CHAVES.values() if not item.get(k)]
            if falta:
                erros.append(f"{onde}: {item['id']}: faltam {', '.join(falta)}")
                return
            p, c, r = item["pergunta"], item["resposta_curta"], item["resposta"]
            if not p.endswith("?"):
                erros.append(f"{onde}: {item['id']}: a pergunta deve terminar com '?'")
            if not 60 <= len(c) <= 360:
                erros.append(f"{onde}: {item['id']}: resposta curta com {len(c)} caracteres (60 a 360)")
            if not 200 <= len(r) <= 1400:
                erros.append(f"{onde}: {item['id']}: resposta completa com {len(r)} caracteres (200 a 1400)")
            for texto in (c, r):
                if not texto.endswith((".", "!", "?", ")")):
                    erros.append(f"{onde}: {item['id']}: resposta sem ponto final")
            rel = [s.strip() for s in item["relacionados"].split(",") if s.strip()]
            for s in rel:
                if s not in slugs:
                    erros.append(f"{onde}: {item['id']}: termo relacionado inexistente: {s}")
            item["relacionados"] = rel
            if item["fonte"] not in fontes:
                erros.append(f"{onde}: {item['id']}: fonte fora do glossário: {item['fonte']}")
            if item["nivel"] not in NIVEIS:
                erros.append(f"{onde}: {item['id']}: nível deve ser iniciante ou avancado")
            itens.append(item)

        inicio = 0
        for n, linha in enumerate(linhas, 1):
            onde = f"perguntas/{arquivo}.txt:{inicio or n}"
            if linha.startswith("? ") or linha.startswith("## ") or not linha.strip():
                if atual is not None and (linha.startswith("? ") or linha.startswith("## ") or n == len(linhas)):
                    fechar(atual, onde)
                    atual = None
            if linha.startswith("## "):
                sub = linha[3:].strip()
            elif linha.startswith("? "):
                pid = linha[2:].strip()
                if not G.SLUG.match(pid):
                    erros.append(f"perguntas/{arquivo}.txt:{n}: id inválido: {pid}")
                if pid in vistos:
                    erros.append(f"perguntas/{arquivo}.txt:{n}: id repetido: {pid}")
                vistos.add(pid)
                atual, inicio = {"id": pid, "grupo": grupo, "subcategoria": sub}, n
            elif linha.startswith("#") or not linha.strip():
                continue
            elif atual is not None and len(linha) > 3 and linha[1:3] == ": " and linha[0] in CHAVES:
                chave = CHAVES[linha[0]]
                if chave in atual:
                    erros.append(f"perguntas/{arquivo}.txt:{n}: {atual['id']}: campo {linha[0]} repetido")
                atual[chave] = linha[3:].strip()
            else:
                erros.append(f"perguntas/{arquivo}.txt:{n}: linha fora do formato")
    return itens, erros


def gerar(itens: list[dict]) -> dict[Path, str]:
    meta = {"nome": "Perguntas do Glossário SEO, GEO e IA", "versao": G.VERSAO, "atualizado_em": G.DATA,
            "total": len(itens), "idioma": "pt-BR", "licenca": "CC BY 4.0", "assistencia_ia": NOTA_IA}
    dados = json.dumps({"meta": meta, "perguntas": itens}, ensure_ascii=False, indent=1) + "\n"
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": "pt-BR",
           "name": meta["nome"], "url": G.REPO + "/blob/main/PERGUNTAS.md", "author": G.AUTOR,
           "license": "https://creativecommons.org/licenses/by/4.0/", "dateModified": G.DATA,
           "mainEntity": [{"@type": "Question", "@id": G.REPO + "/blob/main/PERGUNTAS.md#" + i["id"], "name": i["pergunta"],
                           "acceptedAnswer": {"@type": "Answer", "text": i["resposta_curta"] + " " + i["resposta"]}}
                          for i in itens]}
    md = [f"# Perguntas do Glossário SEO, GEO e IA — {len(itens)} perguntas", "",
          f"Versão {G.VERSAO} · atualizado em {G.DATA} · português do Brasil · [CC BY 4.0](LICENSE) · "
          "Raphael Sousa Pereira", "", NOTA_IA, "",
          "Arquivo gerado por `scripts/perguntas.py` a partir de `perguntas/`. Não edite à mão.", ""]
    sub = None
    for i in itens:
        if i["subcategoria"] != sub:
            sub = i["subcategoria"]
            md += [f"## {sub}", ""]
        rel = ", ".join(f"[{s}](GLOSSARIO.md#{s})" for s in i["relacionados"])
        md += [f'<a id="{i["id"]}"></a>', f"### {i['pergunta']}", "", f"**{i['resposta_curta']}**", "", i["resposta"], "",
               f"Termos: {rel} · Fonte: <{i['fonte']}> · Nível: {i['nivel']}", ""]
    return {G.RAIZ / "dist" / "perguntas.json": dados,
            G.RAIZ / "dist" / "perguntas-faq.jsonld": json.dumps(faq, ensure_ascii=False, indent=1) + "\n",
            G.RAIZ / "PERGUNTAS.md": "\n".join(md).rstrip() + "\n"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="não grava; falha se algo estiver inválido ou desatualizado")
    args = ap.parse_args()
    termos, erros_termos = G.ler()
    if erros_termos:
        print("\n".join(erros_termos), file=sys.stderr)
        return 1
    itens, erros = ler(termos)
    if erros:
        print("\n".join(erros), file=sys.stderr)
        return 1
    saidas = gerar(itens)
    if args.check:
        velhos = [str(p.relative_to(G.RAIZ)) for p, txt in saidas.items()
                  if not p.exists() or p.read_text(encoding="utf-8") != txt]
        if velhos:
            print("Desatualizado (rode python scripts/perguntas.py): " + ", ".join(velhos), file=sys.stderr)
            return 1
    else:
        for p, txt in saidas.items():
            p.write_text(txt, encoding="utf-8")
    print(f"{len(itens)} perguntas válidas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
