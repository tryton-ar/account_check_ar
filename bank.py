# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Account(metaclass=PoolMeta):
    __name__ = 'bank.account'

    issued_check_account = fields.Many2One('account.account',
        'Issued Check Account', domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ])
