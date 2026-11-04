# Demonstrações documentais em dez páginas de GEO

Responsável autoral: Raphael Sousa Pereira. Preparação e verificação assistidas por IA.
Data: 4 de novembro de 2026. Protocolo: RSP-DOC-DEMO-2026-11-04-v1.

## Escopo e resultados

Este material reúne uma coleta pública do site raphaelsousapereira.com.br e exercícios controlados de aplicação de quatro conceitos autorais: GBFA, Retrieval Surface, QF-GEO e Claim-Scope Preservation.

- 26 URLs com resposta HTTP 200 no recorte coletado.
- Três páginas técnicas com a mesma resposta principal no HTML inicial e no HTML devolvido pela inspeção pública.
- Nas três páginas, os três sinais selecionados (resposta, autoria e conceito) estão no texto extraído.
- Dez páginas do piloto com links de ida e volta para a central de perguntas.
- Quatorze trechos de evidência dos exercícios foram localizados literalmente nas fontes preservadas.
- Quatro exercícios com textos redigidos e anotações editoriais assistidas por IA, explícitas. Não são respostas capturadas de provedores de IA.
- Nenhum run de LLM e nenhum teste de efeito causal em ranking, citação ou conversão.

A disponibilidade de uma resposta nesta coleta não demonstra como um provedor específico a recupera. As relações dos mapas de necessidades informacionais foram propostas para auditoria externa; não são observações de consultas internas do Google.

## Arquivos

- `evidencias.json`: URLs, horários UTC, cabeçalhos públicos usados na requisição, status HTTP, hashes, exercícios anotados e capturas históricas do conteúdo principal em tar+gzip+base64.
- `replicar.py`: verifica hashes e reavalia as capturas históricas, sem rede e sem executar o JavaScript dos documentos.
- `coletar.py`: parser e coletor HTTP em Python padrão. Pode fazer uma nova coleta, registrada com sua própria data. A inspeção pública adicional precisa ser coletada separadamente; o coletor HTTP não simula um navegador.

Os arquivos públicos preservam o elemento HTML do conteúdo principal. `sha256` identifica esse recorte; `source_http_sha256` registra o hash da resposta HTTP completa que foi recebida na coleta original. Integridade por hash não comprova a verdade de uma afirmação.

## Reproduzir o recorte histórico

Baixe os três arquivos pelo botão Raw/Download do GitHub, coloque-os na mesma pasta e execute:

```sh
python3 replicar.py
```

O script apenas lê o corpus, confere sua integridade, verifica presença de trechos e recalcula contagens das anotações declaradas. Ele não faz julgamento semântico autônomo, não chama provedores de IA e não certifica precisão geral dos frameworks.

Para uma nova coleta HTTP, em uma cópia de trabalho separada:

```sh
python3 coletar.py
```

Essa execução consulta as URLs atuais e grava arquivos locais. Alterações posteriores das páginas e do HTML podem mudar hashes, textos e contagens. Use a captura histórica para reproduzir o resultado publicado.

## Acompanhar uma intervenção futura

O corpus preserva dez páginas do piloto e dez páginas de comparação, escolhidas por tema. A seleção não foi aleatória. As páginas de comparação não receberam os blocos deste piloto. A coleta serve de linha de base documental; não registra uma linha de base de citações por LLMs. Uma avaliação futura deve declarar provedor, interface/API, modo de busca, localização, histórico, perguntas e repetições antes da coleta e interpretar mudanças sem presumir causalidade.

## Páginas do piloto

- [Como auditar uma marca em GEO?](https://raphaelsousapereira.com.br/perguntas/como-auditar-uma-marca-em-geo/#rsp-demo-1010)
- [Como reduzir alucinações de IA sobre a minha empresa?](https://raphaelsousapereira.com.br/perguntas/como-reduzir-alucinacoes-de-ia-sobre-a-minha-empresa/#rsp-demo-1016)
- [LLMs leem JavaScript?](https://raphaelsousapereira.com.br/perguntas/llms-leem-javascript/#rsp-demo-902)
- [SSR é necessário para GEO?](https://raphaelsousapereira.com.br/perguntas/ssr-e-necessario-para-geo/#rsp-demo-903)
- [Uma descrição em imagem é invisível para a IA?](https://raphaelsousapereira.com.br/perguntas/uma-descricao-em-imagem-e-invisivel-para-a-ia/#rsp-demo-905)
- [Como criar conteúdo que as IAs citam corretamente?](https://raphaelsousapereira.com.br/perguntas/como-criar-conteudo-que-as-ias-citam-corretamente/#rsp-demo-943)
- [O que são perguntas e respostas implícitas?](https://raphaelsousapereira.com.br/perguntas/o-que-sao-perguntas-e-respostas-implicitas/#rsp-demo-946)
- [Como organizar o conteúdo para a IA reconhecer a hierarquia dos temas?](https://raphaelsousapereira.com.br/perguntas/como-organizar-o-conteudo-para-a-ia-reconhecer-a-hierarquia-dos-temas/#rsp-demo-957)
- [O que é query fan-out?](https://raphaelsousapereira.com.br/perguntas/o-que-e-query-fan-out/#rsp-demo-974)
- [Como descobrir o que o ChatGPT diz sobre minha empresa?](https://raphaelsousapereira.com.br/perguntas/como-descobrir-o-que-o-chatgpt-diz-sobre-minha-empresa/#rsp-demo-857)

As definições canônicas permanecem em [termos/autorais.txt](../../termos/autorais.txt) e [GLOSSARIO.md](../../GLOSSARIO.md).
