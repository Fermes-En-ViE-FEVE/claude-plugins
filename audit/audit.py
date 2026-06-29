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
        # 2500 tokens : assez pour ~6 findings verbeux sans tronquer le JSON.
        "max_tokens": 2500,
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


# --- Tri des remontees ortho : fiables vs "mots inconnus" ---------------------
# LanguageTool est un dico generaliste. Sur une page Feve (noms de fermes, sigles
# du secteur : ESUS, Finansol, IFI...), la regle "faute de frappe" crache surtout
# des noms propres -> bruit. On separe ces "mots inconnus" du compte principal pour
# ne pas noyer les vraies remontees (grammaire, accords, typo, typos minuscules).
SPELLING_RULE = "FR_SPELLING_RULE"
# Marque ecrite sans accent : LanguageTool veut "fève/fêtes/rêves" -> faux positif
# systematique, retire entierement (meme pas affiche comme mot inconnu).
BRAND_TOKENS = {"feve", "feves", "fève", "fèves", "eve", "ève"}
# Regles LanguageTool ignorees dans l'audit : soit le conseil est faux sur de la
# copie marketing (chiffres -> lettres alors qu'on veut "9 experts", "55 fermes"),
# soit la regle est trop peu fiable sur du texte web "aplati" en fragments (accord
# d'adjectif detache faussement signale sur une enumeration ; "phrase incomplete" /
# point ou majuscule manquants declenches par des bouts de texte isoles).
NOISY_RULES = {
    "AGREEMENT_POSTPONED_ADJ",
    "NOMBRES_EN_LETTRES_2",
    "NOMBRES_EN_LETTRES_2_IMPROVED",
    "DETERMINER_SENT_END",
    "D_N",
    "POINT",
    "UPPERCASE_SENTENCE_START",
}


def _looks_like_proper_noun(token: str) -> bool:
    """Heuristique : un mot inconnu capitalise, en capitales, ou contenant un
    chiffre est quasi toujours un nom propre / sigle (ESUS, Bonfossé, France2),
    pas une faute de frappe. Les vrais typos (souhaitesconstruire) sont minuscules."""
    t = token.strip()
    if not t:
        return False
    if any(c.isdigit() for c in t):
        return True
    return t[0].isupper()


def split_ortho(matches: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Pre-filtre heuristique (cheap) avant arbitrage IA. Retourne 3 listes :

      - reliable  : regles non-orthographe (grammaire, accord, typo) = haute confiance ;
      - ambiguous : "faute de frappe" sur mot MINUSCULE = a trancher par l'IA
        (vrai typo comme 'souhaitesconstruire' vs jargon comme 'terdecies') ;
      - unknown   : "faute de frappe" sur mot capitalise/sigle/chiffre = nom propre
        quasi certain, ecarte sans deranger l'IA (economise des tokens).
    Les faux positifs de marque (feve/fève...) et les regles bruyantes sont jetes."""
    reliable: list[dict] = []
    ambiguous: list[dict] = []
    unknown: list[dict] = []
    for o in matches:
        token = (o.get("context_match") or "").strip()
        if token.lower() in BRAND_TOKENS:
            continue
        if o.get("rule") in NOISY_RULES:
            continue
        if o.get("rule") == SPELLING_RULE:
            (unknown if _looks_like_proper_noun(token) else ambiguous).append(o)
        else:
            reliable.append(o)
    return reliable, ambiguous, unknown


def _parse_ortho_verdict(content: str, n: int) -> set[int]:
    """Extrait l'ensemble des indices "vraies fautes" du JSON IA (tolere les ``` et
    le texte autour). Leve si rien n'est parsable -> le caller degrade en sur."""
    s = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    candidates = []
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        candidates.append(m.group(0))
    candidates.append(s)
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        raw = data.get("vraies_fautes", []) if isinstance(data, dict) else []
        keep: set[int] = set()
        for x in raw:
            try:
                i = int(x)
            except (ValueError, TypeError):
                continue
            if 0 <= i < n:
                keep.add(i)
        return keep
    raise ValueError("verdict ortho IA non parsable")


def adjudicate_ortho(candidates: list[dict], model: str, api_key: str) -> tuple[list[dict], list[dict]]:
    """Fait trancher par l'IA les remontees ortho ambigues (mots minuscules inconnus
    du dico) : vraie faute de francais vs nom propre / terme metier / mot rare correct.
    Retourne (confirmees, rejetees). Leve en cas d'echec -> le caller degrade en sur."""
    listing = "\n".join(
        f'{i}. "{(o.get("context_match") or "").strip()}"'
        f' — contexte : «{(o.get("context") or "").strip()[:140]}»'
        f' — suggestions LT : {", ".join(s for s in (o.get("suggestions") or [])[:3] if s) or "(aucune)"}'
        for i, o in enumerate(candidates)
    )
    system = (
        "Tu es relecteur francais. LanguageTool a signale ces mots comme inconnus de son "
        "dictionnaire. Pour chacun, juge d'apres le contexte si c'est une VRAIE faute de "
        "francais (mot mal orthographie, mots colles sans espace, accent fautif) ou un FAUX "
        "POSITIF (nom propre, marque, sigle, terme metier/juridique, mot rare mais correct).\n"
        "Reponds UNIQUEMENT en JSON, sans texte autour : {\"vraies_fautes\": [numeros]} ou "
        "[numeros] sont les indices des vraies fautes. Liste vide si tout est faux positif."
    )
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": listing},
        ],
    }).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "feve-audit-wording",
    }
    payload = _openrouter_post(body, headers)
    content = payload["choices"][0]["message"]["content"]
    keep = _parse_ortho_verdict(content, len(candidates))
    confirmed = [o for i, o in enumerate(candidates) if i in keep]
    rejected = [o for i, o in enumerate(candidates) if i not in keep]
    return confirmed, rejected


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
        reliable, ambiguous, unknown = split_ortho(cf.check_orthographe(texte))
    except (Exception, SystemExit) as e:  # check-fr leve SystemExit si LT injoignable
        out["orthographe"] = []
        out["mots_inconnus"] = []
        out["orthographe_error"] = str(e)
    else:
        # L'IA tranche le reste ambigu (jargon minuscule). Si l'appel echoue ou
        # qu'il n'y a pas de cle, on garde tous les candidats (degradation sure).
        if api_key and ambiguous:
            try:
                confirmed, rejected = adjudicate_ortho(ambiguous, model, api_key)
                reliable += confirmed
                unknown += rejected
            except Exception as e:  # noqa: BLE001
                reliable += ambiguous
                out["ortho_adjudication_error"] = str(e)
        else:
            reliable += ambiguous
        reliable.sort(key=lambda o: o.get("rule") == SPELLING_RULE)  # ortho en dernier
        out["orthographe"] = reliable
        out["mots_inconnus"] = unknown

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


def render_slack(pages: list[dict], new_keys: set[str], when: str, model: str,
                 baseline_existed: bool) -> str:
    lines = [f"*Audit wording — {when}*  _(modele: {model})_"]
    if not baseline_existed:
        lines.append("📋 Premier run — référence établie pour le suivi des prochains audits.")
    elif new_keys:
        lines.append(f"🆕 *{len(new_keys)} nouveauté(s)* depuis le dernier run")
    else:
        lines.append("✅ Aucune nouveauté depuis le dernier run.")
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
        # Mots inconnus du dico (noms propres / jargon) : comptés à part, jamais
        # mélangés aux vraies remontées — sinon le rapport donne des points randoms.
        unknown = p.get("mots_inconnus", [])
        if unknown:
            ex = list(dict.fromkeys(
                (o.get("context_match") or "").strip()
                for o in unknown if (o.get("context_match") or "").strip()
            ))[:6]
            lines.append(f"   mots inconnus du dico : {len(unknown)} "
                         f"(noms propres / jargon probables, non comptés) — ex. {', '.join(ex)}")
        # Typo : on groupe par regle (sinon 148 lignes illisibles).
        typo_groups = Counter(t.get("message") for t in p.get("typographie", []))
        if typo_groups:
            top = " ; ".join(f"{n}× {msg}" for msg, n in typo_groups.most_common(2))
            lines.append(f"   typo principale : {top}")
        if p.get("orthographe_error"):
            lines.append(f"   _ortho non verifiee : {p['orthographe_error']}_")
        if p.get("ortho_adjudication_error"):
            lines.append(f"   _ortho non arbitree par IA (heuristique seule) : {p['ortho_adjudication_error']}_")
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
        # On dédoublonne par (message, extrait) pour ne pas gaspiller un slot
        # d'affichage sur une même remontée répétée (ex. « carte cadeau » ×2).
        shown = 0
        seen_ex: set[tuple[str, str]] = set()
        for o in p.get("orthographe", []):
            msg = (o.get("shortMessage") or o.get("message") or "").strip()
            cm = o.get("context_match", "")
            if (msg, cm) in seen_ex:
                continue
            seen_ex.add((msg, cm))
            sugg = ", ".join(s for s in (o.get("suggestions") or [])[:2] if s)
            tail = f" → {sugg}" if sugg else ""
            lines.append(f"   · ortho: {msg} (« {cm} »){tail}")
            shown += 1
            if shown >= 5:
                break
        if n_ortho > shown:
            lines.append(f"   _… +{n_ortho - shown} autres remontees ortho_")
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
    baseline_existed = bool(baseline)

    when = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    report = render_slack(results, new_keys, when, model, baseline_existed)

    can_deliver = bool(
        os.environ.get("SLACK_WEBHOOK_URL") or (slack_bot_token() and slack_channel())
    )
    if args.dry_run or not can_deliver:
        if not can_deliver and not args.dry_run:
            print("⚠️  Aucune cible Slack configuree — rapport imprime ci-dessous.", file=sys.stderr)
        print(report)
    else:
        via = deliver(report)
        summary = "premier run" if not baseline_existed else f"{len(new_keys)} nouveaute(s)"
        print(f"✅ Rapport poste sur Slack via {via} ({summary}).", file=sys.stderr)

    if state_file is not None:
        state_file.write_text(json.dumps(sorted(all_keys), ensure_ascii=False, indent=0),
                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
