{
    'name': 'BI WorldWide contacts custom',
    'version': '13.0.0.3',
    'category': 'Tools',
    'sequence': 1,
    'author': 'Prime Minds Consulting Private Limited',
    'summary': 'Adding new in contacts',
    'description': "",
    'website': 'https://www.primeminds.c/',
    'depends': ['web', 'contacts', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/contacts.xml',
        'views/email_not_sending_customers.xml'



    ],

    'installable': True,
    'application': True,
    'auto_install': False
}
