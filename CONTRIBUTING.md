# Como contribuir

Correções e termos novos são bem-vindos por issue ou pull request.

## Formato

Cada termo é uma linha em `termos/<categoria>.txt`, com sete campos separados por ` | `:

```
slug | termo em inglês | termo em português | definição pt-BR | definition (en) | relacionados | fonte
```

- **slug**: identificador em inglês, minúsculo, com hífens (`query-fan-out`). Não mude o slug de um termo
  publicado: ele é a âncora dos links e o `@id` do JSON-LD.
- **definições**: uma ou duas frases que façam sentido sozinhas, terminadas com ponto. Sem `|`.
- **relacionados**: slugs separados por vírgula. O script recusa um slug que não existe.
- **fonte**: URL de fonte primária (documentação oficial, especificação, artigo original). Deixe vazio se não houver.
- Uma linha `## Nome` abre uma subcategoria.

## Critérios

1. Definição factual e verificável; nada de "o melhor" ou "o único".
2. Fato que muda com o tempo leva data ("desde março de 2024").
3. Termo de mercado sem consenso é descrito como tal ("outro nome usado no mercado para...").
4. Rode `python3 scripts/construir.py` e inclua os arquivos gerados no mesmo commit.
