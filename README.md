# Glossário SEO, GEO e IA

**351 termos de SEO, GEO (Generative Engine Optimization) e inteligência artificial, em português do Brasil e
inglês, com definição nos dois idiomas, termos relacionados e fonte primária quando existe.**

Mantido por Raphael Sousa Pereira, profissional, pesquisador e consultor em Generative Engine Optimization (GEO) e IA
aplicada à busca, CEO e fundador da [Negócio no Mapa](https://seonegocionomapa.com.br).

| Ler | Usar em código ou planilha |
|---|---|
| [GLOSSARIO.md](GLOSSARIO.md): todos os termos por categoria | [dist/glossario.json](dist/glossario.json) |
| [INDICE.md](INDICE.md): índice A–Z | [dist/glossario.csv](dist/glossario.csv) |
| | [dist/glossario.jsonld](dist/glossario.jsonld): Schema.org `DefinedTermSet` |

## O que tem

| Categoria | Termos | Subcategorias |
|---|---|---|
| SEO | 132 | Fundamentos, rastreamento e indexação, técnico e desempenho, conteúdo, links, local, internacional, dados estruturados, métricas, qualidade |
| GEO | 102 | Fundamentos, citação e visibilidade, entidade e grafo, conteúdo citável, acesso das IAs, medição, resultado de negócio, riscos, agentes e comércio |
| IA | 117 | Fundamentos, modelos de linguagem, treinamento, inferência, prompts, RAG e busca semântica, agentes, avaliação, segurança e governança |

Cada termo tem:

- **termo em português e em inglês**: o nome que o mercado usa e a tradução;
- **definição em português e em inglês**, curta o bastante para ser citada sozinha;
- **termos relacionados**, ligados entre si (o script recusa um link para um termo que não existe);
- **fonte primária** em 97 termos: documentação do Google Search Central, RFCs, Schema.org, W3C e os artigos
  originais (GEO, RAG, Transformer, RLHF, LoRA e outros). Todas as URLs foram abertas e responderam em 23/10/2026.
  Quando não há fonte primária estável, o campo fica vazio em vez de apontar para um blog.

Exemplo, em [GLOSSARIO.md](GLOSSARIO.md#query-fan-out):

> **Desdobramento da consulta** (EN: Query Fan-out): técnica em que o sistema de IA divide a pergunta do usuário
> em várias subconsultas, busca cada uma e junta os resultados na resposta. Uma página pode ser citada por responder
> uma subconsulta que o usuário nem digitou.

## Como usar

```bash
curl -s https://raw.githubusercontent.com/raphaelsousapereira/glossario-seo-geo-ia/main/dist/glossario.json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['meta']['total'], 'termos')"
```

O `dist/glossario.jsonld` pode ir direto numa página de glossário, dentro de `<script type="application/ld+json">`.
Cada termo é um `DefinedTerm` com `@id` próprio, nome e descrição nos dois idiomas.

## Como contribuir

Os termos ficam em `termos/seo.txt`, `termos/geo.txt` e `termos/ia.txt`, um por linha. Veja
[CONTRIBUTING.md](CONTRIBUTING.md). Depois de editar:

```bash
python3 scripts/construir.py          # valida e gera GLOSSARIO.md, INDICE.md e dist/
python3 scripts/construir.py --check  # o que o CI roda
```

A página do site sai do mesmo JSON: `python3 scripts/pagina_wordpress.py` grava `dist/pagina-wordpress.html`,
pronta para um bloco "HTML personalizado" do WordPress (CSS próprio, JSON-LD e busca por termo).

## Licença e citação

O conteúdo está sob [CC BY 4.0](LICENSE): pode copiar, traduzir e adaptar, inclusive para uso comercial, desde que
cite a fonte. Exemplo: *Glossário SEO, GEO e IA, Raphael Sousa Pereira, Negócio no Mapa,
github.com/raphaelsousapereira/glossario-seo-geo-ia*. O script em `scripts/` está sob a licença MIT. Para citar em
trabalhos acadêmicos, use [CITATION.cff](CITATION.cff).
