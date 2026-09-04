# Feve Relecture

Deux skills qui partagent les mêmes règles d'écriture, dans
[`regles-ecriture.md`](regles-ecriture.md) à la racine du plugin. On modifie une règle
là, les deux suivent.

`audit-page` tient en plus [`reperes-feve.md`](reperes-feve.md) : ce qu'on a compris du
site au fil des audits (comment tel chiffre se met à jour, quel bug vient d'un composant
partagé) pour ne pas le redécouvrir à chaque passage.

| Skill | Pour quoi | Où |
|---|---|---|
| [`relecture`](skills/relecture/) | Un texte qu'on colle ou un fichier : fautes, registre, cohérence, tics d'IA. | Partout, Chat compris |
| [`audit-page`](skills/audit-page/) | Une page en ligne depuis son URL : en plus, liens et CTA réellement cliqués, contenu invisible pour Google, cohérence du parcours. | Claude Code et Cowork, il faut un navigateur |

S'invoquent via `/feve-relecture:relecture` et `/feve-relecture:audit-page`, ou se
déclenchent seuls quand on demande une relecture. Aucun des deux ne corrige sans accord.

La détection des fautes repose sur un appel à [LanguageTool](https://languagetool.org/),
donc sur un accès réseau : coupé d'internet, il reste la typographie et le comptage
tu/vous, calculés en local. Le script est en Python, sans aucune dépendance à installer,
et Python 3 est déjà présent sur macOS, sur Linux et dans le bac à sable de claude.ai.
