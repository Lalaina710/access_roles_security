# Access Roles - Server Security (Odoo 18)

Module compagnon de [Access Roles](https://apps.odoo.com/apps/modules/18.0/access_roles/) (Cybrosys) qui ajoute l'enforcement **côté serveur** des restrictions de rôles.

## Problème

Le module `access_roles` applique ses restrictions **uniquement au niveau UI** :
- Boutons cachés via XML (`invisible="True"`)
- Champs readonly/invisible via modification de vue
- Menus masqués, export désactivé via JS

**Tout cela est contournable** en collant une URL directe, en utilisant la console développeur, ou via des appels RPC/API.

## Solution

Ce module intercepte les opérations ORM (`create`, `write`, `unlink`) sur **tous les modèles** et vérifie les restrictions configurées dans `access_roles` avant d'autoriser l'opération.

| Opération | Restriction vérifiée | Résultat |
|-----------|---------------------|----------|
| `create()` | `is_hide_create` sur le modèle | `AccessError` |
| `unlink()` | `is_hide_delete` sur le modèle | `AccessError` |
| `write()` | `is_readonly` (global) | `AccessError` |
| `write()` | `is_model_readonly` sur le modèle | `AccessError` |
| `write()` | `is_field_readonly` sur des champs | `AccessError` sur les champs bloqués |

## Exemptions automatiques

Les vérifications sont ignorées pour :
- **Root / SUPERUSER_ID** : l'administrateur système n'est jamais bloqué
- **Opérations `sudo()`** : crons, workflows, actions automatiques fonctionnent normalement
- **Utilisateurs sans rôle** : aucun impact si pas de rôle assigné

## Installation

1. Copier le dossier `access_roles_security` dans votre répertoire d'addons
2. Redémarrer Odoo : `python odoo-bin --addons-path=addons,third-party-addons -d votre_base -u base`
3. Aller dans **Apps** > chercher **"Access Roles - Server Security"** > **Installer**

## Configuration

**Aucune configuration nécessaire.** Le module utilise directement les règles déjà définies dans **Access Role > Role Management** du module `access_roles`.

## Dépendances

- `access_roles` (Cybrosys Techno Solutions)

## Licence

AGPL-3
