{
    'name': 'BI WorldWide Purchase',
    'version': '13.0.0.3',
    'category': 'Tools',
    'sequence': 1,

    'summary': 'Adding new in fields,page and validations',
    'description': "",
    'website': '',
    'depends': ['base', 'contacts', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_po.xml',
        'views/partner_po.xml',
        'views/res_purchase_customer.xml'



    ],

    'installable': True,
    'application': True,
    'auto_install': False
}
