# Feve — plugins Claude Code

Marketplace des plugins partagés chez Feve. Une source de vérité en git, tout le
monde reçoit les skills communs et leurs mises à jour.

| Plugin | Ce que ça fait |
|---|---|
| **Feve Relecture** | Relit un texte français (email, post, page, copie) : orthographe, typographie, registre tu/vous, ton. Demande le contexte, puis rend un rapport priorisé. |

## Installer

**Chat ou Cowork.** Customize → onglet **Plugins** → **+** → **Add marketplace** →
**Add from a repository**, avec `https://github.com/Fermes-En-ViE-FEVE/claude-plugins`.
Puis **Browse plugins** → **Install**.

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

- Marketplace ajouté dans Customize : rien à faire.
- Claude Code : `/plugin marketplace update feve` puis `/reload-plugins`.
- ZIP : retélécharger.

## Ajouter un plugin

1. Créer `plugins/<nom>/.claude-plugin/plugin.json` et `skills/<skill>/SKILL.md`.
   Seul `plugin.json` vit dans `.claude-plugin/`, le reste est à la racine du plugin.
2. Ajouter l'entrée dans `.claude-plugin/marketplace.json`. Un renommage passe par
   la map `renames`, sinon les installs existantes cassent.
3. `claude plugin validate .`, puis commit et push.

`./scripts/package-skill.sh` refabrique le ZIP d'un skill pour claude.ai.

## Audit wording

[`audit/`](audit/README.md) : le pendant non interactif du skill, un cron GitHub
Actions qui relit les pages publiques Feve et poste un rapport sur Slack.
