# Feve — Claude Code plugins

Marketplace de **plugins Claude Code partagés** chez Feve. Une seule source de
vérité en git ; tout le monde dans la boîte reçoit les skills communs et leurs
mises à jour.

C'est le remplaçant propre de l'ancien système (symlinks `~/.claude/skills/` →
`dev-standards`) : versionné, multi-postes, sans bricolage manuel.

## Plugins disponibles

| Plugin | Pour qui | Ce que ça fait |
|---|---|---|
| **check-wording** | Communication, marketing, tout le monde | Relit un texte FR (email, post, page, copie) : orthographe, typo française, registre (tu/vous), ton. Demande le contexte d'abord, puis rapport priorisé. |

## Installation

Trois chemins selon l'outil utilisé. Le premier ne demande aucun terminal.

### 1. Sans terminal : Claude Chat et Cowork

Cowork et les sessions cloud ne lisent pas ce qui est installé sur ta machine :
ils chargent les skills et plugins **activés sur ton compte claude.ai**, resynchronisés
au démarrage de chaque session (ils apparaissent alors sous le nom `check-wording@synced`).

Ça se règle dans **Customize**, dans la barre latérale de l'app desktop Claude,
ou depuis les réglages de skills sur claude.ai. Un membre peut y déposer le plugin
pour lui seul ; pour le diffuser à toute l'équipe d'un coup, voir
[Diffusion à l'équipe](#diffusion-à-léquipe-team--enterprise) plus bas.

### 2. App desktop Claude, onglet Code

Bouton **+** à côté de la zone de saisie → **Plugins** → **Add plugin** : le navigateur
de plugins s'ouvre et liste les marketplaces configurés. **Manage plugins** sert à
activer, désactiver ou désinstaller. Aucune ligne de commande.

Ce navigateur n'existe pas dans les sessions cloud (voir le chemin 1 pour celles-là).

### 3. Claude Code en terminal

```bash
# 1. Ajouter le marketplace
/plugin marketplace add Fermes-En-ViE-FEVE/claude-plugins   # repo GitHub
#   ou en local pendant les tests :
/plugin marketplace add /chemin/vers/claude-plugins

# 2. Installer le plugin
/plugin install check-wording@feve
```

> Le `@feve` réfère au **nom du marketplace** (défini dans `marketplace.json`),
> pas au slug GitHub. C'est voulu : `add` prend le slug du repo, `install` le nom du marketplace.

Ensuite, le skill se déclenche tout seul quand c'est pertinent, ou s'invoque via
`/check-wording:check-wording`.

## Diffusion à l'équipe (Team / Enterprise)

Sur un plan Team ou Enterprise, un Owner distribue le plugin depuis
**[Organization settings → Plugins](https://claude.ai/admin-settings/plugins)** sur claude.ai.
Personne n'a alors de marketplace à gérer : le plugin arrive dans Chat et Cowork,
soit **installé par défaut**, soit **disponible à l'installation** dans le catalogue,
selon ce que l'admin choisit.

Deux façons de l'y mettre :

| Méthode | Contrainte |
|---|---|
| **Synchroniser ce marketplace** (repo GitHub) | Le repo doit être **privé ou interne**. Un repo public est refusé. La lecture se fait via la Claude GitHub App. |
| **Uploader le plugin en ZIP** | Aucune contrainte de visibilité. À refaire à chaque mise à jour. |

⚠️ Ce repo est actuellement **public** : la synchronisation de marketplace le refusera
tant qu'il n'est pas passé en privé. En attendant, l'upload ZIP fonctionne. Pour
fabriquer l'archive (contenu du dossier du plugin à la racine du ZIP, le format
que prend aussi `claude --plugin-dir`) :

```bash
cd plugins/check-wording && zip -r ../../check-wording.zip . -x '*__pycache__*' '*.DS_Store'
```

Autre règle de la distribution par organisation : pas de dossier `bin/` à la racine
d'un plugin (les exécutables vont dans `scripts/`, référencés via
`${CLAUDE_PLUGIN_ROOT}/scripts/<nom>`). C'est déjà le cas ici.

## Installation automatique par projet (repos de dev)

Pour qu'un coéquipier qui clone un repo ait le marketplace sans rien faire, ajoute ceci
au `.claude/settings.json` **du repo concerné** :

```json
{
  "extraKnownMarketplaces": {
    "feve": {
      "source": { "source": "github", "repo": "Fermes-En-ViE-FEVE/claude-plugins" }
    }
  },
  "enabledPlugins": {
    "check-wording@feve": true
  }
}
```

Une fois le dossier approuvé, Claude Code ajoute le marketplace sans demander. En
revanche, depuis la v2.1.195, il **n'installe pas** tout seul un plugin dont la source
est externe (un repo GitHub) : il le signale comme non installé et affiche la commande
à lancer, `claude plugin install check-wording@feve`. Le réglage évite donc l'étape
« ajouter le marketplace », pas l'installation.

## Mises à jour

Aucune `version` n'est déclarée dans les manifestes : c'est délibéré. Renseigner
`version` **épingle** le plugin, les utilisateurs ne recevant plus de mise à jour tant
qu'elle n'est pas incrémentée. Sans elle, chaque commit poussé ici fait une nouvelle
version. `claude plugin validate` émet un avertissement à ce sujet : il est attendu.

Si un jour on veut des versions figées, il faudra remettre `version` dans
`plugin.json`, la bumper à chaque release et taguer avec `claude plugin tag`.

- **Manuelle** : `/plugin marketplace update feve` puis `/reload-plugins`
  (`--force` si Claude Code prévient que le rechargement relit la conversation).
- **Auto** : activable par marketplace dans `/plugin` → **Marketplaces** →
  **Enable auto-update**. Désactivé par défaut sur les marketplaces tiers.

## Structure

```
claude-plugins/
├── .claude-plugin/
│   └── marketplace.json          ← catalogue des plugins
└── plugins/
    └── check-wording/
        ├── .claude-plugin/plugin.json
        └── skills/
            └── check-wording/
                ├── SKILL.md       ← instructions du skill
                ├── scripts/check-fr.py
                └── references/ton-de-voix-feve.md
```

Seul `plugin.json` vit dans `.claude-plugin/`. Tout le reste (`skills/`, `agents/`,
`hooks/`) est à la racine du plugin.

## Ajouter un plugin

1. Créer `plugins/<nom>/.claude-plugin/plugin.json` + `skills/<skill>/SKILL.md`.
2. Référencer le plugin dans `.claude-plugin/marketplace.json` (`source: "./plugins/<nom>"`).
3. Valider : `claude plugin validate ./plugins/<nom>` et `claude plugin validate .`.
4. Commit + push. `/plugin marketplace update feve` chez les utilisateurs.

## Audit wording automatique

Le dossier [`audit/`](audit/README.md) héberge le pendant non interactif du skill :
un cron GitHub Actions qui relit les pages publiques Feve et poste un rapport sur Slack.
