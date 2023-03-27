# -*- coding: utf-8 -*-
{
    'name': "BI Custom Accounting",

    'summary': """
        BI Custom Accounting
    """,

    'description': """
        BI Custom Accounting
    """,

    'author': 'Prixgen Tech Solutions Pvt. Ltd.',
    'company': 'Prixgen Tech Solutions Pvt. Ltd.',
    'website': 'https://www.prixgen.com',
    'category': 'Uncategorized',
    'version': '13.0.2',

    'depends': ['account','base','account_cost_center','account_reports','account_followup'],

    'data': [
        'views/views.xml',
        'views/account_payment.xml',
        'views/report_followup.xml',
        'views/account_payment_journal.xml',
        'data/mail_template.xml',
    ],
}