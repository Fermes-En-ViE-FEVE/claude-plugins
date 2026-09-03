---
name: audit-page
description: >-
  Audite une page web Feve en ligne depuis son URL : liens et CTA réellement cliqués,
  contenu invisible pour Google, cohérence du parcours, plus toutes les règles
  d'écriture (registre, cohérence, tics d'IA). Demande un navigateur, donc Claude Code
  ou Cowork. Pour relire un texte qu'on te donne, utiliser plutôt relecture.
---

Deux passes sur la page : ce qu'un outil de QA attrape, puis ce qu'il rate. La seconde
est celle qui a de la valeur.

Les règles d'écriture sont dans `${CLAUDE_PLUGIN_ROOT}/regles-ecriture.md`. Lis-les, elles
s'appliquent au texte de la page comme à n'importe quel texte.

## Méthode

Ouvre la page dans le navigateur, en 1440px. Ne juge jamais sur une capture seule :
croise toujours avec `get_page_text` (le texte réellement affiché) et `read_page`
(l'arbre d'accessibilité, qui expose aussi les accordéons fermés).

**Un `href="#"` est un déclencheur de vérification, jamais une conclusion.** Avant de
cliquer, regarde ses attributs en JS (`aria-haspopup`, `data-mm`, une classe contenant
« modal-trigger ») : ça suffit souvent à conclure « popup légitime » sans dépenser un
clic. Sinon clique pour de vrai et relis la page : rien de neuf n'apparaît, c'est cassé.
Un clic simulé en JS (`element.click()`) ne suffit pas à conclure « cassé », certains
frameworks ignorent les clics non issus d'un vrai geste souris ; utilise `computer` avec
des coordonnées à l'écran pour le clic qui tranche. Pour une ancre `#nom`, vérifie la
cible avec `javascript_tool` (`document.querySelector('#nom')`), surtout pas en
cherchant le mot dans le texte visible, un id n'a aucune raison d'y figurer. Si tu ne
peux pas trancher, classe le point « à vérifier » au lieu de l'affirmer.

## Passe 1, mécanique

- Liste les liens (`read_page`, filtre interactif), clique les CTA principaux et tout
  « en savoir plus », « voir plus », « FAQ complète ». Un saut suffit pour juger.
- Déplie chaque accordéon et lis la réponse entière.
- Cherche les artefacts de CMS restés bruts (`:*`, `**`, balises échappées) et les
  phrases cassées (ponctuation orpheline, mot manquant).
- Une info visible à l'écran mais absente de `get_page_text` et de `read_page` est une
  image sans texte alternatif : invisible pour Google et les lecteurs d'écran. Grave si
  c'est un bloc entier, par exemple un tableau comparatif.
- Vérifie que les vidéos embarquées existent, en ouvrant l'URL du lecteur.
- Un accordéon fermé n'existe pas pour `get_page_text` (il lit ce qui est affiché). Pour
  lire son contenu sans tout déplier à la main, prends le `textContent` de l'élément en
  JS. Le `textContent` de `document.body` entier, lui, aspire aussi le CSS et le JS des
  balises `<style>`/`<script>` : si une recherche y trouve un `--` ou un `:*`, vérifie
  l'élément parent avant de le reporter, ça peut être une variable CSS, pas du contenu.

## Passe 2, le fond

- **Promesse du lien.** La page d'arrivée doit tenir ce que le libellé annonçait, et
  apporter au moins autant que ce qui était déjà résumé au départ.
- **Promesse visible sans scroller.** Bonne page mais action promise noyée sous la ligne
  de flottaison : c'est un problème de parcours, moins grave qu'une mauvaise destination.
- **Routage par audience.** Un porteur de projet ne doit jamais atterrir sur du contenu
  écrit pour des investisseurs, ni l'inverse.
- **Chiffres.** Recoupe tout chiffre ou date avec le reste du site, la home faisant foi.
  Si un même bloc (footer, widget carte, module témoignages) revient sur plusieurs pages,
  compare-le d'une page à l'autre : ça dit si un souci est propre à cette page ou vient
  d'un composant partagé, et une seule correction règle alors tout le site d'un coup.
- **Hors sujet.** Un argument qui ne sert ni la compréhension ni la conversion à cet
  endroit précis, même s'il n'est faux nulle part.
- **Preuve sociale.** Un témoignage doit illustrer le problème que Feve a résolu, pas
  seulement l'activité de la personne.

## Rapport

Un point par ligne, chacun classé **haute**, **moyenne** ou **faible**, avec l'endroit
exact sur la page et une correction quand elle est simple. Termine par ce qui a été
vérifié et qui est bon. Ne corrige rien sans accord.
