# -*- encoding: utf-8 -*-
{
    'name': 'Account Check',
    'version': '0.1',
    'author': 'Ignacio E. Parszyk',
    'email': 'iparszyk@thymbra.com',
    'website': 'http://thymbra.com',
    'description': '''Account Check''',
    'depends': [
        'account',
        'account_invoice',
        'account_voucher',
    ],
    'xml': [
        'account_check.xml',
        'account_voucher_view.xml',
        'journal.xml',
        'workflow.xml'
    ],
    'translation': [
        'es_CO.csv',
    ],
    'active': False,
}
