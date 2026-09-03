# Feve Relecture

Relit un texte français avant envoi ou publication. Trois choses, pas plus :

1. **Fautes** : orthographe, grammaire, conjugaison (LanguageTool), et typographie
   française (espaces insécables, guillemets, apostrophes).
2. **Registre** : on vouvoie par défaut chez Feve, sauf sur La Grange où on tutoie les
   porteurs de projet. Le skill signale un mélange tu/vous et un registre inadapté, et
   demande le destinataire s'il ne le devine pas.
3. **Tics d'IA** : tiret cadratin en séparateur, point médian, connecteurs mécaniques,
   phrases toutes calibrées pareil.

S'invoque via `/feve-relecture:relecture`, ou se déclenche seul quand on demande une
relecture. Il ne corrige rien sans accord.

La détection des fautes repose sur un appel à [LanguageTool](https://languagetool.org/),
donc sur un accès réseau : coupé d'internet, il ne reste que la typographie et le
comptage tu/vous, calculés en local. Le script qui porte tout ça est en Python, mais
sans aucune dépendance à installer (bibliothèque standard uniquement), et Python 3 est
déjà présent sur macOS, sur Linux et dans le bac à sable de claude.ai.
