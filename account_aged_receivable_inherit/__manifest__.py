{
    'name': 'Account Aged Receivable Extended',
    'version': '13.0.0.1 07 Dec',
    'category': 'Account',
    'license': 'AGPL-3',
    'description': """""",
    'Last Updated': '',
    'company': 'Prime Minds Consulting Pvt Ltd',
    'author': 'PMCS Er. Biswajeet',
    'website': 'http://www.primeminds.co',
    'depends': ['account_reports','account','report_xlsx','web','base'],
    'data': [
        'views/account_report_search_view_inherit.xml',

    ],

    # "assets": {
    #     "web.assets_backend": [
    #         "account_aged_receivable_inherit/static/src/js/aged_receivable_inherit.js",
    #     ],
    # },
    'installable': True,
}


