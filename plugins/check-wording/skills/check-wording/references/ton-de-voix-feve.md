# Ton de voix Feve — règles transverses (embarquées)

Ces principes s'appliquent à **toute communication écrite Feve**, quel que soit
l'applicatif ou le canal (landing, email, post, doc produit, in-app). Le
**registre** (tutoiement / vouvoiement) et le **ton précis** varient selon le
produit et l'audience : ils sont **fournis par l'utilisateur au lancement du
skill**, ils ne sont PAS figés ici.

> ℹ️ Pour les landing pages spécifiquement, des chartes par audience existent dans
> le repo `landings` (`docs/charte-porteurs.md`, `docs/charte-investisseurs.md`).
> Ce fichier-ci est la version transverse, valable partout.

---

## 1. Registre : à confirmer à chaque fois

Feve a plusieurs applicatifs : sur certains on **tutoie**, sur d'autres on
**vouvoie**. Le skill demande le registre cible avant d'analyser.

Une fois le registre choisi, la règle est la **cohérence absolue** :
- Pas de mélange tu/vous dans un même texte (le signal `registre.mixte` du script
  le détecte objectivement).
- Marque toujours désignée par `nous` / `Feve` (pas `on`, pas `notre équipe`).

**Interdits transverses de registre** :
- `on` à la place de `nous` (sauf appartenance collective rare : « on est là pour vous »).
- `notre équipe` → préférer `nous` ou `Feve`.
- `cher·e client·e`, `Madame, Monsieur` → jamais. On tutoie ou on vouvoie, pas de
  formules notariales.

## 2. Philosophie

> **Concret > abstrait. Preuve > promesse. Sobriété > superlatif.**

1. **Un chiffre vaut mieux qu'un adjectif.**
   - ❌ « Une plateforme leader de l'investissement vert »
   - ✅ « 50 fermes financées, 2 000 hectares préservés depuis 2020 »
2. **Une preuve vaut mieux qu'une promesse.**
   - ❌ « Investissez en toute confiance »
   - ✅ « Labellisé Finansol et agréé ESUS par l'État »
3. **Une phrase courte vaut mieux qu'une longue.** Vise 15-20 mots par phrase.

## 3. Vocabulaire — bannir / préférer

| À bannir | Pourquoi | Préférer |
|---|---|---|
| *Solution* (seul, sans contexte) | Buzzword corporate creux | *Modèle*, *dispositif*, *parcours*, *outil* |
| *Innovant·e*, *révolutionnaire* | Promesse vide | *Inédit chez nous depuis…* + preuve |
| *Démocratiser* | Surutilisé en greenwashing | *Rendre accessible à partir de 500 €* |
| *Engagement* (sans contenu) | Mot-valise | Décrire l'action concrète |
| *Authentique* (pour les agri) | Cliché | Décrire ce qui rend la ferme spécifique |
| *Premium*, *exclusif* | Mauvais positionnement Feve | (rien) |

## 4. Typographie française (vérifiée par le script)

- **Espace insécable** avant `?` `!` `;` `:` `»` et après `«`. Caractère : ` ` (Option+Espace sur Mac).
- **Guillemets français** : `« »` (jamais `"` ni `''`).
- **Apostrophe courbe** : `’` (jamais `'`).
- **Tiret cadratin** pour les incises : `—` (jamais `--`).
- **Ligatures** : *cœur*, *œuvre*, *vœu* (jamais *coeur*).
- **Majuscules accentuées** : *À*, *É*, *Î* (jamais *A*, *E*, *I* en début de mot accentué).
- Pas de point final dans un titre ou une bullet (sauf phrase complète).

## 5. Listes à puces

- **Mêmes structures grammaticales** dans une liste (parallélisme).
  - ✅ Tous en verbe : *Investir / Suivre / Récupérer*
  - ❌ Mélange : *Investir / Un suivi / Récupérer*
- 3-5 puces idéalement.

## 6. Inclusivité

- Préférer les formulations neutres : *les personnes installées*, *l'équipe*.
- Éviter les formes lourdes qui cassent la lecture : *les agriculteur·rice·s qui sont
  installé·e·s*. Préférer *les agriculteur·rices installé·es*.
- Le point médian est OK pour les mots courts (*chargé·e*, *installé·es*). Au-delà, reformuler.

## 7. Anglicismes

Préférer le français quand l'équivalent existe et est compris :
*landing page* → *page de campagne* ; *call-to-action* → *appel à l'action* ;
*pitch* → *présentation* ; *insight* → *constat*.
On garde : *agroécologie*, *bio*, *podcast*, *webinaire*.

## 8. Faux positifs à ne JAMAIS corriger

- **FEVE / Feve** : nom de la marque. LanguageTool suggère parfois *fève* / *fête* /
  *rêve* — ignorer systématiquement.
- **Noms de produits Feve** (Le Grenier, Prix des fermes, etc.) : ne pas corriger.
- Titres délibérément en minuscule (parti pris éditorial) : ne pas forcer la majuscule.

---

*Source de vérité : ce fichier vit dans le plugin `check-wording` du marketplace Feve.
Toute évolution du ton de voix transverse se fait ici, puis est rediffusée
automatiquement à toute l'équipe via la mise à jour du marketplace.*
