{
    'name': 'TDS Report Form',
    'summary': 'TDS Report From',
    'category': 'account',
    'version': '13.0.5',
    'description': """TDS Report Form """,
    'depends': ['base','account'],
    'author': 'Prixgen Tech Solutions Pvt. Ltd.',
    'company': 'Prixgen Tech Solutions Pvt. Ltd.',
    'website': 'https://www.prixgen.com',
    'data': [
        'security/ir.model.access.csv',
		'views/tds_custom_view.xml'
	    ],
    'auto_install': False,
    'application': True,
}
