# -*- coding: utf-8 -*-
{
    "name": "Quick Create RFQ From Quotation and PO",
    "author": "Prime Minds",
    "version": "1.0",
    "website": "https://www.primeminds.co",
    "category": 'Purchases',
    'description' : """
        This Odoo app allows to Create RFQ from Sales Order(Quotation).
    """,
    'summary': """ """,
    "depends": [
        "stock",
        "sale_management",
        "purchase",
        "l10n_in_purchase",
        "account"],
    "data": [
        "views/sale_view.xml",
        "views/purchase_view.xml",
        "views/purchase_report_2.xml",
        "wizard/rfq_from_quotation.xml",
     ],
    'license': 'LGPL-3',
    # 'currency':'USD',
    'price': 15.0,
    'installable' : True,
    "auto_install" : False,
    "application" : True,
    # "pre_init_hook": "pre_init_check",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
