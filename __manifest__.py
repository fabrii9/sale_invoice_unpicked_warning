# -*- coding: utf-8 -*-
{
    "name": "Venta: aviso al facturar mercadería sin separar",
    "summary": "Al confirmar una factura de venta avisa si hay productos que "
               "todavía no pasaron el primer paso de la entrega (recolección)",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Mundolimpio",
    "license": "LGPL-3",
    "depends": ["sale_stock", "account"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/unpicked_warning_wizard_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
