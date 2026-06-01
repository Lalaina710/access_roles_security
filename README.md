# Access Roles - Server Security (Odoo 18)

**Version : 18.0.1.2.0** — [Changelog complet](CHANGELOG.md)

Module compagnon de [Access Roles](https://apps.odoo.com/apps/modules/18.0/access_roles/) (Cybrosys) qui ajoute l'enforcement **côté serveur** des restrictions de rôles.

## Features

- Enforcement ORM des restrictions `access_roles` sur `create` / `write` / `unlink` (anti-bypass URL/RPC)
- Vérifications per-modèle (`is_model_readonly`), per-champ (`is_field_readonly`) et globales (`is_readonly`)
- Bypass automatique pour TransientModel (wizards), modèles critiques POS (`pos.order`, `account.move`, ...) et modèles infra Odoo (`bus.presence`, `res.users.settings`, ...)
- **Configurable writable models exceptions for read-only roles (UI-driven)** — onglet "Exceptions écriture" sur Role Management, voir [Usage](#exceptions-écriture)

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

## Comment ça marche concrètement

`access_roles` = la **configuration** (quoi bloquer, pour qui)
`access_roles_security` = le **verrou serveur** (empêche le contournement)

Les deux travaillent ensemble :

| | Sans `access_roles_security` | Avec `access_roles_security` |
|---|---|---|
| Bouton "Créer" caché | Caché dans l'UI, **URL `/new` fonctionne** | Caché dans l'UI **+ URL `/new` → AccessError** |
| Modèle en lecture seule | Champs grisés, **RPC `write()` passe** | Champs grisés **+ RPC `write()` → AccessError** |
| Champ prix en readonly | Grisé dans le formulaire, **modifiable via RPC** | Grisé **+ RPC sur ce champ → AccessError** |
| Suppression cachée | Bouton caché, **`unlink()` via RPC passe** | Bouton caché **+ `unlink()` → AccessError** |

**Vous ne changez rien dans votre configuration.** Vous continuez à tout configurer dans `access_roles` comme d'habitude. Le module `access_roles_security` lit ces mêmes règles et les applique au niveau du serveur Python automatiquement.

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

**Aucune configuration nécessaire** pour démarrer. Le module utilise directement les règles déjà définies dans **Access Role > Role Management** du module `access_roles`.

## Usage

### Exceptions écriture

À partir de la **v18.0.1.1.0**, lorsqu'un rôle a `is_readonly=True` (lecture seule globale), **tous les modèles** sont en lecture seule pour les utilisateurs assignés à ce rôle — sauf ceux explicitement listés en exception.

**Workflow** :

1. Ouvrir **Settings > Access Roles > Role Management** et sélectionner le rôle concerné (ex. `Controleur`).
2. Cocher `Make System ReadOnly` (`is_readonly=True`).
3. Un nouvel onglet **"Exceptions écriture"** apparaît dans le formulaire (visible uniquement si `is_readonly=True`).
4. Dans cet onglet, ajouter les modèles autorisés à l'édition via le widget Many2many tags (`writable_model_ids`).
5. Sauvegarder — les users de ce rôle peuvent désormais éditer ces modèles, le reste reste verrouillé.

**Exemple SOPROMER — rôle "Contrôleur de gestion"** :

- `is_readonly` coché → tout en lecture seule par défaut
- Exceptions cochées : `product.template`, `product.product`, `product.category`
- Résultat : les CdG peuvent éditer les fiches produits (prix, catégorie, fournisseur) **sans perdre la protection** sur le reste du système (factures, commandes, paiements, etc.)

> Les restrictions per-model (`is_model_readonly`) et per-field (`is_field_readonly`) configurées explicitement sur ces modèles **continuent de s'appliquer** — l'exception lève uniquement la lecture seule globale.

> Note : un screenshot de l'onglet "Exceptions écriture" pourra être ajouté ici ultérieurement.

## Migration / Upgrade notes

### System models bypass (v18.0.1.2.0)

À partir de la **v18.0.1.2.0**, une seconde liste de bypass inconditionnel
(`_SYSTEM_BYPASS_MODELS`) est appliquée AVANT le check `is_readonly`. Elle cible
les modèles techniques infrastructure d'Odoo écrits en arrière-plan par le
framework lui-même :

| Modèle | Rôle |
|--------|------|
| `bus.presence` | Heartbeat longpolling (ping ~30s pour suivre les users online) |
| `bus.presence.dispatcher` | Dispatcher du bus de présence (v18) |
| `res.users.settings` | Préférences UI utilisateur (sidebar discuss, etc.) |
| `res.users.settings.volumes` | Niveaux audio canal discuss (notifications) |
| `mail.notification` | Notifications mail / chatter par destinataire |
| `res.users.log` | Logs internes de connexion utilisateur |

**Pourquoi hardcodé et pas configurable via UI** :

- Ces modèles ne portent **aucune donnée métier** (heartbeat, prefs UI,
  logs techniques).
- Les writes sont déclenchés par le **runtime Odoo lui-même**, pas par une
  action utilisateur. Bloquer ces writes via `is_readonly=True` génère une
  popup "Erreur d'accès" à chaque navigation, **même sans action user**.
- L'administrateur n'a aucune raison légitime de vouloir bloquer ces écritures.
- Pattern miroir de `_POS_BYPASS_MODELS` (v18.0.1.0.1).

Les checks per-model (`is_model_readonly`) et per-field (`is_field_readonly`)
configurés explicitement sur ces modèles ne s'appliquent **plus** (bypass total).
En pratique, aucun admin ne configure ces modèles de toute façon.

### Upgrade vers v18.0.1.1.0 (depuis v18.0.1.0.3 ou antérieur) :

- Le script `migrations/18.0.1.1.0/post-migration.py` s'exécute automatiquement lors de l'upgrade et **pré-coche les 12 modèles `product.*`** sur tout rôle dont le nom contient `Controleur` (insensible à la casse).
- Objectif : préserver à l'identique le comportement de la whitelist hardcodée v18.0.1.0.3 sans régression pour les 8 utilisateurs CdG SOPROMER impactés.
- Migration **idempotente** : ré-exécutable sans risque, ignore les modèles non installés sur l'instance.
- Aucune perte de données : les configurations de rôles existantes restent intactes.
- Post-upgrade : vérifier que l'onglet "Exceptions écriture" est bien renseigné sur le rôle `Controleur` (12 entrées `product.*` attendues).

## Changelog (résumé)

Détail complet dans [CHANGELOG.md](CHANGELOG.md).

| Version | Date | Résumé |
|---------|------|--------|
| **18.0.1.2.0** | 2026-06-01 | fix — bypass modèles infra Odoo (bus.presence, res.users.settings, mail.notification, res.users.log) pour rôles `is_readonly` (résout popup "Erreur d'accès" sur navigation) |
| 18.0.1.1.0 | 2026-06-01 | feat — whitelist écriture configurable via UI (Many2many `writable_model_ids`) |
| 18.0.1.0.3 | 2026-06-01 | superseded by 1.1.0 (whitelist `product.*` hardcodée — abandonnée) |
| 18.0.1.0.2 | 2026-05-19 | fix — bypass TransientModel (wizards CdG débloqués) |
| 18.0.1.0.1 | 2026-05-12 | fix — bypass modèles critiques POS (incident P0 caissier) |
| 18.0.1.0.0 | — | Initial release |

## Dépendances

- `access_roles` (Cybrosys Techno Solutions)

## Licence

AGPL-3
