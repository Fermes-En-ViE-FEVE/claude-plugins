# Repères feve.co

Alimenté par `audit-page` d'une review à l'autre. Que des faits vérifiés à une date
donnée, pas de commentaire. Si un repère est mis en doute par un audit suivant,
corriger la ligne plutôt que la dupliquer.

## Mécanismes

- **Chiffres d'impact** (fermes financées, hectares, montant collecté, investisseurs) :
  `legrenier.feve.co/metrics` répond en JSON, un script sur chaque page cherche
  `.metric-<clé>` (classe exacte, insensible à la casse) et y écrit la valeur. Un
  chiffre qui ne bouge jamais est soit une classe mutée (élément dupliqué dans
  l'éditeur Webflow, ex. `metric-totalfarms-1-2`), soit un chiffre tapé en dur dans une
  phrase, jamais branché à ce système. Les deux se corrigent différemment : renommer la
  classe pour l'un, remplacer le texte par la vignette gérée pour l'autre.
- **Footer global** : le lien « Mon espace - Le Grenier » a été vu cassé (`href="#"`,
  aucun gestionnaire) sur plusieurs pages simultanément le 02-03/09/2026 : un bug de
  composant partagé, pas un souci page par page.

## Blocs de contenu réutilisés

- « Des fermages perçus [...] réinvestis – entre 1% et 1.5% [...] » : identique sur
  /investir/cadeau, /investir/offrir-des-actions-feve,
  /investir/offrir-un-cadeau-d-entreprise. Contient un tiret demi-cadratin en
  séparateur (tic d'écriture IA).
- FAQ « critères de financement des fermes » et « critères de sélection des porteurs
  ou porteuses de projet » : bloc réutilisé mot pour mot entre
  /installation/je-finance-ma-ferme et /installation/sessions-d-information.
- Widget carte des fermes (« Explorez [...] Cliquez sur celles qui vous intéressent ») :
  vu en tutoiement complet sur /installation-agricole (03/09/2026) alors que la même
  version sur home et /investir/impact vouvoie correctement. Un bug page par page,
  pas de composant.

## Historique des audits

| Date | Pages | Points (Haute/Moyenne/Faible) | Notes |
|---|---|---|---|
| 2026-09-03 | 32 (feve-relecture:audit-page) | voir `audit-feve-pages-statiques.md` | Pages statiques principales hors collections |
