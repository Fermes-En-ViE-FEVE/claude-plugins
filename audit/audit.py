#!/usr/bin/env python3
"""Audit periodique de wording sur des pages publiques Feve.

Pensé pour tourner sans humain dans la boucle (cron GitHub Actions), par opposition
au skill `check-wording` qui est interactif. Pour chaque page de `pages.json` :

  1. recupere le HTML public de l'URL ;
  2. reutilise `check-fr.py` (du plugin check-wording) pour la couche OBJECTIVE :
     orthographe (LanguageTool), typographie francaise, comptage tu/vous ;
  3. fait juger le TON par un LLM (via OpenRouter) avec la charte ton-de-voix-feve.md
     comme bareme + le registre attendu pour cette page ;
  4. compare au run precedent (delta) pour ne mettre en avant que les nouveautes ;
  5. poste un rapport priorise sur Slack (ou l'imprime en --dry-run).

Variables d'environnement :
  OPENROUTER_API_KEY   token OpenRouter (obligatoire pour la couche ton)
  OPENROUTER_MODEL     slug du modele OpenRouter (defaut: anthropic/claude-opus-4.8)
  SLACK_WEBHOOK_URL    webhook Slack (si absent, le rapport est imprime sur stdout)
  LANGUAGETOOL_URL     endpoint LanguageTool (defaut: api publique ; en CI = self-host)

Usage :
  python3 audit/audit.py                       # run complet, poste sur Slack
  python3 audit/audit.py --dry-run             # n'appelle pas Slack, imprime le rapport
  python3 audit/audit.py --state-dir audit/.state   # active le delta (run vs run)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN = REPO_ROOT / "plugins" / "check-wording" / "skills" / "check-wording"
CHARTE_PATH = PLUGIN / "references" / "ton-de-voix-feve.md"
CHECKFR_PATH = PLUGIN / "scripts" / "check-fr.py"
PAGES_PATH = Path(__file__).resolve().parent / "pages.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"


def load_dotenv() -> None:
    """Charge un .env.local (gitignore) pour le confort en local.

    Ne touche jamais a une variable deja definie : en CI, les vrais secrets
    (env GitHub Actions) ont donc toujours la priorite.
    """
    for candidate in (REPO_ROOT / ".env.local", Path(__file__).resolve().parent / ".env.local"):
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def load_checkfr():
    """Charge check-fr.py comme module (le tiret du nom empeche un import classique)."""
    spec = importlib.util.spec_from_file_location("check_fr", CHECKFR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Bascule LanguageTool sur l'instance self-hostee en CI si fournie.
    lt = os.environ.get("LANGUAGETOOL_URL")
    if lt:
        mod.LANGUAGETOOL_API = lt
    return mod


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "feve-audit-wording/0.1 (+https://feve.co)"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, errors="replace")


# --- Couche TON : le juge LLM via OpenRouter ----------------------------------
def parse_findings(content: str) -> list[dict]:
    """Parse defensivement la reponse du LLM (tolere les fences ``` et le texte autour)."""
    s = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    candidates = [s]
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        candidates.append(m.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return data.get("findings", []) if isinstance(data, dict) else []
    return [{"severite": "info", "type": "erreur",
             "probleme": "Reponse IA non parsable", "extrait": content[:200],
             "suggestion": ""}]


def _openrouter_post(body: bytes, headers: dict, attempts: int = 3) -> dict:
    """POST avec retry/backoff sur 429 (rate-limit), utile pour un cron."""
    last_err = None
    for i in range(attempts):
        req = urllib.request.Request(OPENROUTER_URL, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and i < attempts - 1:
                retry_after = e.headers.get("Retry-After")
                wait = int(retry_after) if (retry_after and str(retry_after).isdigit()) else (2 ** i) * 3
                time.sleep(min(wait, 30))
                continue
            raise
    raise last_err  # pragma: no cover


def judge_ton(charte: str, registre: str, texte: str, model: str, api_key: str) -> list[dict]:
    system = (
        charte
        + "\n\n---\n"
        + f"Registre attendu sur cette page : {registre}.\n"
        + "Tu es relecteur editorial Feve. Analyse le texte ci-dessous selon la charte.\n"
        + "Ne traite PAS l'orthographe ni la typographie (couvertes ailleurs).\n"
        + "Concentre-toi sur : coherence du registre (tu/vous), ton, vocabulaire a bannir,\n"
        + "preuve > promesse, phrases trop longues.\n"
        + "Ignore les faux positifs sur FEVE/Feve et les noms de produits Feve.\n"
        + "Reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, de la forme :\n"
        + '{"findings":[{"severite":"haute|moyenne|basse","type":"registre|ton|vocabulaire|preuve|longueur","extrait":"...","probleme":"...","suggestion":"..."}]}\n'
        + "0 a 6 findings, les plus impactants d'abord. Liste vide si tout est bon."
    )
    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        # Plafond indispensable : sinon OpenRouter reserve le cout MAX possible de la
        # sortie (enorme sur les gros modeles) et refuse en 402 si le solde est juste.
        # 1500 tokens suffisent largement pour ~6 findings en JSON.
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": texte[:16000]},
        ],
    }).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "feve-audit-wording",
    }
    payload = _openrouter_post(body, headers)
    content = payload["choices"][0]["message"]["content"]
    return parse_findings(content)


# --- Filtrage des faux positifs (cf. charte §8) -------------------------------
# La marque s'ecrit FEVE/Feve sans accent : LanguageTool veut "fève/fête/rêve",
# c'est un faux positif systematique. On le retire ici (la couche objective ne le
# faisait pas, c'etait le job de Claude dans le skill interactif).
BRAND_TOKENS = {"feve"}


def filter_ortho(matches: list[dict]) -> list[dict]:
    kept = []
    for o in matches:
        token = (o.get("context_match") or "").strip().lower()
        if token in BRAND_TOKENS:
            continue
        kept.append(o)
    return kept


# --- Audit d'une page ---------------------------------------------------------
def audit_page(page: dict, cf, charte: str, model: str, api_key: str) -> dict:
    url = page["url"]
    registre_attendu = page.get("registre", "tu")
    out = {"label": page.get("label", url), "url": url, "registre_attendu": registre_attendu}

    try:
        html_src = fetch(url)
    except Exception as e:  # noqa: BLE001 — on isole l'echec d'une page sans tuer le run
        out["error"] = f"fetch: {e}"
        return out

    texte = cf.extract_text(html_src, True)
    out["chars"] = len(texte)
    out["registre"] = cf.check_registre(texte)
    out["typographie"] = cf.check_typography(texte)

    try:
        out["orthographe"] = filter_ortho(cf.check_orthographe(texte))
    except (Exception, SystemExit) as e:  # check-fr leve SystemExit si LT injoignable
        out["orthographe"] = []
        out["orthographe_error"] = str(e)

    if api_key:
        try:
            out["ton"] = judge_ton(charte, registre_attendu, texte, model, api_key)
        except Exception as e:  # noqa: BLE001
            out["ton"] = []
            out["ton_error"] = str(e)
    else:
        out["ton"] = []
        out["ton_error"] = "OPENROUTER_API_KEY absent"
    return out


# --- Delta (run vs run) -------------------------------------------------------
def finding_keys(page: dict) -> set[str]:
    """Cle stable par finding pour reperer les nouveautes d'un run a l'autre."""
    keys: set[str] = set()
    url = page["url"]
    reg = page.get("registre", {})
    if reg.get("mixte"):
        keys.add(f"{url}|registre|mixte")
    for o in page.get("orthographe", []):
        keys.add(f"{url}|ortho|{o.get('rule')}|{o.get('context_match')}")
    for t in page.get("typographie", []):
        keys.add(f"{url}|typo|{t.get('message')}|{t.get('match')}")
    for f in page.get("ton", []):
        keys.add(f"{url}|ton|{f.get('type')}|{(f.get('extrait') or '')[:60]}")
    return keys


# --- Rendu Slack --------------------------------------------------------------
def fmt_registre(page: dict) -> str:
    reg = page.get("registre", {})
    tu, vous = reg.get("tutoiement_count", 0), reg.get("vouvoiement_count", 0)
    attendu = page.get("registre_attendu", "tu")
    flags = []
    if reg.get("mixte"):
        flags.append("⚠️ mixte")
    if attendu == "tu" and vous > tu and vous > 0:
        flags.append(f"❗ vous domine (attendu {attendu})")
    if attendu == "vous" and tu > vous and tu > 0:
        flags.append(f"❗ tu domine (attendu {attendu})")
    suffix = (" · " + ", ".join(flags)) if flags else ""
    return f"registre tu={tu}/vous={vous}{suffix}"


def render_slack(pages: list[dict], new_keys: set[str], when: str, model: str) -> str:
    total_new = len(new_keys)
    lines = [f"*Audit wording — {when}*  _(modele: {model})_"]
    if new_keys:
        lines.append(f"🆕 *{total_new} nouveaute(s)* depuis le dernier run")
    lines.append("")

    for p in pages:
        if p.get("error"):
            lines.append(f"*{p['label']}*  ❌ {p['error']}")
            lines.append("")
            continue
        n_ortho = len(p.get("orthographe", []))
        n_typo = len(p.get("typographie", []))
        n_ton = len([f for f in p.get("ton", []) if f.get("type") != "erreur"])
        lines.append(f"*{p['label']}*  <{p['url']}>")
        head = f"ortho: {n_ortho} · typo: {n_typo} · {fmt_registre(p)} · ton: {n_ton} finding(s)"
        lines.append(head)
        # Typo : on groupe par regle (sinon 148 lignes illisibles).
        typo_groups = Counter(t.get("message") for t in p.get("typographie", []))
        if typo_groups:
            top = " ; ".join(f"{n}× {msg}" for msg, n in typo_groups.most_common(2))
            lines.append(f"   typo principale : {top}")
        if p.get("orthographe_error"):
            lines.append(f"   _ortho non verifiee : {p['orthographe_error']}_")
        if p.get("ton_error"):
            lines.append(f"   _ton non verifie : {p['ton_error']}_")
        # Top findings de ton (les plus impactants, max 5)
        for f in p.get("ton", [])[:5]:
            sev = f.get("severite", "?")
            extrait = (f.get("extrait") or "").strip().replace("\n", " ")
            if len(extrait) > 120:
                extrait = extrait[:117] + "…"
            sugg = (f.get("suggestion") or "").strip()
            line = f"   • [{sev}] {f.get('probleme', '')}"
            if extrait:
                line += f" — _{extrait}_"
            if sugg:
                line += f" → {sugg}"
            lines.append(line)
        # Quelques exemples d'ortho (3 max) pour donner a voir
        for o in p.get("orthographe", [])[:3]:
            msg = (o.get("shortMessage") or o.get("message") or "").strip()
            sugg = ", ".join(s for s in (o.get("suggestions") or [])[:2] if s)
            tail = f" → {sugg}" if sugg else ""
            lines.append(f"   · ortho: {msg} (« {o.get('context_match', '')} »){tail}")
        if n_ortho > 3:
            lines.append(f"   _… +{n_ortho - 3} autres remontees ortho_")
        lines.append("")
    return "\n".join(lines).strip()


def slack_bot_token() -> str:
    """Bot token Slack, soit direct (SLACK_BOT_TOKEN) soit extrait d'un DSN style
    Symfony Notifier (SLACK_DSN = slack://TOKEN@default?channel=…)."""
    tok = os.environ.get("SLACK_BOT_TOKEN", "")
    if tok:
        return tok
    dsn = os.environ.get("SLACK_DSN", "")
    if dsn.startswith("slack://"):
        return urllib.parse.urlparse(dsn).username or ""
    return ""


def slack_channel() -> str:
    """Canal cible : SLACK_CHANNEL en priorite, sinon celui du DSN."""
    ch = os.environ.get("SLACK_CHANNEL", "")
    if ch:
        return ch.lstrip("#")
    dsn = os.environ.get("SLACK_DSN", "")
    if dsn.startswith("slack://"):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(dsn).query))
        return q.get("channel", "")
    return ""


def post_webhook(webhook: str, text: str) -> None:
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def post_chat(token: str, channel: str, text: str) -> None:
    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage", data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if not payload.get("ok"):
        err = payload.get("error", "inconnu")
        hint = " (invite le bot dans le canal : /invite @ton-bot)" if err == "not_in_channel" else ""
        raise RuntimeError(f"Slack a refuse : {err}{hint}")


def deliver(text: str) -> str | None:
    """Poste sur Slack. Webhook prioritaire, sinon bot token + canal. None si rien."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if webhook:
        post_webhook(webhook, text)
        return "webhook"
    token, channel = slack_bot_token(), slack_channel()
    if token and channel:
        post_chat(token, channel, text)
        return f"chat.postMessage #{channel}"
    return None


# --- Orchestration ------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Audit periodique de wording (pages Feve).")
    ap.add_argument("--dry-run", action="store_true",
                    help="N'appelle pas Slack ; imprime le rapport sur stdout.")
    ap.add_argument("--state-dir", default=None,
                    help="Dossier de persistance pour le delta (run vs run).")
    ap.add_argument("--pages", default=str(PAGES_PATH), help="Chemin du pages.json.")
    args = ap.parse_args()

    load_dotenv()
    cf = load_checkfr()
    charte = CHARTE_PATH.read_text(encoding="utf-8")
    pages_cfg = json.loads(Path(args.pages).read_text(encoding="utf-8"))["pages"]

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    if not api_key:
        print("⚠️  OPENROUTER_API_KEY absent — la couche ton sera vide.", file=sys.stderr)

    results = [audit_page(p, cf, charte, model, api_key) for p in pages_cfg]

    # Delta : compare l'ensemble des cles a l'etat precedent.
    all_keys: set[str] = set()
    for r in results:
        all_keys |= finding_keys(r)

    baseline: set[str] = set()
    state_file = None
    if args.state_dir:
        sd = Path(args.state_dir)
        sd.mkdir(parents=True, exist_ok=True)
        state_file = sd / "findings.json"
        if state_file.exists():
            try:
                baseline = set(json.loads(state_file.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 — etat corrompu = on repart de zero
                baseline = set()
    new_keys = all_keys - baseline

    when = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    report = render_slack(results, new_keys, when, model)

    can_deliver = bool(
        os.environ.get("SLACK_WEBHOOK_URL") or (slack_bot_token() and slack_channel())
    )
    if args.dry_run or not can_deliver:
        if not can_deliver and not args.dry_run:
            print("⚠️  Aucune cible Slack configuree — rapport imprime ci-dessous.", file=sys.stderr)
        print(report)
    else:
        via = deliver(report)
        print(f"✅ Rapport poste sur Slack via {via} ({len(new_keys)} nouveaute(s)).", file=sys.stderr)

    if state_file is not None:
        state_file.write_text(json.dumps(sorted(all_keys), ensure_ascii=False, indent=0),
                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
