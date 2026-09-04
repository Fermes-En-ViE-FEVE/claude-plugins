#!/usr/bin/env python3
"""Vérifie un texte français : orthographe (LanguageTool) + typographie + registre.

Généraliste : accepte du texte collé (--stdin) ou un fichier (.txt, .md, .html).
Le HTML est nettoyé pour ne garder que le texte visible. Le ton de voix vs charte
(vocabulaire à bannir, preuve > promesse, etc.) est évalué SÉPARÉMENT par Claude
dans le skill `relecture` : ce script ne traite QUE ce qui est scriptable de façon
fiable : orthographe, typo française, et un signal objectif sur le registre
(comptage des marqueurs tutoiement vs vouvoiement).

Usage :
    python3 check-fr.py mon-texte.md
    python3 check-fr.py page.html
    pbpaste | python3 check-fr.py --stdin
    python3 check-fr.py --stdin --html < page.html

Sortie : JSON sur stdout avec quatre blocs :
  - "orthographe" : issues remontées par LanguageTool (FR-FR)
  - "typographie" : issues remontées par nos règles maison
  - "registre"    : marqueurs tutoiement / vouvoiement détectés (signal de cohérence)

Pré-requis : connexion Internet pour l'appel à api.languagetool.org.
Le tier gratuit autorise ~20 req/min, max 10k chars par requête.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

LANGUAGETOOL_API = "https://api.languagetool.org/v2/check"
MAX_CHUNK_CHARS = 9000  # marge sous la limite 10k de LT


# --- Extraction de texte HTML ---
class TextExtractor(HTMLParser):
    """Parse un HTML et accumule le texte visible (hors <script>, <style>, etc.)."""
    SKIP_TAGS = {"script", "style", "noscript", "template"}
    BREAK_TAGS = {
        "p", "div", "section", "article", "header", "footer", "li", "h1", "h2",
        "h3", "h4", "h5", "h6", "br", "tr", "td", "th",
    }
    # Éléments « autonomes » : liens et boutons portent en général un libellé
    # indépendant (nav, CTA, cartes). On les sépare par un saut de ligne, sinon
    # LanguageTool lit deux libellés voisins comme une même phrase et signale de
    # faux « majuscule en milieu de phrase » / « espace avant point ».
    SEGMENT_TAGS = {"a", "button"}
    # Ponctuation qui ne se fait jamais précéder d'une espace en français : on
    # n'insère pas d'espace inline juste devant (« mot . » resterait fautif).
    ATTACH_PUNCT = ".,…)]}"

    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._skip_depth = 0
        # Une frontière inline a été franchie (ex. </a><a>) : on attend le
        # prochain texte pour décider d'insérer un espace, afin de ne pas coller
        # deux mots de balises voisines (« trouvéeAcheter »).
        self._pending_space = False

    def _flush_pending(self, nxt: str = "") -> None:
        """Matérialise une séparation inline en espace, sauf si ça collerait à
        une élision (l'/d'/j'…) ou si le texte suivant démarre par une ponctuation
        qui s'attache au mot précédent (« mot . » → « mot. »)."""
        if not self._pending_space:
            return
        self._pending_space = False
        if not (self._buf and self._buf[-1]):
            return
        if self._buf[-1][-1] in " \n\t'’":
            return
        nstrip = nxt.lstrip()
        if nstrip and nstrip[0] in self.ATTACH_PUNCT:
            return
        self._buf.append(" ")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self.BREAK_TAGS or tag in self.SEGMENT_TAGS:
            self._buf.append("\n")
            self._pending_space = False
            return
        if tag == "img":
            for k, v in attrs:
                if k == "alt" and v:
                    self._buf.append(f" {v} ")
        # Tout autre tag est inline de mise en forme (span, strong, em…) : il
        # sépare le texte de part et d'autre sans le couper en lignes.
        self._pending_space = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in self.BREAK_TAGS or tag in self.SEGMENT_TAGS:
            self._buf.append("\n")
            self._pending_space = False
            return
        self._pending_space = True

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._flush_pending(data)
        self._buf.append(data)

    def text(self) -> str:
        raw = "".join(self._buf)
        raw = html.unescape(raw)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n[ \t]+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def extract_text(src: str, is_html: bool) -> str:
    if not is_html:
        return src.strip()
    ext = TextExtractor()
    ext.feed(src)
    return ext.text()


# --- Règles typographie française ---
TYPO_RULES = [
    (
        re.compile(r'(?<!\s)([!?;:])'),
        "Manque l'espace insécable AVANT la ponctuation double",
        "Toute ponctuation double (! ? ; :) en français doit être précédée d'une espace insécable (Opt+Espace sur Mac)",
    ),
    (
        re.compile(r'"([^"]{2,200})"'),
        "Guillemets droits anglais : utiliser les guillemets français",
        "Remplace par « … » (avec espaces insécables à l'intérieur)",
    ),
    (
        re.compile(r"(\w)'(\w)"),
        "Apostrophe droite : utiliser l'apostrophe courbe",
        "Remplace ' par ’ (U+2019)",
    ),
    (
        re.compile(r"\s[\u2014\u2013]\s|(?<!-)--(?!-)"),
        "Tiret en séparateur : marqueur d'écriture IA",
        "Remplace par deux-points, virgule, parenthèses ou une nouvelle phrase",
    ),
    (
        re.compile(r"\s\u00b7\s"),
        "Point médian en séparateur : marqueur d'écriture IA",
        "Remplace par une virgule ou une nouvelle phrase",
    ),
    (
        re.compile(r"([«])(?! | )"),
        "Manque l'espace insécable APRÈS «",
        "Après « doit suivre une espace insécable, puis le contenu",
    ),
    (
        re.compile(r"(?<! )(?<! )([»])"),
        "Manque l'espace insécable AVANT »",
        "Avant » doit précéder une espace insécable",
    ),
    (
        re.compile(r"\b(etc)(\.\.\.|…)"),
        "etc. ne prend jamais de points de suspension",
        "Écris simplement « etc. »",
    ),
    (
        re.compile(r"\b(\w+)'(?=\w)"),  # apostrophe droite générique (info, doublon possible)
        "Apostrophe droite",
        "Utilise l'apostrophe courbe ’ (U+2019)",
    ),
    (
        re.compile(r"\bcoeur\b|\boeuvre\b|\boeil\b|\bvoeu\b", re.IGNORECASE),
        "Ligature œ manquante",
        "Écris cœur / œuvre / œil / vœu avec la ligature œ",
    ),
    (
        # Espaces fines et insécables (U+202F, U+00A0) exclues : elles sont légitimes.
        re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]"),
        "Caractère invisible parasite",
        "Artefact de copier-coller depuis un éditeur riche : à supprimer",
    ),
    (
        re.compile(r":\*|&(?:nbsp|amp|lt|gt|quot|#39);"),
        "Artefact de CMS resté brut",
        "Balisage ou entité HTML affiché tel quel : à corriger à la source du contenu",
    ),
]


def check_typography(text: str) -> list[dict]:
    issues: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for rx, msg, hint in TYPO_RULES:
        for m in rx.finditer(text):
            key = (m.start(), msg)
            if key in seen:
                continue
            seen.add(key)
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].replace("\n", " ⏎ ")
            issues.append({
                "message": msg,
                "hint": hint,
                "offset": m.start(),
                "match": m.group(0),
                "context": context,
            })
    return issues


# --- Registre : tutoiement vs vouvoiement (signal objectif) ---
TU_MARKERS = re.compile(
    r"\b(tu|ton|ta|tes|toi|t')\b|\bt'(?=[aeiouyéèêhAEIOUYÉÈÊH])", re.IGNORECASE)
VOUS_MARKERS = re.compile(r"\b(vous|votre|vos)\b", re.IGNORECASE)


def _markers(rx: re.Pattern, text: str) -> list[dict]:
    out: list[dict] = []
    for m in rx.finditer(text):
        start = max(0, m.start() - 25)
        end = min(len(text), m.end() + 25)
        out.append({
            "match": m.group(0),
            "offset": m.start(),
            "context": text[start:end].replace("\n", " ⏎ "),
        })
    return out


def check_registre(text: str) -> dict:
    tu = _markers(TU_MARKERS, text)
    vous = _markers(VOUS_MARKERS, text)
    return {
        "tutoiement_count": len(tu),
        "vouvoiement_count": len(vous),
        "mixte": len(tu) > 0 and len(vous) > 0,
        "tutoiement_samples": tu[:8],
        "vouvoiement_samples": vous[:8],
    }


# --- Orthographe / grammaire via LanguageTool ---
def call_languagetool(text: str) -> list[dict]:
    if not text.strip():
        return []
    data = urllib.parse.urlencode({
        "text": text,
        "language": "fr",
        "level": "default",
    }).encode("utf-8")
    req = urllib.request.Request(
        LANGUAGETOOL_API,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "feve-check-wording/0.1 (check-fr)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise SystemExit(f"❌ LanguageTool a refusé ({e.code}) : {detail}")
    except urllib.error.URLError as e:
        raise SystemExit(f"❌ Impossible de joindre LanguageTool : {e.reason}")
    return payload.get("matches", [])


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        end = min(len(text), pos + max_chars)
        if end < len(text):
            for delim in ("\n\n", "\n", ". ", " "):
                cut = text.rfind(delim, pos + max_chars // 2, end)
                if cut != -1:
                    end = cut + len(delim)
                    break
        chunks.append(text[pos:end])
        pos = end
    return chunks


def check_orthographe(text: str) -> list[dict]:
    issues: list[dict] = []
    offset_accum = 0
    for chunk in chunk_text(text):
        for m in call_languagetool(chunk):
            ctx = m.get("context", {})
            ctx_text = ctx.get("text", "")
            ctx_offset = ctx.get("offset", 0)
            ctx_length = ctx.get("length", 0)
            issues.append({
                "rule": m.get("rule", {}).get("id"),
                "category": m.get("rule", {}).get("category", {}).get("name"),
                "message": m.get("message"),
                "shortMessage": m.get("shortMessage"),
                "offset": offset_accum + m.get("offset", 0),
                "length": m.get("length", 0),
                "context": ctx_text,
                "context_match": ctx_text[ctx_offset:ctx_offset + ctx_length] if ctx_text else "",
                "suggestions": [r.get("value") for r in m.get("replacements", [])[:5]],
            })
        offset_accum += len(chunk)
    return issues


# --- Orchestration ---
def main() -> int:
    ap = argparse.ArgumentParser(description="Vérifie un texte français (ortho + typo + registre).")
    ap.add_argument("path", nargs="?", help="Chemin vers un fichier .txt/.md/.html")
    ap.add_argument("--stdin", action="store_true", help="Lire le texte depuis stdin")
    ap.add_argument("--html", action="store_true", help="Forcer l'extraction HTML")
    ap.add_argument("--text", action="store_true", help="Forcer le mode texte brut (pas d'extraction HTML)")
    ap.add_argument("--no-orthographe", action="store_true",
                    help="Ne pas appeler LanguageTool (coupure réseau / rate-limit)")
    args = ap.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
        source = "<stdin>"
        is_html = args.html
    elif args.path:
        p = Path(args.path).expanduser().resolve()
        if not p.is_file():
            sys.exit(f"❌ Fichier introuvable : {p}")
        raw = p.read_text(encoding="utf-8")
        source = str(p)
        is_html = args.html or (p.suffix.lower() in {".html", ".htm"} and not args.text)
    else:
        sys.exit("❌ Fournis un chemin de fichier ou --stdin. Voir --help.")

    text = extract_text(raw, is_html)
    if not text.strip():
        sys.exit("❌ Aucun texte exploitable trouvé.")

    result = {
        "source": source,
        "is_html": is_html,
        "chars_analyzed": len(text),
        "registre": check_registre(text),
        "typographie": check_typography(text),
        "orthographe": [] if args.no_orthographe else check_orthographe(text),
        "no_orthographe": args.no_orthographe,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
