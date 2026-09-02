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

Personne n'a le même setup chez Feve (plans persos, Chat, Cowork, un ou deux
Claude Code). Prends la ligne qui correspond.

| Tu utilises | Ce que tu fais |
|---|---|
| Chat (web ou app) ou Cowork, plan payant | Ajouter ce marketplace dans **Customize**, puis installer. Rien à télécharger. |
| Chat sur un plan Free | Le ZIP du skill : les plugins demandent un plan payant, les skills non. |
| Claude Code en terminal | `/plugin marketplace add` puis `/plugin install`. |

### Chat et Cowork : ajouter le marketplace depuis Customize

Les plugins s'installent depuis l'interface, sans terminal et sans passer par un
catalogue Anthropic. Il suffit de brancher ce repo une fois :

1. Ouvrir **Customize** dans la barre latérale, onglet **Plugins**.
2. Dans la section **Personal plugins**, bouton **+** → **Add marketplace** →
   **Add from a repository**.
3. Coller `https://github.com/Fermes-En-ViE-FEVE/claude-plugins`.
4. **Browse plugins** → **Install** sur **check-wording**.

Le skill est ensuite disponible dans le chat web, dans l'onglet Chat de l'app desktop
et dans Cowork (les hooks et sous-agents, eux, ne tournent que dans Cowork ; ce plugin
n'en a pas). Comme c'est un marketplace, les mises à jour suivent les push sur `main` :
rien à refaire à chaque fois.

Plugins réservés aux plans payants (Pro, Max, Team, Enterprise). Sur un plan Free,
prendre le ZIP ci-dessous.

### Repli : déposer le ZIP du skill

Utile sur un plan Free, ou si on ne veut pas ajouter de marketplace. On perd les mises
à jour automatiques : il faut retélécharger à chaque évolution du skill.

1. Télécharger
   [`check-wording-skill.zip`](https://github.com/Fermes-En-ViE-FEVE/claude-plugins/releases/download/skill-latest/check-wording-skill.zip)
   (regénéré à chaque modification du skill).
2. Aller sur [claude.ai → Customize → Skills](https://claude.ai/customize/skills)
   et l'uploader.
3. Vérifier dans **Settings → Capabilities** que **Code execution and file creation**
   est activé : sans ça, les skills ne tournent pas du tout.

Pour refabriquer le ZIP à la main : `./scripts/package-skill.sh check-wording`.

### Claude Code en terminal

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

Dans l'onglet Code de l'app desktop, le même marketplace s'ajoute au bouton **+** →
**Plugins** → **Add plugin**.

### Si Feve passe un jour sur un plan Team ou Enterprise

Un Owner pourrait alors distribuer le plugin à tout le monde d'un coup depuis
**[Organization settings → Plugins](https://claude.ai/admin-settings/plugins)** :
plus personne n'aurait de ZIP à télécharger, le skill arriverait installé par défaut
dans Chat et Cowork. Deux réserves : la synchronisation de marketplace exige un repo
**privé ou interne** (celui-ci est public, il faudrait le basculer) ou un upload de ZIP
du plugin, et un plugin distribué par organisation ne doit pas avoir de dossier `bin/`
à sa racine (ce n'est pas le cas ici).

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

Selon le chemin d'installation :

- **Marketplace ajouté dans Customize** (Chat, Cowork) : rien à faire, la
  synchronisation suit les push sur `main`.
- **Claude Code** : `/plugin marketplace update feve` puis `/reload-plugins`
  (`--force` si Claude Code prévient que le rechargement relit la conversation).
  L'auto-update s'active par marketplace dans `/plugin` → **Marketplaces** →
  **Enable auto-update** ; il est désactivé par défaut sur les marketplaces tiers.
- **ZIP du skill** : aucune mise à jour automatique, il faut retélécharger.

## Structure

```
claude-plugins/
├── .claude-plugin/
│   └── marketplace.json          ← catalogue des plugins
├── plugins/
│   └── check-wording/
│       ├── .claude-plugin/plugin.json
│       └── skills/
│           └── check-wording/
│               ├── SKILL.md       ← instructions du skill
│               ├── scripts/check-fr.py
│               └── references/ton-de-voix-feve.md
├── scripts/package-skill.sh      ← fabrique le ZIP pour claude.ai
├── audit/                        ← audit wording périodique (voir plus bas)
└── .github/workflows/
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
