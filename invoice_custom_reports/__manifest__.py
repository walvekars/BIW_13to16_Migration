# -*- coding: utf-8 -*-
{
    'name': 'Invoice Custom Reports',
    'version': '13.0.1.21',
    'author': 'Prixgen Tech Solutions Pvt. Ltd.',
    'company':'Prixgen Tech Solutions Pvt. Ltd.',
    'website':'https://www.prixgen.com',
    'license': 'OPL-1',
    'category': 'Tools',
    'summary': 'Invoice Custom Reports',
    'description': """Prix
Invoice Custom Reports
----------------------

Invoice Custom Reports
""",
    'depends': ['account', 'l10n_in', 'l10n_in_einvoice'],
    'data': [
        'views/account_move_view.xml',
        'views/invoice_reports.xml',
        'views/invoice_reports_2.xml',
        'views/invoice_reports_3.xml',
        'views/sez_invoice_reports.xml',
        'views/res_company_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
