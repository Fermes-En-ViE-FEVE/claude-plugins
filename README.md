# Feve — Claude Code plugins

Marketplace de **plugins Claude Code partagés** chez Feve. Une seule source de
vérité en git ; tout le monde dans la boîte ajoute ce marketplace une fois, et
reçoit ensuite les skills communs + leurs mises à jour automatiquement.

C'est le remplaçant propre de l'ancien système (symlinks `~/.claude/skills/` →
`dev-standards`) : versionné, multi-postes, sans bricolage manuel.

## Plugins disponibles

| Plugin | Pour qui | Ce que ça fait |
|---|---|---|
| **check-wording** | Communication, marketing, tout le monde | Relit un texte FR (email, post, page, copie) : orthographe, typo française, registre (tu/vous), ton. Demande le contexte d'abord, puis rapport priorisé. |

## Installation (chaque personne, une fois)

```bash
# 1. Ajouter le marketplace
/plugin marketplace add Fermes-En-ViE-FEVE/claude-plugins   # repo GitHub
#   ou en local pendant les tests :
/plugin marketplace add /chemin/vers/claude-plugins

# 2. Installer le(s) plugin(s)
/plugin install check-wording@feve
```

> Le `@feve` réfère au **nom du marketplace** (défini dans `marketplace.json`),
> pas au slug GitHub. C'est voulu : `add` prend le slug du repo, `install` le nom du marketplace.

Ensuite, le skill se déclenche tout seul quand c'est pertinent, ou s'invoque via
`/check-wording:check-wording`.

## Installation automatique par projet (recommandé pour une équipe)

Pour qu'un coéquipier qui clone un repo ait le plugin sans rien faire, ajoute ceci
au `.claude/settings.json` **du repo concerné** :

```json
{
  "extraKnownMarketplaces": {
    "feve": {
      "source": { "source": "github", "repo": "Fermes-En-ViE-FEVE/claude-plugins" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "check-wording@feve": "installed"
  }
}
```

Au prochain ouverture du projet (workspace de confiance), Claude Code propose
d'installer le marketplace + le plugin.

## Mises à jour

- **Manuelle** : `/plugin marketplace update feve` puis `/reload-plugins`.
- **Auto** : `autoUpdate: true` (ci-dessus) → re-tiré à chaque session.

Comme tout est dans ce repo git, améliorer un skill = éditer + commit + push ici.
Toute l'équipe a la nouvelle version à la session suivante.

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

## Ajouter un plugin

1. Créer `plugins/<nom>/.claude-plugin/plugin.json` + `skills/<skill>/SKILL.md`.
2. Référencer le plugin dans `.claude-plugin/marketplace.json` (`source: "./plugins/<nom>"`).
3. Commit + push. `/plugin marketplace update feve` chez les utilisateurs.
