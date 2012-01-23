#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Account Check',
    'version': '2.0.1',
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
}
