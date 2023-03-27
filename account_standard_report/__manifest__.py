# -*- coding: utf-8 -*-

{
    'name': 'Standard Accounting Report',
    'version': '13.0.1.0.6',
    'category': 'Accounting',
    'author': "Prixgen Tech Solutions Pvt. Ltd.",
    'website': 'https://www.prixgen.com',
    'company': 'Prixgen Tech Solutions Pvt. Ltd.',
    'depends': ['account', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'data/report_paperformat.xml',
        'data/data_account_standard_report.xml',
        'data/res_currency_data.xml',
        'report/report_account_standard_report.xml',
        'views/account_view.xml',
        'views/account_standard.xml',
        'views/account_standard_report_template_view.xml',
        'views/res_currency_views.xml',
        'wizard/account_standard_report_view.xml',
    ],
    'demo': [],


    'installable': True,
    'auto_install': False,

    # 'images': ['images/main_screenshot.png'],
}
