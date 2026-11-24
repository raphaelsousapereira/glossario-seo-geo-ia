# Especificações

Cada mudança relevante nasce aqui, antes do código (PANDORA GOVERNANÇA, etapa **Declarar**).

- Um arquivo por tema: `specs/AAAA-MM-tema.md`.
- Cada item tem ID estável `SPEC-<ÁREA>-<n>` e um critério de aceite observável.
- O PR cita os IDs que atende. O portão reprova ID citado que não existe aqui.
- ID de outro repositório: `SPEC-GOV-1@pandora-saas-forge`.

## Modelo

```markdown
# SPEC-AREA · título

- **Pedido:** quem pediu e o quê.
- **Memória consultada:** MEMORIA.md@<commit>, IDs.

| ID | Item | Critério de aceite |
|---|---|---|
| **SPEC-AREA-1** | … | … |
```
