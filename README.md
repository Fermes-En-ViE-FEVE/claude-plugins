# Feve, plugins Claude Code

Marketplace des plugins partagés chez Feve. Une source de vérité en git, tout le
monde reçoit les skills communs et leurs mises à jour.

| Plugin | Ce que ça fait |
|---|---|
| **Feve Relecture** | Relit un texte français : fautes, cohérence du tutoiement/vouvoiement, et tics d'écriture qui font « écrit par une IA ». Ne corrige rien sans accord. |

## Installer

**Chat ou Cowork.** Depuis **claude.ai dans le navigateur** (l'app desktop échoue) :
**Personnaliser** → onglet **Plugins** → **Ajouter** → depuis un dépôt, avec
`Fermes-En-ViE-FEVE/claude-plugins`. Puis **Découvrir** → **Installer**.

**Claude Code.**

```bash
/plugin marketplace add Fermes-En-ViE-FEVE/claude-plugins
/plugin install feve-relecture@feve
```

**Plan Free.** Les plugins demandent un plan payant, pas les skills : déposer
[le ZIP du skill](https://github.com/Fermes-En-ViE-FEVE/claude-plugins/releases/download/skill-latest/feve-relecture-skill.zip)
dans [Customize → Skills](https://claude.ai/customize/skills), après avoir activé
**Code execution and file creation** dans Settings → Capabilities.

## Mettre à jour

Les manifestes ne déclarent pas de `version` : renseignée, elle épinglerait le
plugin jusqu'au prochain bump. Chaque push sur `main` fait donc une nouvelle version.

- **Marketplace (Chat, Cowork)** : coche la mise à jour automatique proposée à
  l'ajout du marketplace, et il n'y a plus rien à faire. Sinon, passe par le menu
  du marketplace dans Personnaliser pour le resynchroniser à la main.
- **Claude Code** : `/plugin marketplace update feve` puis `/reload-plugins`.
  L'auto-update s'active par marketplace dans `/plugin`, onglet Marketplaces.
- **ZIP** (repli plan Free uniquement) : rien ne se met à jour tout seul, un
  fichier déposé n'a pas de source à surveiller. Il faut le retélécharger.

## Ajouter un plugin

1. Créer `plugins/<nom>/.claude-plugin/plugin.json` et `skills/<skill>/SKILL.md`.
   Seul `plugin.json` vit dans `.claude-plugin/`, le reste est à la racine du plugin.
2. Ajouter l'entrée dans `.claude-plugin/marketplace.json`. Un renommage passe par
   la map `renames`, sinon les installs existantes cassent.
3. `claude plugin validate .`, puis commit et push.

`./scripts/package-skill.sh` refabrique le ZIP d'un skill pour claude.ai.
