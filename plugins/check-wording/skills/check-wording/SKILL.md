---
name: check-wording
description: >-
  Relit et corrige une communication écrite en français (email, post LinkedIn,
  page web, copie produit, message in-app) : orthographe, grammaire, typographie
  française (espaces insécables, guillemets, apostrophes), cohérence du registre
  (tutoiement / vouvoiement) et conformité au ton de voix Feve. À utiliser dès
  qu'on veut vérifier ou nettoyer un texte avant de l'envoyer/publier. Le skill
  DEMANDE D'ABORD le contexte (registre, ton, audience) car il varie selon
  l'applicatif Feve, puis produit un rapport priorisé sans rien modifier sans accord.
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py *)
  - Bash(printf *)
---

Tu vas relire un texte français et produire un **rapport priorisé et actionnable**.
La règle d'or : **tu ne corriges rien tant que l'utilisateur n'a pas donné son go.**

Le registre (tu/vous) et le ton **ne sont jamais présumés** : Feve a plusieurs
applicatifs, certains tutoient, d'autres vouvoient. Tu demandes le contexte avant
d'analyser.

## Étape 1 — Recueillir le texte ET le contexte

D'abord, récupère le **texte à relire** :
- Si l'utilisateur l'a déjà collé dans la conversation → utilise-le.
- S'il a donné un **chemin de fichier** → tu le liras via le script à l'étape 2.
- Sinon, demande-lui de coller le texte ou de donner le chemin.

Ensuite, **avant toute analyse de fond**, pose le contexte via `AskUserQuestion`
(une seule fois, en regroupant les questions). N'invente pas les réponses :

1. **Registre** — tutoiement / vouvoiement / *je ne sais pas, déduis du texte*.
2. **Ton visé** — propose des options courtes et laisse « Autre » libre. Exemples :
   *chaleureux et direct* · *institutionnel et rassurant* · *expert et factuel* ·
   *militant et engagé*. Adapte selon ce que tu sais du support.
3. **Contexte / audience** (champ libre utile) — quel applicatif ou canal, et à qui
   ça s'adresse (ex. « email aux porteurs de projet », « post LinkedIn grand public »,
   « page produit investisseurs »). Ça affine l'analyse du ton.

Si l'utilisateur a **déjà** précisé tout ça dans sa demande, ne repose pas la question.

## Étape 2 — Lancer le script (ortho + typo + signal de registre)

Le script est bundlé dans le plugin. Lance-le selon la source :

```bash
# Fichier (txt, md, html — le HTML est nettoyé automatiquement)
python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py <chemin>

# Texte collé : passe-le sur stdin
printf '%s' "<le texte>" | python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py --stdin
```

⏱ ~10-15 s (appel à LanguageTool, tier gratuit). Capture la sortie JSON, parse-la.

Le JSON contient :
- `orthographe` : remontées LanguageTool (fautes de frappe, grammaire, accords, ponctuation).
- `typographie` : règles maison (espaces insécables, guillemets, apostrophes, tirets, ligatures).
- `registre` : `tutoiement_count`, `vouvoiement_count`, `mixte` (true si les deux
  coexistent) + échantillons. C'est un **signal objectif** pour vérifier la cohérence
  avec le registre choisi à l'étape 1.

> Si Python n'est pas dispo ou si tu travailles dans un environnement sans shell
> (ex. Claude web), fais l'analyse ortho/typo toi-même du mieux possible et
> préviens que la passe LanguageTool n'a pas tourné.

## Étape 3 — Charger la charte de ton

Lis la charte transverse embarquée :

```
${CLAUDE_SKILL_DIR}/references/ton-de-voix-feve.md
```

Puis relis le texte et identifie 0 à 5 passages problématiques selon la charte ET
le ton/registre demandés à l'étape 1 :
- **Registre** : le texte respecte-t-il le tu/vous choisi ? Croise avec `registre.mixte`.
  Pas de `on` parasite, pas de `notre équipe`.
- **Vocabulaire à bannir** : *solution* (creux), *innovant·e*, *démocratiser*,
  *premium*, *authentique*, *engagement* sans contenu.
- **Preuve > promesse** : phrases sans chiffres ni preuves qui pourraient être renforcées.
- **Ton** : l'écriture colle-t-elle au ton visé (ex. trop corporate alors qu'on
  voulait chaleureux) ?
- **Longueur** : phrases > 30 mots à raccourcir. **Parallélisme** des listes.

## Étape 4 — Filtrer les faux positifs

Avant de présenter, **ignore systématiquement** (cf. charte §8) :
- LanguageTool suggérant *fève* / *fête* / *rêve* à la place de **FEVE/Feve**.
- Noms de produits Feve.
- Majuscule réclamée sur un titre délibérément en minuscule.
- Mots issus de balises/URLs s'il restait du HTML mal nettoyé.

## Étape 5 — Présenter le rapport

### A. Synthèse en 1 phrase
Ex. « Copie globalement propre — 2 vraies corrections. » ou « Registre incohérent
(tu et vous mélangés) + typo à reprendre ; orthographe OK. »

### B. Registre
Si `mixte` = true OU si le registre ne correspond pas à celui demandé : signale-le
en premier (c'est souvent le reproche n°1). Montre 2-3 exemples concrets.

### C. Orthographe / grammaire
Les **vraies** issues après filtrage. Pour chacune : type, extrait de contexte
(mot fautif en **gras**), suggestion(s). Si > 10 : montre les 10 plus impactantes,
dis combien restent, propose la liste complète.

### D. Typographie française
**Groupe les issues répétitives.** Ex. : « ⚠️ Espace insécable manquante avant
ponctuation double : 60 occurrences. » plutôt que 60 lignes. Pour les cas isolés :
1 ligne chacun.

### E. Ton de voix
0-5 passages : citation courte → pourquoi ça coince vs charte/ton → reformulation
proposée. Du plus impactant (vocabulaire interdit, mauvais registre) au plus mineur.

### F. Proposition d'action
Termine par des propositions, sans rien appliquer :
- « Je corrige la typo + l'ortho directement dans le fichier/texte ? »
- « Je reformule les passages de ton ? Dis-moi les numéros qui t'intéressent. »

## Règles

- **Ne corrige RIEN sans go explicite.** Le ton est subjectif : propositions, pas verdicts.
- Si l'utilisateur dit « corrige tout » : applique d'abord la typo (auto-fixable sans
  risque), puis l'ortho avec ses suggestions, puis les reformulations de ton après accord.
- Si LanguageTool est en rate-limit (HTTP 429, tier gratuit ~20 req/min) : relance
  avec `--no-orthographe` et préviens — typo et ton restent vérifiables.
- Réponds toujours en français.
