---
name: relecture
description: >-
  Relit un texte en français avant envoi ou publication : fautes d'orthographe,
  de grammaire et de conjugaison, cohérence et justesse du tutoiement/vouvoiement,
  et tics d'écriture qui font « écrit par une IA ». À utiliser dès qu'on veut
  vérifier ou nettoyer un email, un post, une page ou une copie produit.
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py *)
  - Bash(printf *)
---

Lance le script sur le texte, puis rends un rapport court. Ne corrige rien avant accord.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py <chemin>            # fichier txt, md ou html
printf '%s' "<texte>" | python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py --stdin
```

Hors Claude Code, le script est en `scripts/check-fr.py`. S'il ne tourne pas, analyse
toi-même et dis-le.

**1. Fautes.** Orthographe, grammaire, conjugaison. Ignore les faux positifs sur FEVE
et sur les noms de produits. Groupe les remontées typographiques répétitives.

**2. Registre.** Chez Feve on vouvoie par défaut, tout le monde, investisseurs et
cédants compris. Seule exception : sur La Grange, on tutoie les porteurs de projet.
Signale un mélange tu/vous dans le texte (le script les compte) et un registre inadapté
au destinataire. Si le texte ne dit pas à qui il s'adresse, demande-le.

**3. Tics d'IA.** Tiret cadratin ou demi-cadratin en séparateur, point médian, « en
outre », « par ailleurs », « de plus », « néanmoins », « il est crucial de », « dans un
monde où », « il ne s'agit pas seulement de X, mais de Y », adverbes en rafale, phrases
toutes de la même longueur, emojis en tête de puce.
