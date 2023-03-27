{
    'name': 'BI WorldWide invoice custom',
    'version': '13.0.0.2',
    'category': 'Accounting',
    
    'summary': 'Modifictaion in standard reports',
    'description': "",
    'website': 'https://www.prixgen.com/',
    'depends': ['web','account','base',],
    'data': [ 
    'views/report_templates.xml',
    'views/invoice_report.xml',
    'views/pono.xml',
     ],
    
    'installable': True,
    'application': True,
    'auto_install': False
}
