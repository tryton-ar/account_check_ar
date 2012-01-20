# -*- encoding: utf-8 -*-
{
    'name': 'Account Check',
    'version': '0.1',
    'author': 'Ignacio E. Parszyk',
    'email': 'iparszyk@thymbra.com',
    'website': 'http://thymbra.com',
    'translation': ['es_CO.csv'],
    'depends': [
        'account',
        'account_invoice',
        'account_voucher',
    ],
    'description': '''
        Account Check
''',

    'xml': [
        'account_check.xml',
        'account_voucher_view.xml',
        'journal.xml',
        'workflow.xml'
    ],
    'active': False,
}
