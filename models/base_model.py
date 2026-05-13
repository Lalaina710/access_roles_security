from odoo import api, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError


# Whitelist des modèles critiques workflow POS + comptabilité auto-générée.
# Ces modèles bypassent les restrictions de role pour éviter de bloquer
# les flux natifs Odoo (paiement POS → write pos.order state, création
# stock.picking/move automatique, comptabilisation auto via account.move).
# Cf. incident P0 2026-05-12 : caissier role PDV bloqué sur write pos.order
# state draft→paid→done par AccessError ici.
_POS_BYPASS_MODELS = frozenset({
    'pos.order',
    'pos.order.line',
    'pos.payment',
    'pos.session',
    'stock.picking',
    'stock.move',
    'stock.move.line',
    'stock.quant',
    'account.move',
    'account.move.line',
    'account.bank.statement',
    'account.bank.statement.line',
    'account.payment',
})


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _is_pos_critical_model(self):
        """True si le modèle est critique pour le workflow POS et doit
        bypasser les restrictions de role (write/create/unlink).

        La sécurité reste assurée par les ACL/record rules natifs Odoo
        et par les modules `sensible_pos_access_rights_employee` /
        `access_roles` côté UI. Cette exemption évite uniquement le
        blocage du workflow ORM automatique (état POS, picking, AML).
        """
        return self._name in _POS_BYPASS_MODELS

    def _get_role_management(self):
        """Return the current user's role management, or False."""
        if self.env.su:
            return False
        user = self.env.user
        if user.id == SUPERUSER_ID:
            return False
        role = user.access_role_id
        if not role or not role.role_management_id:
            return False
        return role.role_management_id

    def _check_role_model_restriction(self, operation):
        """Check if the current user's role restricts an operation on this model.

        :param operation: 'is_hide_create' or 'is_hide_delete'
        :raises AccessError: if the operation is blocked
        """
        management = self._get_role_management()
        if not management:
            return
        model_access = management.model_access_ids.filtered(
            lambda r: r.model_id.model == self._name
        )
        if not model_access:
            return
        if any(model_access.mapped(operation)):
            raise AccessError(
                _("Your access role '%(role)s' does not allow this operation on %(model)s.",
                  role=self.env.user.access_role_id.name, model=self._name)
            )

    @api.model_create_multi
    def create(self, vals_list):
        # Bypass précoce pour les modèles critiques POS (workflow natif).
        if not self._is_pos_critical_model():
            self._check_role_model_restriction('is_hide_create')
        return super().create(vals_list)

    def unlink(self):
        # Bypass précoce pour les modèles critiques POS (workflow natif).
        if not self._is_pos_critical_model():
            self._check_role_model_restriction('is_hide_delete')
        return super().unlink()

    def write(self, vals):
        # Bypass précoce pour les modèles critiques POS (workflow natif).
        # Évite de bloquer write pos.order/stock.picking/account.move
        # générés automatiquement par le flux POS et la chaîne logistique.
        if self._is_pos_critical_model():
            return super().write(vals)

        management = self._get_role_management()
        if not management:
            return super().write(vals)

        # Global readonly
        if management.is_readonly:
            raise AccessError(
                _("Your access role '%(role)s' has system-wide read-only access.",
                  role=self.env.user.access_role_id.name)
            )

        # Model readonly
        model_access = management.model_access_ids.filtered(
            lambda r: r.model_id.model == self._name
        )
        if model_access and any(model_access.mapped('is_model_readonly')):
            raise AccessError(
                _("Your access role '%(role)s' does not allow editing %(model)s.",
                  role=self.env.user.access_role_id.name, model=self._name)
            )

        # Field readonly
        field_access = management.field_access_ids.filtered(
            lambda r: r.model_id.model == self._name and r.is_field_readonly
        )
        if field_access:
            readonly_fields = set()
            for fa in field_access:
                readonly_fields.update(fa.fields_ids.mapped('name'))
            blocked = readonly_fields & set(vals.keys())
            if blocked:
                raise AccessError(
                    _("Your access role '%(role)s' does not allow editing fields: %(fields)s on %(model)s.",
                      role=self.env.user.access_role_id.name,
                      fields=', '.join(blocked), model=self._name)
                )

        return super().write(vals)
