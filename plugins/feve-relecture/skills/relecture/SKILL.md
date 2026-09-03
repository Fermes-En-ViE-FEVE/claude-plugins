---
name: relecture
description: >-
  Relit un texte en français qu'on te donne (collé ou chemin de fichier) avant envoi ou
  publication : fautes d'orthographe, de grammaire et de conjugaison, cohérence du
  tutoiement/vouvoiement, cohérence interne, et tics d'écriture qui font « écrit par une
  IA ». Pour une page en ligne à auditer depuis son URL, utiliser plutôt audit-page.
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py *)
  - Bash(printf *)
---

Lance le script sur le texte, lis les règles, rends un rapport court. Ne corrige rien
avant accord.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py <chemin>            # fichier txt, md ou html
printf '%s' "<texte>" | python3 ${CLAUDE_SKILL_DIR}/scripts/check-fr.py --stdin
```

Hors Claude Code, le script est en `scripts/check-fr.py`. S'il ne tourne pas, analyse
toi-même et dis-le.

Les règles d'écriture (registre, cohérence, tics d'IA, faux positifs) sont dans
`${CLAUDE_PLUGIN_ROOT}/regles-ecriture.md`, ou dans `regles-ecriture.md` à côté de ce
fichier si la variable n'est pas substituée. Lis-le avant d'analyser.

Rends trois blocs, chaque point classé **haute**, **moyenne** ou **faible** :

**1. Fautes.** Orthographe, grammaire, conjugaison, typographie. Groupe les remontées
répétitives plutôt que de les lister une par une.

**2. Registre et cohérence.** Ce que dit le fichier de règles. Le script compte les tu et
les vous, sers-t'en. Si le texte ne dit pas à qui il s'adresse, demande-le.

**3. Tics d'IA.** Idem, d'après le fichier de règles.

Termine par ce que tu as vérifié et qui est bon, pour ne pas donner l'impression que
tout est cassé.
