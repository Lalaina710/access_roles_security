from odoo import fields, models


class RoleManagement(models.Model):
    _inherit = 'role.management'

    writable_model_ids = fields.Many2many(
        'ir.model',
        'role_management_writable_model_rel',
        'role_management_id',
        'model_id',
        string='Modèles éditables (exceptions à lecture seule)',
        help=(
            "Modèles que les users de ce rôle peuvent éditer même si "
            "'Make System ReadOnly' est coché. Permet une whitelist "
            "configurable sans modification de code. Les restrictions "
            "per-model et per-field continuent de s'appliquer si "
            "configurées explicitement sur ces modèles."
        ),
    )
