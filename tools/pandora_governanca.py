#!/usr/bin/env python3
"""PANDORA GOVERNANÇA — governança do ciclo de desenvolvimento com IA, em um arquivo, sem dependências.

Declarar → Estruturar → Gerar → Rastrear:

  verificar   portão: contrato de arquitetura, segredos, caminhos proibidos, arquivos gerados, especificação,
              memória técnica e integridade do registro                              (SPEC-GOV-1..4, 6)
  bom         BOM de proveniência do intervalo base..HEAD (JSON)                    (SPEC-GOV-5)
  registrar   grava o BOM em governanca/bom/ e acrescenta linha encadeada por hash    (SPEC-GOV-6)
  registro    confere a cadeia de governanca/registro.jsonl                          (SPEC-GOV-6)
  uso-ia      uso de IA, PRs e commits diretos no ramo principal, por repositório     (SPEC-GOV-7)
  instalar    instala ou atualiza o kit em outro repositório (idempotente)           (SPEC-GOV-8)

Fonte única: pandora-saas-forge/tools/pandora_governanca.py. Nos outros repositórios esta é uma cópia
instalada por `instalar`; não edite a cópia, atualize a fonte e reinstale.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VERSAO = "1.0.0"
CONTRATO = Path(".pandora/arquitetura.json")
REGISTRO = Path("governanca/registro.jsonl")
DIR_BOM = Path("governanca/bom")
GENESE = "0" * 64
IGNORAR = "pandora-governanca: ignorar"

# Padrões montados por partes para que este arquivo não case consigo mesmo.
_PK = "-----BEGIN " + r"(?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY" + "-----"
SEGREDOS = [
    ("chave privada", re.compile(_PK)),
    ("token GitHub", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("chave Anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("chave OpenAI", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}")),
    ("chave AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("token Slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("chave Google", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("chave Render", re.compile(r"\brnd_[A-Za-z0-9]{24,}\b")),
    ("chave Stripe", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}")),
]
SPEC_RE = re.compile(r"\bSPEC-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+(?:\.\d+)*(?:@[\w.\-]+)?")
SEM_SPEC_RE = re.compile(r"^\s*[-*]?\s*Sem spec\s*:\s*(\S.{9,})$", re.I | re.M)
MEMORIA_RE = re.compile(r"Mem[oó]ria[^\n:]*:[^\n]*?\b([0-9a-f]{7,40})\b", re.I)
CAMINHOS_PROIBIDOS_PADRAO = [".env", "*/.env", ".env.*", "*/.env.*", "*.pem", "*.key", "*.p12", "*.pfx",
                             "id_rsa*", "*/id_rsa*", "id_ed25519*", "*/id_ed25519*", "*.sqlite", "*.db"]
EXCECOES_PADRAO = ["*.example", "*.sample", "*.dist"]


# ───────────────────────────── git ─────────────────────────────

def git(*args: str, cwd: Path | None = None, ok: bool = False) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        if ok:
            return ""
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def raiz(cwd: Path | None = None) -> Path:
    return Path(git("rev-parse", "--show-toplevel", cwd=cwd).strip())


def ramo_padrao(cwd: Path | None = None) -> str:
    """Nome do ramo principal do repositório (não presume `main`)."""
    ref = git("symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD", cwd=cwd, ok=True).strip()
    if ref.startswith("origin/"):
        return ref[len("origin/"):]
    saida = git("remote", "show", "origin", cwd=cwd, ok=True)
    m = re.search(r"HEAD branch:\s*(\S+)", saida)
    if m and m.group(1) != "(unknown)":
        return m.group(1)
    return "main"


def resolver_base(base: str | None, cwd: Path) -> str | None:
    candidatos = [base] if base else []
    if os.environ.get("GITHUB_BASE_REF"):
        candidatos.append("origin/" + os.environ["GITHUB_BASE_REF"])
    candidatos += ["origin/HEAD", "origin/" + ramo_padrao(cwd), "origin/main"]
    for c in candidatos:
        if c and git("rev-parse", "--verify", "-q", c + "^{commit}", cwd=cwd, ok=True).strip():
            mb = git("merge-base", c, "HEAD", cwd=cwd, ok=True).strip()
            if mb:
                return mb
    return None


def arquivos_versionados(cwd: Path) -> list[str]:
    return [f for f in git("ls-files", "-z", cwd=cwd).split("\0") if f]


def nao_versionados(cwd: Path) -> list[str]:
    return [f for f in git("ls-files", "-z", "--others", "--exclude-standard", cwd=cwd).split("\0") if f]


def alterados(base: str | None, cwd: Path) -> list[tuple[str, str]]:
    """(estado, caminho) do merge-base até a árvore de trabalho, mais não versionados."""
    out: list[tuple[str, str]] = []
    if base:
        for linha in git("diff", "--name-status", "--no-renames", base, cwd=cwd).splitlines():
            st, _, p = linha.partition("\t")
            out.append((st[:1], p))
    vistos = {p for _, p in out}
    out += [("A", p) for p in nao_versionados(cwd) if p not in vistos]
    return out


def linhas_adicionadas(base: str | None, cwd: Path, tudo: bool) -> list[tuple[str, int, str]]:
    res: list[tuple[str, int, str]] = []
    if tudo or not base:
        arquivos = arquivos_versionados(cwd) + nao_versionados(cwd)
        for p in arquivos:
            for n, t in enumerate(_ler_texto(cwd / p).splitlines(), 1):
                res.append((p, n, t))
        return res
    atual, n = None, 0
    for linha in git("diff", "-U0", "--no-renames", "--no-color", base, cwd=cwd).splitlines():
        if linha.startswith("+++ "):
            atual = linha[6:] if linha.startswith("+++ b/") else None
        elif linha.startswith("@@"):
            m = re.search(r"\+(\d+)", linha)
            n = int(m.group(1)) if m else 0
        elif linha.startswith("+") and atual:
            res.append((atual, n, linha[1:]))
            n += 1
    for p in nao_versionados(cwd):
        for k, t in enumerate(_ler_texto(cwd / p).splitlines(), 1):
            res.append((p, k, t))
    return res


def _ler_texto(p: Path) -> str:
    try:
        if not p.is_file() or p.stat().st_size > 2_000_000:
            return ""
        dados = p.read_bytes()
        if b"\0" in dados[:8192]:
            return ""
        return dados.decode("utf-8", "replace")
    except OSError:
        return ""


def commits(base: str | None, cwd: Path) -> list[dict]:
    if not base:
        return []
    fmt = "%H%x1f%an%x1f%aI%x1f%s%x1f%b%x1e"
    out = []
    for bloco in git("log", f"--format={fmt}", f"{base}..HEAD", cwd=cwd).split("\x1e"):
        bloco = bloco.strip("\n")
        if not bloco:
            continue
        sha, autor, data, titulo, corpo = (bloco.split("\x1f") + [""] * 5)[:5]
        out.append({"sha": sha, "autor": autor, "data": data, "titulo": titulo, "corpo": corpo,
                    **_trailers(corpo, autor)})
    return out


def agente_de(texto: str) -> str | None:
    """Família do agente de IA, sem identificador de modelo."""
    t = texto.lower()
    for chave, nome in (("claude", "Claude"), ("anthropic", "Claude"), ("codex", "Codex"), ("openai", "Codex"),
                        ("chatgpt", "Codex"), ("copilot", "Copilot"), ("cursor", "Cursor"), ("gemini", "Gemini")):
        if chave in t:
            return nome
    return None


def _trailers(corpo: str, autor: str) -> dict:
    sessoes = re.findall(r"^Claude-Session:\s*(\S+)", corpo, re.M)
    coautores = re.findall(r"^Co-Authored-By:\s*(.+?)\s*(?:<[^>]*>)?\s*$", corpo, re.M | re.I)
    agentes = sorted({a for a in (agente_de(c) for c in coautores + [autor]) if a} | ({"Claude"} if sessoes else set()))
    return {"sessoes": sessoes, "agentes": agentes}


# ───────────────────────────── contrato ─────────────────────────────

def norm_py(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _nome_req(linha: str) -> str | None:
    linha = linha.split(" #", 1)[0].strip()
    if not linha or linha.startswith(("#", "-r", "-c", "--", "-e .", "-e ./", ".", "/")):
        return None
    if linha.startswith("-e "):
        linha = linha[3:].strip()
    m = re.search(r"[#&]egg=([A-Za-z0-9][A-Za-z0-9._\-]*)", linha)
    if m:
        return norm_py(m.group(1))
    m = re.match(r"([A-Za-z0-9][A-Za-z0-9._\-]*)", linha)
    if not m or "://" in linha[: m.end() + 3]:
        return None
    return norm_py(m.group(1))


def _toml(texto: str) -> dict:
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(texto)
    except Exception:
        return {}


def dependencias(cwd: Path) -> dict[str, list[str]]:
    """{'py:nome' | 'npm:nome': [arquivos onde aparece]}"""
    achadas: dict[str, set[str]] = {}

    def add(chave: str, origem: str) -> None:
        achadas.setdefault(chave, set()).add(origem)

    for f in arquivos_versionados(cwd):
        if "node_modules/" in f:
            continue
        nome = f.rsplit("/", 1)[-1]
        if re.fullmatch(r"requirements[^/]*\.(?:txt|in)", nome):
            for linha in _ler_texto(cwd / f).splitlines():
                n = _nome_req(linha)
                if n:
                    add("py:" + n, f)
        elif nome == "pyproject.toml":
            d = _toml(_ler_texto(cwd / f))
            proj = d.get("project") or {}
            reqs = list(proj.get("dependencies") or [])
            for grupo in (proj.get("optional-dependencies") or {}).values():
                reqs += list(grupo or [])
            for grupo in (d.get("dependency-groups") or {}).values():
                reqs += [r for r in grupo or [] if isinstance(r, str)]
            reqs += list((d.get("build-system") or {}).get("requires") or [])
            for r in reqs:
                n = _nome_req(r)
                if n:
                    add("py:" + n, f)
        elif nome == "package.json":
            try:
                d = json.loads(_ler_texto(cwd / f) or "{}")
            except json.JSONDecodeError:
                continue
            for sec in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                for n in (d.get(sec) or {}):
                    add("npm:" + n, f)
    return {k: sorted(v) for k, v in sorted(achadas.items())}


def contrato_padrao(cwd: Path, projeto: str) -> dict:
    return {
        "kit": f"pandora-governanca/{VERSAO}",
        "projeto": projeto,
        "ramo_principal": ramo_padrao(cwd),
        "dependencias": {
            "permitidas": sorted(dependencias(cwd)),
            "proibidas": [],
            "_como": "Nova dependência entra aqui no mesmo PR, com o motivo no texto do PR. Prefixos: py: e npm:.",
        },
        "caminhos_proibidos": CAMINHOS_PROIBIDOS_PADRAO,
        "excecoes_caminhos": EXCECOES_PADRAO,
        "segredos_permitidos_em": [],
        "gerados": [],
        "exigir_spec": True,
        "exigir_memoria": True,
    }


def ler_contrato(cwd: Path) -> tuple[dict | None, str]:
    p = cwd / CONTRATO
    if not p.exists():
        return None, f"{CONTRATO} não existe (rode `instalar`)"
    try:
        c = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, f"{CONTRATO} não é JSON válido: {e}"
    if not isinstance(c.get("dependencias", {}).get("permitidas"), list):
        return None, f"{CONTRATO} sem dependencias.permitidas"
    return c, ""


def casa(caminho: str, padroes: list[str]) -> bool:
    nome = caminho.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(caminho, p) or fnmatch.fnmatch(nome, p) for p in padroes)


# ───────────────────────────── texto do PR ─────────────────────────────

def texto_pr(arquivo: str | None) -> tuple[str | None, str]:
    if arquivo:
        return Path(arquivo).read_text(encoding="utf-8"), f"arquivo {arquivo}"
    if os.environ.get("PANDORA_PR_CORPO") and Path(os.environ["PANDORA_PR_CORPO"]).is_file():
        return Path(os.environ["PANDORA_PR_CORPO"]).read_text(encoding="utf-8"), "PANDORA_PR_CORPO"
    ev = os.environ.get("GITHUB_EVENT_PATH")
    if ev and Path(ev).is_file():
        try:
            pr = json.loads(Path(ev).read_text(encoding="utf-8")).get("pull_request")
        except json.JSONDecodeError:
            pr = None
        if pr is not None:
            return (pr.get("title") or "") + "\n\n" + (pr.get("body") or ""), "evento do GitHub"
    return None, ""


def specs_definidas(cwd: Path) -> set[str]:
    ids: set[str] = set()
    pasta = cwd / "specs"
    if pasta.is_dir():
        for p in pasta.rglob("*.md"):
            ids |= {i for i in SPEC_RE.findall(p.read_text(encoding="utf-8", errors="replace")) if "@" not in i}
    return ids


# ───────────────────────────── verificar ─────────────────────────────

class Resultado:
    def __init__(self) -> None:
        self.itens: list[dict] = []

    def add(self, cid: str, nome: str, status: str, detalhes: list[str] | None = None) -> None:
        self.itens.append({"id": cid, "verificacao": nome, "status": status, "detalhes": detalhes or []})

    @property
    def aprovado(self) -> bool:
        return all(i["status"] != "reprovado" for i in self.itens)


def verificar(cwd: Path, base_arg: str | None = None, pr_arquivo: str | None = None, tudo: bool = False) -> tuple[Resultado, dict]:
    r = Resultado()
    base = resolver_base(base_arg, cwd)
    ctx: dict = {"base": base, "head": git("rev-parse", "HEAD", cwd=cwd).strip()}
    contrato, erro = ler_contrato(cwd)
    if contrato is None:
        r.add("G1", "contrato de arquitetura", "reprovado", [erro])
        contrato = contrato_padrao(cwd, cwd.name)
    else:
        r.add("G1", "contrato de arquitetura", "aprovado", [f"{CONTRATO} ({contrato.get('kit', '?')})"])

    # G2 dependências (árvore inteira: o contrato vale sempre)
    perm = set(contrato["dependencias"].get("permitidas") or [])
    proib = set(contrato["dependencias"].get("proibidas") or [])
    probs = []
    for dep, onde in dependencias(cwd).items():
        if dep in proib:
            probs.append(f"{dep} é proibida pelo contrato ({', '.join(onde)})")
        elif dep not in perm:
            probs.append(f"{dep} não está em dependencias.permitidas ({', '.join(onde)})")
    r.add("G2", "dependências dentro do contrato", "reprovado" if probs else "aprovado", probs)

    mudados = alterados(base, cwd)
    ctx["arquivos"] = mudados
    # G3 caminhos proibidos
    alvo = [p for st, p in mudados if st != "D"] if not tudo else arquivos_versionados(cwd)
    ruins = [p for p in alvo if casa(p, contrato.get("caminhos_proibidos") or [])
             and not casa(p, contrato.get("excecoes_caminhos") or [])]
    r.add("G3", "caminhos proibidos", "reprovado" if ruins else "aprovado", [f"{p} casa com caminhos_proibidos" for p in ruins])

    # G4 segredos nas linhas adicionadas
    livres = contrato.get("segredos_permitidos_em") or []
    achados = []
    for arq, n, linha in linhas_adicionadas(base, cwd, tudo):
        if IGNORAR in linha or casa(arq, livres):
            continue
        for nome, rx in SEGREDOS:
            if rx.search(linha):
                achados.append(f"{arq}:{n}: possível {nome}")
                break
    r.add("G4", "segredos em linhas adicionadas", "reprovado" if achados else "aprovado", achados[:50])

    # G5 arquivos gerados
    mud = {p for _, p in mudados}
    gprob = []
    for g in contrato.get("gerados") or []:
        if g.get("arquivo") in mud and not any(any(m == f or m.startswith(f.rstrip("/") + "/") for f in g.get("fontes") or []) for m in mud):
            gprob.append(f"{g['arquivo']} mudou sem mudança nas fontes {g.get('fontes')}; {g.get('regenerar', 'regenere a partir da fonte')}")
    r.add("G5", "arquivos gerados só a partir da fonte", "reprovado" if gprob else "aprovado", gprob)

    # G6 especificação e memória (texto do PR + mensagens de commit)
    corpo, fonte = texto_pr(pr_arquivo)
    cs = commits(base, cwd)
    ctx["commits"] = cs
    texto = (corpo or "") + "\n" + "\n".join(c["titulo"] + "\n" + c["corpo"] for c in cs)
    refs = sorted(set(SPEC_RE.findall(texto)))
    sem_spec = SEM_SPEC_RE.search(texto)
    memoria = MEMORIA_RE.search(texto)
    ctx.update({"specs": refs, "sem_spec": sem_spec.group(1).strip() if sem_spec else None,
                "memoria": memoria.group(1) if memoria else None, "fonte_pr": fonte})
    em_pr = corpo is not None
    det, falhou = [], False
    if contrato.get("exigir_spec", True):
        definidas = specs_definidas(cwd)
        faltam = [i for i in refs if "@" not in i and i not in definidas]
        if faltam:
            falhou = True
            det.append("itens citados que não existem em specs/: " + ", ".join(faltam))
        if refs:
            det.append("itens: " + ", ".join(refs))
        elif sem_spec:
            det.append("sem spec: " + sem_spec.group(1).strip())
        else:
            det.append("nenhum SPEC-… nem `Sem spec: <motivo>` no texto do PR ou nos commits")
            falhou = falhou or em_pr
    if contrato.get("exigir_memoria", True):
        if memoria:
            det.append("memória consultada: " + memoria.group(1))
        else:
            det.append("falta `Memória: <commit do MEMORIA.md consultado>` no texto do PR ou nos commits")
            falhou = falhou or em_pr
    if falhou:
        st = "reprovado"
    elif em_pr or (refs or sem_spec) and (memoria or not contrato.get("exigir_memoria", True)):
        st = "aprovado"
    else:
        st = "aviso"
        det.append("sem texto de PR (use --pr-corpo ARQUIVO): no PR esta verificação reprova")
    r.add("G6", "especificação e memória técnica", st, det)

    # G7 registro
    ok, msgs = verificar_registro(cwd)
    r.add("G7", "registro encadeado", "aprovado" if ok else "reprovado", msgs)
    ctx["contrato"] = contrato
    return r, ctx


def imprimir(r: Resultado, ctx: dict, como_json: bool) -> None:
    if como_json:
        print(json.dumps({"aprovado": r.aprovado, "base": ctx.get("base"), "head": ctx.get("head"), "itens": r.itens},
                         ensure_ascii=False, indent=2))
        return
    simb = {"aprovado": "✔", "reprovado": "✘", "aviso": "!"}
    print(f"PANDORA GOVERNANÇA {VERSAO} · base {(ctx.get('base') or 'nenhuma')[:12]} · head {ctx['head'][:12]}")
    for i in r.itens:
        print(f"  {simb[i['status']]} {i['id']} {i['verificacao']}: {i['status']}")
        for d in i["detalhes"]:
            print(f"      - {d}")
    print("RESULTADO: " + ("APROVADO" if r.aprovado else "REPROVADO"))


# ───────────────────────────── BOM e registro ─────────────────────────────

def sha256_arquivo(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def gerar_bom(cwd: Path, base_arg: str | None, pr_arquivo: str | None) -> dict:
    r, ctx = verificar(cwd, base_arg, pr_arquivo)
    cs = ctx["commits"]
    sessoes = sorted({s for c in cs for s in c["sessoes"]})
    agentes = sorted({a for c in cs for a in c["agentes"]})
    return {
        "formato": "pandora-bom/1",
        "kit": VERSAO,
        "projeto": ctx["contrato"].get("projeto") or cwd.name,
        "gerado_em": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "base": ctx["base"],
        "head": ctx["head"],
        "commits": [{"sha": c["sha"], "autor": c["autor"], "data": c["data"], "titulo": c["titulo"],
                     "agentes_ia": c["agentes"], "sessoes": c["sessoes"]} for c in cs],
        "ia": {"agentes": agentes, "sessoes": sessoes,
               "commits_com_ia": sum(1 for c in cs if c["agentes"]), "commits": len(cs)},
        "arquivos": [{"caminho": p, "estado": st, "sha256": None if st == "D" else sha256_arquivo(cwd / p)}
                     for st, p in sorted(ctx["arquivos"], key=lambda x: x[1])
                     if not p.startswith(str(DIR_BOM) + "/") and p != str(REGISTRO)],
        "especificacao": {"itens": ctx["specs"], "sem_spec": ctx["sem_spec"]},
        "memoria": {"commit": ctx["memoria"]},
        "portao": {"aprovado": r.aprovado, "itens": [{k: i[k] for k in ("id", "status")} for i in r.itens]},
        "aprovacao_humana": {"tipo": "pull_request", "estado": "pendente",
                             "nota": "A aprovação humana é o review e o merge deste PR no GitHub."},
    }


def _canon(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def ler_registro(cwd: Path) -> list[dict]:
    p = cwd / REGISTRO
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def verificar_registro(cwd: Path) -> tuple[bool, list[str]]:
    p = cwd / REGISTRO
    if not p.exists():
        return True, ["registro ainda vazio"]
    anterior, msgs = GENESE, []
    try:
        linhas = ler_registro(cwd)
    except json.JSONDecodeError as e:
        return False, [f"linha inválida em {REGISTRO}: {e}"]
    for i, e in enumerate(linhas, 1):
        corpo = {k: v for k, v in e.items() if k != "hash"}
        if e.get("seq") != i:
            msgs.append(f"linha {i}: seq {e.get('seq')} fora de ordem")
        if e.get("anterior") != anterior:
            msgs.append(f"linha {i}: elo quebrado (anterior não confere)")
        if hashlib.sha256(_canon(corpo)).hexdigest() != e.get("hash"):
            msgs.append(f"linha {i}: hash não confere (linha alterada)")
        bom = cwd / e.get("bom", "")
        if e.get("bom") and sha256_arquivo(bom) != e.get("bom_sha256"):
            msgs.append(f"linha {i}: {e.get('bom')} ausente ou alterado")
        anterior = e.get("hash", "")
    return (not msgs), (msgs or [f"{len(linhas)} entrada(s) íntegras"])


def registrar(cwd: Path, base_arg: str | None, pr_arquivo: str | None) -> dict:
    ok, msgs = verificar_registro(cwd)
    if not ok:
        raise SystemExit("registro com problema, nada foi acrescentado:\n  " + "\n  ".join(msgs))
    bom = gerar_bom(cwd, base_arg, pr_arquivo)
    destino = cwd / DIR_BOM / f"{bom['head'][:12]}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(bom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    linhas = ler_registro(cwd)
    e = {"seq": len(linhas) + 1, "quando": bom["gerado_em"], "projeto": bom["projeto"], "base": bom["base"],
         "head": bom["head"], "itens": bom["especificacao"]["itens"], "memoria": bom["memoria"]["commit"],
         "portao_aprovado": bom["portao"]["aprovado"], "bom": destino.relative_to(cwd).as_posix(),
         "bom_sha256": sha256_arquivo(destino), "anterior": linhas[-1]["hash"] if linhas else GENESE}
    e["hash"] = hashlib.sha256(_canon(e)).hexdigest()
    (cwd / REGISTRO).parent.mkdir(parents=True, exist_ok=True)
    with open(cwd / REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    return e


# ───────────────────────────── uso de IA ─────────────────────────────

def uso_ia(repo: Path, dias: int) -> dict:
    ramo = ramo_padrao(repo)
    ref = f"origin/{ramo}" if git("rev-parse", "-q", "--verify", f"origin/{ramo}", cwd=repo, ok=True).strip() else "HEAD"
    desde = f"--since={dias}.days.ago"
    total = ia = mais = menos = mais_ia = 0
    sessoes: set[str] = set()
    agentes: dict[str, int] = {}
    log = git("log", ref, desde, "--no-merges", "--format=%x1e%H%x1f%an%x1f%b%x1f", "--numstat", cwd=repo, ok=True)
    for bloco in log.split("\x1e"):
        partes = bloco.split("\x1f")
        if len(partes) < 4:
            continue
        _sha, autor, corpo, stats = partes[:4]
        tr = _trailers(corpo, autor)
        add = rem = 0
        for m in re.finditer(r"^(\d+)\t(\d+)\t", stats, re.M):
            add += int(m.group(1))
            rem += int(m.group(2))
        total += 1
        mais += add
        menos += rem
        sessoes |= set(tr["sessoes"])
        if tr["agentes"]:
            ia += 1
            mais_ia += add
            for a in tr["agentes"]:
                agentes[a] = agentes.get(a, 0) + 1
    principal = git("log", ref, desde, "--first-parent", "--format=%P%x1f%s", cwd=repo, ok=True).splitlines()
    prs = diretos = 0
    for l in principal:
        pais, _, titulo = l.partition("\x1f")
        if len(pais.split()) > 1 or re.search(r"\(#\d+\)\s*$", titulo) or titulo.startswith("Merge pull request #"):
            prs += 1
        else:
            diretos += 1
    return {"repositorio": repo.name, "ramo": ramo, "dias": dias, "commits": total, "commits_com_ia": ia,
            "agentes": agentes, "sessoes": len(sessoes), "linhas_adicionadas": mais, "linhas_removidas": menos,
            "linhas_adicionadas_com_ia": mais_ia, "entradas_por_pr": prs, "commits_diretos_no_principal": diretos}


def imprimir_uso(linhas: list[dict], como_json: bool) -> None:
    if como_json:
        print(json.dumps(linhas, ensure_ascii=False, indent=2))
        return
    dias = linhas[0]["dias"] if linhas else 0
    print(f"## Uso de IA e disciplina de PR — últimos {dias} dias\n")
    print("| Repositório | Ramo | Commits | Com IA | % IA | Sessões | Linhas + (IA) | Entradas por PR | Commits diretos |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for d in linhas:
        pct = f"{100 * d['commits_com_ia'] / d['commits']:.0f}%" if d["commits"] else "—"
        print(f"| {d['repositorio']} | {d['ramo']} | {d['commits']} | {d['commits_com_ia']} | {pct} | {d['sessoes']} | "
              f"{d['linhas_adicionadas']} ({d['linhas_adicionadas_com_ia']}) | {d['entradas_por_pr']} | {d['commits_diretos_no_principal']} |")
    print("\n`Com IA`: commit com `Claude-Session` ou coautor/autor de agente conhecido. Commits de agentes que não"
          " deixam marca (ex.: Codex sem coautor) contam como humanos. `Commits diretos`: entradas no ramo principal"
          " que não são merge nem squash `(#n)` de PR.")


# ───────────────────────────── instalar ─────────────────────────────

MARCA_INI = "<!-- pandora-governanca:inicio -->"
MARCA_FIM = "<!-- pandora-governanca:fim -->"
MEMORIA_BLOCO = """## Memória técnica obrigatória da PANDORA

Antes da primeira alteração e antes de publicar, consulte a main de raphaelsousapereira/pandora-memoria-tecnica. Abra AGENTS.md e MEMORIA.md pelo conector GitHub autenticado ou por uma cópia Git atualizada. Busque o sintoma e o componente. Registre no PR ou no histórico de execução o commit consultado, o ID aplicável e o teste que será executado. Ao fechar o trabalho, acrescente a descoberta em MEMORIA.md seguindo MODELO.md, ou explique por que o caso existente continua suficiente. Referencie o commit da atualização. Preserve instruções específicas deste projeto.
"""
GOV_BLOCO = MARCA_INI + """
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
""" + MARCA_FIM + "\n"
PR_MODELO = MARCA_INI + """
## O que muda


## Especificação
- Itens: SPEC-…  <!-- ou: Sem spec: <motivo com pelo menos 10 caracteres> -->

## Memória técnica
Memória: MEMORIA.md@<commit> · IDs aplicáveis: … · primeiro teste: …

## Verificação
- [ ] `python tools/pandora_governanca.py verificar --pr-corpo <arquivo>` → APROVADO
- [ ] Testes do projeto (ex.: `python tools/ci_local.py`) → resultado:
- [ ] `registrar` executado no último commit

## Uso de IA
Agente e sessão ficam nos trailers dos commits (`Claude-Session`, `Co-Authored-By`).
""" + MARCA_FIM + "\n"
SPECS_README = """# Especificações

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
"""


def _workflow(ramo: str) -> str:
    return f"""# Gerado por PANDORA GOVERNANÇA {VERSAO} (`python tools/pandora_governanca.py instalar`). Não edite à mão.
# Os passos não usam expressões do GitHub: rodam iguais aqui e no tools/ci_local.py.
name: PANDORA GOVERNANÇA

on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
  push:
    branches: [{ramo}]

permissions:
  contents: read

jobs:
  governanca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Portão de governança
        run: python tools/pandora_governanca.py verificar
      - name: Registro encadeado
        run: python tools/pandora_governanca.py registro
"""


def _escrever(p: Path, conteudo: str, acoes: list[str], checar: bool, rot: str) -> None:
    atual = p.read_text(encoding="utf-8") if p.exists() else None
    if atual == conteudo:
        return
    acoes.append(f"{'criar' if atual is None else 'atualizar'} {rot}")
    if not checar:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")


def _bloco(texto: str, bloco: str) -> str:
    if MARCA_INI in texto and MARCA_FIM in texto:
        ini = texto.index(MARCA_INI)
        fim = texto.index(MARCA_FIM) + len(MARCA_FIM)
        if texto[fim:fim + 1] == "\n":
            fim += 1
        return texto[:ini] + bloco + texto[fim:]
    return texto.rstrip("\n") + ("\n\n" if texto.strip() else "") + bloco


def instalar(dest: Path, projeto: str | None = None, sem_memoria: bool = False, checar: bool = False) -> list[str]:
    dest = raiz(dest)
    acoes: list[str] = []
    fonte = Path(__file__).resolve()
    kit = dest / "tools/pandora_governanca.py"
    if kit.resolve() != fonte:
        _escrever(kit, fonte.read_text(encoding="utf-8"), acoes, checar, "tools/pandora_governanca.py")

    ctr = dest / CONTRATO
    if ctr.exists():
        c = json.loads(ctr.read_text(encoding="utf-8"))
        if c.get("kit") != f"pandora-governanca/{VERSAO}":
            c["kit"] = f"pandora-governanca/{VERSAO}"
            _escrever(ctr, json.dumps(c, ensure_ascii=False, indent=2) + "\n", acoes, checar, str(CONTRATO))
    else:
        c = contrato_padrao(dest, projeto or dest.name)
        _escrever(ctr, json.dumps(c, ensure_ascii=False, indent=2) + "\n", acoes, checar, str(CONTRATO))

    _escrever(dest / ".github/workflows/governanca.yml", _workflow(c.get("ramo_principal") or ramo_padrao(dest)),
              acoes, checar, ".github/workflows/governanca.yml")
    if not (dest / "specs/README.md").exists():
        _escrever(dest / "specs/README.md", SPECS_README, acoes, checar, "specs/README.md")

    tpl = dest / ".github/pull_request_template.md"
    atual = tpl.read_text(encoding="utf-8") if tpl.exists() else ""
    _escrever(tpl, _bloco(atual, PR_MODELO), acoes, checar, ".github/pull_request_template.md")

    ag = dest / "AGENTS.md"
    texto = ag.read_text(encoding="utf-8") if ag.exists() else ""
    if not sem_memoria and "Memória técnica obrigatória" not in texto and "Regra de trabalho PANDORA" not in texto:
        texto = texto.rstrip("\n") + ("\n\n" if texto.strip() else "") + MEMORIA_BLOCO
    _escrever(ag, _bloco(texto, GOV_BLOCO), acoes, checar, "AGENTS.md")

    cl = dest / "CLAUDE.md"
    texto = cl.read_text(encoding="utf-8") if cl.exists() else ""
    if not re.search(r"^@AGENTS\.md\s*$", texto, re.M):
        _escrever(cl, "@AGENTS.md\n" + ("\n" + texto if texto.strip() else ""), acoes, checar, "CLAUDE.md")
    return acoes


# ───────────────────────────── CLI ─────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pandora_governanca", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("verificar", "bom", "registrar"):
        s = sub.add_parser(nome)
        s.add_argument("--base", help="ref base (padrão: ramo principal do origin)")
        s.add_argument("--pr-corpo", help="arquivo com título e texto do PR")
        if nome == "verificar":
            s.add_argument("--tudo", action="store_true", help="procura segredos e caminhos em todo o repositório")
            s.add_argument("--json", action="store_true")
        if nome == "bom":
            s.add_argument("--saida", help="arquivo de saída (padrão: stdout)")
    sub.add_parser("registro")
    s = sub.add_parser("uso-ia")
    s.add_argument("repos", nargs="*", default=["."])
    s.add_argument("--dias", type=int, default=30)
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("instalar")
    s.add_argument("destino")
    s.add_argument("--projeto")
    s.add_argument("--sem-memoria", action="store_true", help="não acrescenta o bloco da memória técnica ao AGENTS.md")
    s.add_argument("--checar", action="store_true", help="só mostra o que mudaria; sai 1 se houver divergência")
    sub.add_parser("versao")
    a = ap.parse_args(argv)

    if a.cmd == "versao":
        print(VERSAO)
        return 0
    if a.cmd == "instalar":
        acoes = instalar(Path(a.destino), a.projeto, a.sem_memoria, a.checar)
        print("\n".join(acoes) if acoes else "nada a mudar")
        return 1 if (a.checar and acoes) else 0
    if a.cmd == "uso-ia":
        imprimir_uso([uso_ia(raiz(Path(r)), a.dias) for r in a.repos], a.json)
        return 0
    cwd = raiz()
    if a.cmd == "verificar":
        r, ctx = verificar(cwd, a.base, a.pr_corpo, a.tudo)
        imprimir(r, ctx, a.json)
        return 0 if r.aprovado else 1
    if a.cmd == "bom":
        texto = json.dumps(gerar_bom(cwd, a.base, a.pr_corpo), ensure_ascii=False, indent=2) + "\n"
        if a.saida:
            Path(a.saida).write_text(texto, encoding="utf-8")
        else:
            sys.stdout.write(texto)
        return 0
    if a.cmd == "registrar":
        e = registrar(cwd, a.base, a.pr_corpo)
        print(f"registro #{e['seq']} {e['hash'][:16]} → {e['bom']} (portão {'aprovado' if e['portao_aprovado'] else 'REPROVADO'})")
        return 0 if e["portao_aprovado"] else 1
    if a.cmd == "registro":
        ok, msgs = verificar_registro(cwd)
        print(("✔ " if ok else "✘ ") + "\n  ".join(msgs))
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
