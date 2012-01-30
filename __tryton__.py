#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Account Check Argentina',
    'version': '2.0.1',
    'author': 'Thymbra - Torre de Hanoi',
    'email': 'iparszyk@thymbra.com',
    'website': 'http://thymbra.com/',
    'description': '''Account Check for Argentina''',
    'depends': [
        'account',
        'account_invoice',
        'account_voucher_ar',
    ],
    'xml': [
        'account_check_ar.xml',
        'account_voucher_ar.xml',
        'journal.xml',
        'workflow.xml'
    ],
    'translation': [
        'es_CO.csv',
    ],
}
