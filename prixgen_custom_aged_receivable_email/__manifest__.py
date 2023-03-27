# -*- coding: utf-8 -*-
{
    'name': "Custom Aged Receivable Email",
    'summary': "Custom Aged Receivable Email",
    'description': """
        
    """,
    'author': "Prixgen to Prime Minds Consulting Pvt. Ltd.",
    'company': "Prixgen & Prime Minds Consulting Pvt. Ltd.",
    'website': "https://www.primeminds.com",

    'category': 'Account',
    'version': '14.3',
    'depends': ['base','account','account_reports','mail','account_reports'],
    'data': [
        'views/view.xml',
        'views/aged_receivable_email_template.xml',
        'wizard/email_wizard.xml',



    ],
    "assets": {
        "web.assets_backend": [
            "prixgen_custom_aged_receivable_email/static/src/js/receivable_report.js",
        ],
    },

}
