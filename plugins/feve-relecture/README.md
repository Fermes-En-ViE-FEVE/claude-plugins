# Feve Relecture

Relit une communication écrite en français avant envoi : orthographe et grammaire
(LanguageTool), typographie française (espaces insécables, guillemets, apostrophes),
cohérence du registre tu/vous, et ton selon la charte Feve.

Le registre et le ton ne sont jamais présumés (ils varient d'un applicatif à l'autre) :
le skill demande le contexte, rend un rapport priorisé, et ne corrige rien sans accord.

S'invoque via `/feve-relecture:relecture`, ou se déclenche seul quand on demande une
relecture. Nécessite Python 3 et un accès réseau pour la passe LanguageTool ; sans eux,
la typographie et le ton restent analysés.

La charte de ton vit dans
[`skills/relecture/references/ton-de-voix-feve.md`](skills/relecture/references/ton-de-voix-feve.md) :
la modifier ici et pousser suffit à mettre toute l'équipe à jour.
