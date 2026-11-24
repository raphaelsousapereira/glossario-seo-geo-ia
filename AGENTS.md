## Memória técnica obrigatória da PANDORA

Antes da primeira alteração e antes de publicar, consulte a main de raphaelsousapereira/pandora-memoria-tecnica. Abra AGENTS.md e MEMORIA.md pelo conector GitHub autenticado ou por uma cópia Git atualizada. Busque o sintoma e o componente. Registre no PR ou no histórico de execução o commit consultado, o ID aplicável e o teste que será executado. Ao fechar o trabalho, acrescente a descoberta em MEMORIA.md seguindo MODELO.md, ou explique por que o caso existente continua suficiente. Referencie o commit da atualização. Preserve instruções específicas deste projeto.

<!-- pandora-governanca:inicio -->
## Governança do desenvolvimento (PANDORA GOVERNANÇA)

Toda mudança segue **Declarar → Estruturar → Gerar → Rastrear**. Guia: `docs/GOVERNANCA.md` em
raphaelsousapereira/pandora-saas-forge.

1. **Declarar.** Antes de codar, escreva os itens em `specs/` (`SPEC-<ÁREA>-<n>`, cada um com critério de aceite).
   Mudança trivial: uma linha `Sem spec: <motivo>` no texto do PR. Item de outro repositório: `SPEC-GOV-1@pandora-saas-forge`.
2. **Estruturar.** Dependências permitidas, caminhos proibidos e arquivos gerados estão em `.pandora/arquitetura.json`.
   Dependência nova entra no contrato no mesmo PR, com o motivo no texto do PR.
3. **Gerar.** Escreva o texto do PR em um arquivo e rode
   `python tools/pandora_governanca.py verificar --pr-corpo <arquivo>` até sair `APROVADO`.
4. **Rastrear.** Último commit do PR: `python tools/pandora_governanca.py registrar --pr-corpo <arquivo>`. Ele grava o
   BOM de proveniência em `governanca/bom/` e acrescenta uma linha encadeada por hash em `governanca/registro.jsonl`.
   Nunca edite linhas antigas. Conflito no registro: atualize o ramo com o principal, descarte a sua linha e rode `registrar` de novo.

O texto do PR sempre traz: itens `SPEC-…` atendidos, `Memória: <commit do MEMORIA.md consultado>`, testes executados e
o resultado do portão. A aprovação humana é o review e o merge do PR: nada vai direto para o ramo principal.
Não edite `tools/pandora_governanca.py` aqui; ele é instalado a partir do pandora-saas-forge.
<!-- pandora-governanca:fim -->
