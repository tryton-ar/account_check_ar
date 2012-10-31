#This file is part of the account_check_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
{
    'name': 'Account Check Argentina',
    'name_es_AR': 'Cartera de Cheques para Argentina',
    'version': '2.4.0',
    'author': 'Thymbra - Torre de Hanoi',
    'email': 'info@thymbra.com',
    'website': 'http://thymbra.com/',
    'description': '''Account Check for Argentina''',
    'description_es_AR': '''Manejo de Cartera de Cheques para Argentina''',
    'depends': [
        'account',
        'account_invoice',
        'account_voucher_ar',
        'account_bank_ar',
    ],
    'xml': [
        'account_check_ar.xml',
        'account_voucher_ar.xml',
        'journal.xml',
    ],
    'translation': [
        'locale/es_AR.po',
    ],
}
