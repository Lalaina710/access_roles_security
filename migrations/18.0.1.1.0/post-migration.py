"""Post-migration v18.0.1.1.0 — access_roles_security.

Pré-coche les modèles fiche produit dans `writable_model_ids` du
role.management associé au rôle "Controleur" (CdG SOPROMER), afin de
reproduire le comportement de la whitelist hardcodée v18.0.1.0.3 sans
modification de code.

Idempotent :
    - skip si role "Controleur" absent
    - skip si role.management absent
    - skip silencieusement les modèles non installés sur l'instance
    - utilise (4, id, 0) (link) donc pas de doublon si exécuté 2x
"""
import logging

_logger = logging.getLogger(__name__)


# Modèles fiche produit historiquement débloqués par la whitelist v18.0.1.0.3.
# La liste reste minimaliste — un admin peut compléter via UI sans patch code.
_PRODUCT_MODELS_DEFAULT = [
    'product.template',
    'product.product',
    'product.category',
    'product.pricelist',
    'product.pricelist.item',
    'product.attribute',
    'product.attribute.value',
    'product.template.attribute.line',
    'product.template.attribute.value',
    'product.supplierinfo',
    'product.packaging',
    'product.tag',
]


def migrate(cr, version):
    """Pré-remplit la whitelist pour le rôle 'Controleur' (CdG SOPROMER)."""
    if not version:
        return

    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Cherche le rôle "Controleur" (CdG SOPROMER).
    #    On ne le crée pas — s'il n'existe pas sur l'instance (ex. autre
    #    client que SOPROMER), on skip silencieusement.
    role = env['access.role'].search([('name', '=', 'Controleur')], limit=1)
    if not role:
        _logger.info(
            "[access_roles_security 1.1.0] Rôle 'Controleur' absent — "
            "skip pré-remplissage writable_model_ids."
        )
        return

    management = role.role_management_id
    if not management:
        _logger.info(
            "[access_roles_security 1.1.0] Rôle 'Controleur' sans "
            "role_management_id — skip."
        )
        return

    # 2. Résout uniquement les modèles présents dans ir.model
    #    (un module produit absent = on ignore, pas d'erreur).
    IrModel = env['ir.model']
    existing_models = IrModel.search([('model', 'in', _PRODUCT_MODELS_DEFAULT)])
    missing = set(_PRODUCT_MODELS_DEFAULT) - set(existing_models.mapped('model'))
    if missing:
        _logger.info(
            "[access_roles_security 1.1.0] Modèles non installés ignorés: %s",
            sorted(missing),
        )

    if not existing_models:
        _logger.warning(
            "[access_roles_security 1.1.0] Aucun modèle produit installé — "
            "rien à pré-remplir."
        )
        return

    # 3. Link (4, id, 0) : ajoute sans toucher aux existants déjà cochés.
    #    Idempotent — exécution multiple = même résultat.
    commands = [(4, m.id, 0) for m in existing_models]
    management.write({'writable_model_ids': commands})

    _logger.info(
        "[access_roles_security 1.1.0] Pré-rempli %d modèles dans "
        "writable_model_ids du rôle 'Controleur' (role.management id=%d): %s",
        len(existing_models),
        management.id,
        existing_models.mapped('model'),
    )
