# Changelog

All notable changes to `access_roles_security` are documented here.

This module follows [Semantic Versioning](https://semver.org/) with the Odoo
prefix convention `18.0.X.Y.Z`.

## 18.0.1.1.0 (2026-06-01)

- feat: configurable writable models exceptions for read-only roles (UI-driven)
- New Many2many field `writable_model_ids` on `role.management`, exposed in
  the form view via a new notebook page **"Exceptions écriture"** (visible
  only when `is_readonly=True`).
- Admins can now manage the exception list from the UI — no code change
  needed each time a new model must be writable for a read-only role.
- Migration `migrations/18.0.1.1.0/post-migration.py` automatically
  pre-ticks the 12 product.* models on the `Controleur` role (CdG SOPROMER)
  to preserve the v18.0.1.0.3 behavior with zero regression. Idempotent and
  skips models not installed on the instance.

**Migration notes**
- No data loss: existing role configurations untouched.
- After upgrade: open *Settings → Access Roles → Role Management → Controleur*,
  check the **Exceptions écriture** tab — 12 product.* models should appear.
- To add/remove exceptions: edit the Many2many tags directly (no code).

## 18.0.1.0.3 (2026-06-01) — SUPERSEDED by 18.0.1.1.0

- fix: whitelist product.* models for write/create even when role is_readonly=True
- Resolves AccessError blocking CdG controllers from editing products (8 users impacted)

Whitelisted models: `product.template`, `product.product`, `product.category`,
`product.pricelist`, `product.pricelist.item`, `product.attribute`,
`product.attribute.value`, `product.template.attribute.line`,
`product.template.attribute.value`, `product.supplierinfo`,
`product.packaging`, `product.tag`.

Per-model (`is_model_readonly`) and per-field (`is_field_readonly`)
restrictions configured explicitly on these product models continue to apply.

**Superseded**: the hardcoded whitelist approach has been replaced in
v18.0.1.1.0 by a configurable Many2many field (`writable_model_ids`) on
`role.management`, manageable via the UI without code changes.

Diagnostic source: `sopromer-rapports/05_securite_acces/diag_controller_product_edit_45_20260601.html`.

## 18.0.1.0.2 (2026-05-19)

- fix: bypass TransientModel (wizards) in create/write/unlink to unblock
  users with is_readonly roles (ex. CdG Controleur) on report wizards
  (stock_movement_report, sale_invoice_report, purchase_sage_report,
  sopromer_sale_analysis_report, pos_cash_anomaly_report,
  pos_cashinout_report, pos_sales_report, odoo_sage_export).

## 18.0.1.0.1 (2026-05-12)

- fix: bypass POS critical models to prevent workflow blocking
  (pos.order, pos.order.line, pos.payment, pos.session, stock.picking,
  stock.move, stock.move.line, stock.quant, account.move, account.move.line,
  account.bank.statement, account.bank.statement.line, account.payment).
- Origin: incident P0 2026-05-12 — POS cashier role blocked on write
  pos.order state draft→paid→done.

## 18.0.1.0.0

- Initial release: server-side ORM enforcement of access_roles restrictions
  (create/write/unlink interception based on role configuration).
