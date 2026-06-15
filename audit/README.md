# Audit wording (POC)

Audit **automatique et périodique** du wording sur les pages publiques Feve.
C'est le pendant non-interactif du skill `check-wording` : au lieu qu'un humain
colle un texte, un cron va chercher les pages tout seul et poste un rapport sur Slack.

## Comment ça marche

```
cron GitHub Actions  →  récupère les pages  →  LanguageTool (ortho/typo, objectif)
                                            →  OpenRouter/Claude (juge le TON, charte = barème)
                                            →  delta vs run précédent  →  rapport Slack
```

GitHub Actions ne « comprend » pas le ton : il n'est que le déclencheur. Le jugement
du ton vient de l'appel LLM dans [`audit.py`](audit.py), qui charge la charte
`plugins/check-wording/.../ton-de-voix-feve.md` comme barème.

## Pages auditées

Définies dans [`pages.json`](pages.json). **Le `registre` (tu/vous) est par page** —
c'est lui qui remplace la question interactive du skill. ⚠️ Les valeurs actuelles
(`tu` partout) sont une supposition pour le POC, **à confirmer**.

## Lancer en local

```bash
cp audit/.env.local.example audit/.env.local   # puis renseigne ta clé dedans (gitignore)
python3 audit/audit.py --dry-run               # imprime le rapport au lieu de poster sur Slack
```

Sans `LANGUAGETOOL_URL`, le script tape l'API publique LanguageTool (rate-limité
~20 req/min) — suffisant pour quelques pages en test.

## En CI (GitHub Actions)

Workflow : [`.github/workflows/audit-wording.yml`](../.github/workflows/audit-wording.yml).
Cron hebdo (lundi 8h UTC) + bouton **Run workflow** pour tester à la demande.

À configurer dans **Settings → Secrets and variables → Actions** du repo :

| Type     | Nom                  | Valeur                                          |
| -------- | -------------------- | ----------------------------------------------- |
| Secret   | `OPENROUTER_API_KEY` | ton token OpenRouter                            |
| Secret   | `SLACK_DSN`          | DSN bot Slack `slack://TOKEN@default?channel=…` (réutilise celui de lagrange) |
| Variable | `SLACK_CHANNEL`      | canal cible (ex. `test-automatisation`) ; override le canal du DSN |
| Variable | `OPENROUTER_MODEL`   | (optionnel) slug du modèle ; défaut `anthropic/claude-sonnet-4.6` |

> Alternative à `SLACK_DSN` : une Incoming Webhook dans `SLACK_WEBHOOK_URL` (prioritaire si définie).
> Le bot doit être **membre du canal** (`/invite @bot`) sinon `chat.postMessage` renvoie `not_in_channel`.

LanguageTool tourne en service container (pas de rate-limit). Le delta entre deux
runs s'appuie sur `actions/cache` (best-effort : si le cache expire, le run signale tout).

## Limites connues (POC) → pistes v2

- **Delta via cache** = best-effort. Pour un delta robuste : committer `audit/.state`
  dans le repo, ou stocker l'état ailleurs (gist, S3, DB).
- **Pages déconnectées uniquement.** Auditer des pages derrière login = ajouter une
  étape d'auth (cookie/token) au fetch.
- **Pas un gate.** Le jugement de ton n'est pas déterministe : c'est un rapport pour
  relecture humaine, jamais un blocage de déploiement.
