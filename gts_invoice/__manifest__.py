# -*- coding: utf-8 -*-
{
    'name': 'GTS Invoice Report',
    'version': '13.0.1.14',
    'author': 'Prixgen Tech Solutions Pvt. Ltd.',
    'company': 'Prixgen Tech Solutions Pvt. Ltd.',
    'website': 'https://www.prixgen.com',
    'license': 'OPL-1',
    'category': 'Tools',
    'summary': 'GTS Invoice Report',
    'description': """
GTS Invoice Report
------------------

GTS Invoice Report
""",
    'depends': ['account', 'l10n_in'],
    'data': [
        'views/invoice_reports.xml',
    ],
    'installable': True,
    'auto_install': False,
}
