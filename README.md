# Access Roles - Server Security

![Version](https://img.shields.io/badge/version-18.0.1.2.0-blue) ![License](https://img.shields.io/badge/license-AGPL--3-green) ![Odoo](https://img.shields.io/badge/Odoo-18.0%20Community-purple)

Companion module for [Access Roles](https://apps.odoo.com/apps/modules/18.0/access_roles/) (Cybrosys Techno Solutions). See [CHANGELOG.md](CHANGELOG.md) for full version history.

## Overview

Server-side ORM enforcement extension for the `access_roles` module. Prevents privilege escalation via URL or RPC bypass and resolves common false-positive blocks introduced by roles flagged as `is_readonly=True`. The original `access_roles` module restricts the UI only; this extension intercepts `create` / `write` / `unlink` at the ORM layer so the restrictions hold across every entry point (web, RPC, scripts, automated actions).

## Problem statement

The third-party `access_roles` module enforces restrictions **at the UI level only**:

- Buttons hidden via XML (`invisible="True"`)
- Fields rendered read-only via dynamic view tweaks
- Menus masked and export disabled via JavaScript

All of these are bypassable by crafting a direct URL, using the developer console, or issuing raw RPC/API calls. `access_roles_security` closes that gap.

A second problem appears once `access_roles` is fully enforced server-side: a role flagged `is_readonly=True` (system-wide read-only access) ends up blocking even **harmless technical writes** — user heartbeat, UI preferences, wizard scratch data, automated POS state transitions — which produces intrusive "Access Error" popups during regular navigation. `access_roles_security` ships intelligent bypass layers to preserve the security intent while removing these false positives.

## Solution

The module intercepts ORM operations on **every model** and checks the restrictions configured in `access_roles` before letting the operation through.

| Operation | Restriction checked      | Outcome on violation         |
| --------- | ------------------------ | ---------------------------- |
| `create()`| `is_hide_create`         | `AccessError`                |
| `unlink()`| `is_hide_delete`         | `AccessError`                |
| `write()` | `is_readonly` (global)   | `AccessError`                |
| `write()` | `is_model_readonly`      | `AccessError`                |
| `write()` | `is_field_readonly`      | `AccessError` on the field   |

You do not change anything in your `access_roles` configuration. You keep declaring rules in **Settings > Access Roles > Role Management** as usual; this module reads the same rules and applies them at the Python server layer automatically.

### UI-only vs. UI + server enforcement

| | Without `access_roles_security` | With `access_roles_security` |
|---|---|---|
| "Create" button hidden | Hidden in UI, **URL `/new` still works** | Hidden in UI **+ URL `/new` → `AccessError`** |
| Read-only model | Fields greyed, **RPC `write()` passes** | Fields greyed **+ RPC `write()` → `AccessError`** |
| Read-only price field | Greyed in form, **mutable via RPC** | Greyed **+ RPC on that field → `AccessError`** |
| Hidden delete | Button hidden, **`unlink()` via RPC passes** | Button hidden **+ `unlink()` → `AccessError`** |

## Features

- ORM enforcement of `access_roles` restrictions on `create` / `write` / `unlink` (anti-bypass for URL / RPC entry points)
- Per-model (`is_model_readonly`), per-field (`is_field_readonly`), and global (`is_readonly`) checks
- Automatic bypass for `TransientModel` (wizards), POS-critical business models, and Odoo infrastructure models
- **UI-configurable writable exceptions** per role — Many2many `writable_model_ids` on `role.management`, no code change required
- Root / `SUPERUSER_ID` and `sudo()` operations always pass through (crons, automated actions, server-side workflows unaffected)
- Users without any role assigned are unaffected

## Architecture: bypass order

The interception logic evaluates layers in this order. The first matching layer short-circuits the check.

| Layer | Bypass type | Configurable | When applied |
| ----- | ----------- | ------------ | ------------ |
| Root / `SUPERUSER_ID` / `sudo()` | Automatic | No | Any operation by the superuser or in `sudo` context |
| `TransientModel` | Automatic | No (hardcoded) | All wizards (`_transient = True`) |
| POS critical models | Automatic | No (hardcoded) | List of 13 POS workflow models |
| System infrastructure models | Automatic | No (hardcoded) | List of 6 Odoo runtime models |
| Writable exceptions | User-defined | Yes (UI) | Per `role.management` via `writable_model_ids` |
| `is_readonly` global | Enforced | — | Falls through if no bypass above matched |
| `is_model_readonly` per model | Enforced | Yes (Field Access list) | After all bypass checks |
| `is_field_readonly` per field | Enforced | Yes (Field Access list) | After all bypass checks |

## Installation

This module depends on the third-party `access_roles` module; install that one first.

1. Copy the `access_roles_security` folder into your Odoo addons path
2. Restart Odoo: `python odoo-bin --addons-path=addons,third-party-addons -d <your_db> -u base`
3. Go to **Apps**, search for **"Access Roles - Server Security"**, and click **Install**

No further configuration is required to start enforcing the existing rules.

## Usage

### Configuring writable exceptions

When a role has `is_readonly=True`, every model becomes read-only for the users assigned to that role — except for the ones explicitly listed as exceptions.

**Workflow:**

1. Open **Settings > Access Roles > Role Management** and pick the role.
2. Tick **Make System ReadOnly** (`is_readonly=True`).
3. A new notebook tab **"Exceptions écriture"** appears on the form (visible only when `is_readonly` is on).
4. In that tab, add the writable models via the Many2many tags widget (`writable_model_ids`).
5. Save — users assigned to that role can now edit those specific models; everything else stays locked.

**Example.** A controller / management-control role needs to maintain the product catalogue (price, category, supplier) but must stay read-only on everything else (invoices, orders, payments, accounting, etc.). Add `product.template`, `product.product`, `product.category` to the exceptions list. Per-model and per-field restrictions configured explicitly on these models (`is_model_readonly`, `is_field_readonly`) keep applying — the exception only lifts the global read-only switch.

## Bypass model lists (reference)

The following bypass lists are hardcoded by design. They cover technical models that either do not carry business data, or are written by the Odoo framework itself in the background. Exposing them in the UI would only invite misconfiguration.

### `_POS_BYPASS_MODELS` — Point of Sale workflow (13 models)

Introduced in v18.0.1.0.1 after a P0 incident where a cashier role with `is_readonly` semantics was blocked at the `pos.order` state transition `draft → paid → done`. POS sessions interleave write operations across orders, payments, stock moves, and journal entries; blocking any single step corrupts the session.

| Model | Why it is bypassed |
| ----- | ------------------ |
| `pos.order` | POS order header, state transitions during checkout |
| `pos.order.line` | Order lines written as the cart is built |
| `pos.payment` | Payment registration on order validation |
| `pos.session` | Session open / close lifecycle |
| `stock.picking` | Outbound picking generated on session validation |
| `stock.move` | Stock moves linked to picking |
| `stock.move.line` | Lot / serial assignment on stock moves |
| `stock.quant` | Quant recomputation after move processing |
| `account.move` | Invoices generated for paid orders flagged as invoiced |
| `account.move.line` | Journal items on invoice / closing entry |
| `account.bank.statement` | Cash control entries on session close |
| `account.bank.statement.line` | Statement line creation per payment method |
| `account.payment` | Linked payment record for invoiced orders |

Security is preserved by the native ACLs, record rules, and complementary modules (e.g. `sensible_pos_access_rights_employee`, `access_roles` UI hiding). Cashiers cannot reach these models from the UI; the bypass only covers the automatic ORM writes triggered by the POS workflow itself.

### `_SYSTEM_BYPASS_MODELS` — Odoo infrastructure (6 models)

Introduced in v18.0.1.2.0 to suppress the "Access Error" popup triggered by Odoo background writes during regular navigation.

| Model | Why it is bypassed |
| ----- | ------------------ |
| `bus.presence` | User heartbeat for real-time notifications, written every ~30 s by longpolling |
| `bus.presence.dispatcher` | Dispatcher of the presence bus (v18) |
| `res.users.settings` | Per-user UI preferences (Discuss sidebar, OWL settings) |
| `res.users.settings.volumes` | Audio volume levels per Discuss channel |
| `mail.notification` | Mail / chatter notifications per recipient |
| `res.users.log` | Internal login / connection logs |

These models hold no business data, and the writes are issued by the runtime, not by a user action. Blocking them produces an error popup on every page load.

### `TransientModel` bypass

All transient models (wizards) are bypassed in `create` / `write` / `unlink`. Wizards are session-scoped scratch data, garbage-collected after ~60 minutes; they do not persist business state. The downstream actions launched by a wizard still go through their target models (`stock.move`, `account.move`, etc.), where the ACLs, record rules, and role restrictions apply normally.

This bypass was introduced in v18.0.1.0.2 after read-only roles were found unable to launch any reporting wizard, because every wizard writes its own state and binary result back onto itself.

## Migration notes

### Upgrade to v18.0.1.1.0 (from v18.0.1.0.3 or earlier)

The script `migrations/18.0.1.1.0/post-migration.py` runs automatically on upgrade and **pre-populates the 12 `product.*` models** on any role whose name contains `Controleur` (case-insensitive). This preserves the behaviour of the v18.0.1.0.3 hardcoded whitelist, which has been removed in favour of the UI-managed `writable_model_ids` field.

- Instances without any role named `Controleur` are skipped silently — no impact.
- The migration is idempotent and ignores models not installed on the instance.
- No data loss: existing role configurations are untouched.
- Post-upgrade: open the role form, **Exceptions écriture** tab, and verify that the expected `product.*` entries are present.

If your deployment uses a different naming convention for management-control roles, you can either rename the role to include `Controleur` before the upgrade, or simply tick the desired models manually in the new tab after upgrade.

## Changelog summary

Full detail in [CHANGELOG.md](CHANGELOG.md).

| Version | Date | Summary |
| ------- | ---- | ------- |
| **18.0.1.2.0** | 2026-06-01 | fix — bypass for Odoo infra models (`bus.presence`, `res.users.settings`, `mail.notification`, `res.users.log`, ...) under `is_readonly` roles, removes spurious "Access Error" popups on navigation |
| 18.0.1.1.0 | 2026-06-01 | feat — UI-configurable writable exception list (`writable_model_ids` Many2many on `role.management`) |
| 18.0.1.0.3 | 2026-06-01 | superseded by 1.1.0 (hardcoded `product.*` whitelist — replaced by configurable list) |
| 18.0.1.0.2 | 2026-05-19 | fix — bypass `TransientModel` (unblocks wizards under read-only roles) |
| 18.0.1.0.1 | 2026-05-12 | fix — bypass POS-critical models to prevent workflow blocking |
| 18.0.1.0.0 | — | Initial release |

## Compatibility

- Odoo 18.0 Community
- Third-party module `access_roles` (Cybrosys Techno Solutions) — required dependency

## Dependencies

- `access_roles` (Cybrosys Techno Solutions)

## License

AGPL-3

## Author / Contributors

Custom
