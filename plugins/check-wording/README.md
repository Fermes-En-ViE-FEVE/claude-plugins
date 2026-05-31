# check-wording

Skill Claude Code pour relire une **communication écrite en français** avant
envoi/publication : orthographe, grammaire, typographie française, cohérence du
**registre** (tutoiement / vouvoiement) et conformité au **ton de voix Feve**.

Conçu pour **tous les applicatifs Feve** : le skill ne présume jamais le registre
ni le ton (ils varient d'un produit à l'autre) — il **demande le contexte** au
lancement, puis adapte son analyse.

> Successeur de l'ancien slash command `/check-wording` du repo `landings`, généralisé
> et rendu autonome (charte de ton embarquée, plus de dépendance à `src/*.html`).

## Ce que ça couvre

- **Orthographe / grammaire** — via LanguageTool (FR-FR).
- **Typographie française** — espaces insécables (`?` `!` `;` `:` `«` `»`),
  guillemets `« »`, apostrophe courbe `’`, tiret cadratin `—`, ligatures `œ`.
- **Registre** — détecte objectivement un mélange tu/vous, vérifie vs le registre voulu.
- **Ton de voix** — vocabulaire à bannir, preuve > promesse, longueur, parallélisme,
  selon la charte transverse embarquée (`references/ton-de-voix-feve.md`).

## Utilisation

S'invoque via `/check-wording:check-wording` ou se déclenche automatiquement quand on
demande de relire/corriger un texte. Le skill :

1. récupère le texte (collé ou chemin de fichier) ;
2. **demande** le registre, le ton visé et l'audience ;
3. lance l'analyse (script + charte) ;
4. rend un **rapport priorisé** ;
5. **ne corrige rien** sans ton accord.

## Prérequis

- **Python 3** (pour la passe ortho/typo).
- **Connexion internet** — appel à [LanguageTool](https://languagetool.org/)
  (tier gratuit, ~20 req/min). Sans réseau, la typo et le ton restent vérifiables.

## Source de vérité du ton de voix

La charte transverse vit dans
[`skills/check-wording/references/ton-de-voix-feve.md`](skills/check-wording/references/ton-de-voix-feve.md).
La modifier ici + push = nouvelle version pour toute l'équipe.
