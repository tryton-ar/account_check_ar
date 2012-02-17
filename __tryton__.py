#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Account Check Argentina',
    'name_es_ES': 'Cartera de Cheques para Argentina',
    'version': '2.2.0',
    'author': 'Thymbra - Torre de Hanoi',
    'email': 'info@thymbra.com',
    'website': 'http://thymbra.com/',
    'description': '''Account Check for Argentina''',
    'description_es_ES': '''Manejo de Cartera de Cheques para Argentina''',
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
        'es_ES.po',
    ],
}
