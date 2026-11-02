# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval


class Configuration(metaclass=PoolMeta):
    __name__ = 'account.configuration'

    default_check_journal = fields.MultiValue(fields.Many2One(
        'account.journal', 'Default Check Journal',
        domain=[('type', '=', 'cash')]))
    third_check_account = fields.MultiValue(fields.Many2One(
        'account.account', 'Received Check Account',
        domain=[
            ('closed', '!=', True),
            ('type', '!=', None),
            ('company', '=', Eval('context', {}).get('company', -1)),
            ]))
    rejected_check_account = fields.MultiValue(fields.Many2One(
        'account.account', 'Rejected Check Account',
        domain=[
            ('closed', '!=', True),
            ('type', '!=', None),
            ('company', '=', Eval('context', {}).get('company', -1)),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'third_check_account', 'rejected_check_account',
                'default_check_journal'}:
            return pool.get('account.configuration.default_account')
        return super().multivalue_model(field)


class ConfigurationDefaultAccount(metaclass=PoolMeta):
    __name__ = 'account.configuration.default_account'

    default_check_journal = fields.Many2One(
        'account.journal', 'Default Check Journal',
        domain=[('type', '=', 'cash')],
        context={'company': Eval('company', -1)},
        depends={'company'})
    third_check_account = fields.Many2One(
        'account.account', 'Received Check Account',
        domain=[
            ('closed', '!=', True),
            ('type', '!=', None),
            ('company', '=', Eval('company', -1)),
            ])
    rejected_check_account = fields.Many2One(
        'account.account', 'Rejected Check Account',
        domain=[
            ('closed', '!=', True),
            ('type', '!=', None),
            ('company', '=', Eval('company', -1)),
            ])
