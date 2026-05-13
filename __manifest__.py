{
    'name': 'Access Roles - Server Security',
    'version': '18.0.1.0.1',
    'category': 'Security',
    'summary': 'Server-side enforcement for Access Roles restrictions',
    'description': """
Blocks create/write/unlink at the ORM level based on access_roles configuration.
Prevents bypass via URL or RPC.

Changelog
---------
18.0.1.0.1 (2026-05-12)
    [FIX] Bypass POS critical models to prevent workflow blocking
          (pos.order, pos.order.line, pos.payment, pos.session,
           stock.picking, stock.move, stock.move.line, stock.quant,
           account.move, account.move.line, account.bank.statement,
           account.bank.statement.line, account.payment).
          Origine : incident P0 2026-05-12 — caissier role PDV
          bloqué sur write pos.order state draft→paid→done.

18.0.1.0.0
    Initial release.
""",
    'author': 'Custom',
    'depends': ['access_roles'],
    'data': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
