# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Not, In, Or
from trytond.exceptions import UserError
from trytond.i18n import gettext

_ZERO = Decimal('0.0')


class AccountVoucher(metaclass=PoolMeta):
    __name__ = 'account.voucher'

    issued_check = fields.One2Many('account.issued.check', 'voucher',
        'Issued Checks',
        add_remove=[('state', '=', 'draft')],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': Or(
                In(Eval('state'), ['posted', 'cancelled']),
                Not(In(Eval('currency_code'), ['ARS']))),
            })
    third_pay_checks = fields.Many2Many('account.voucher-account.third.check',
        'voucher', 'third_check', 'Third Checks',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': Or(
                In(Eval('state'), ['posted', 'cancelled']),
                Not(In(Eval('currency_code'), ['ARS']))),
            },
        domain=[
            ('state', 'in', ['held', 'reverted']),
            ('not_to_order', '!=', True),
            ])
    third_check = fields.One2Many('account.third.check', 'voucher_in',
        'Third Checks',
        add_remove=[('state', '=', 'draft')],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
            'readonly': Or(
                In(Eval('state'), ['posted', 'cancelled']),
                Not(In(Eval('currency_code'), ['ARS']))),
            })

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.third_pay_checks.search_order = [
            ('date', 'ASC'),
            ]

    @fields.depends('third_check', 'issued_check', 'third_pay_checks')
    def on_change_with_amount(self, name=None):
        amount = super().on_change_with_amount(name)
        if self.third_check:
            for t_check in self.third_check:
                amount += t_check.amount
        if self.issued_check:
            for i_check in self.issued_check:
                amount += i_check.amount
        if self.third_pay_checks:
            for check in self.third_pay_checks:
                amount += check.amount
        return amount

    def prepare_move_lines(self):
        pool = Pool()
        Configuration = pool.get('account.configuration')

        move_lines = super().prepare_move_lines()

        if self.voucher_type == 'receipt':
            if self.third_check:
                config = Configuration(1)
                account = config.get_multivalue('third_check_account')
                if not account:
                    raise UserError(gettext('account_check_ar.'
                        'msg_missing_third_check_account'))
                for check in self.third_check:
                    if check.state != 'draft':
                        raise UserError(gettext('account_check_ar.'
                            'msg_check_not_draft',
                            check=check.name))
                    move_lines.append({
                        'account': account.id,
                        'move': self.move.id,
                        'debit': check.amount,
                        'credit': _ZERO,
                        'maturity_date': check.date,
                        'party': (
                            account.party_required and
                            self.party.id or None),
                    })

        if self.voucher_type == 'payment':
            if self.issued_check:
                for check in self.issued_check:
                    account = check.bank_account.issued_check_account
                    if not account:
                        raise UserError(gettext('account_check_ar.'
                            'msg_missing_issued_check_account',
                            bank_account=check.bank_account.rec_name))
                    move_lines.append({
                        'account': account.id,
                        'move': self.move.id,
                        'debit': _ZERO,
                        'credit': check.amount,
                        'maturity_date': check.date,
                        'party': (
                            account.party_required and
                            self.party.id or None),
                        })
            if self.third_pay_checks:
                config = Configuration(1)
                account = config.get_multivalue('third_check_account')
                if not account:
                    raise UserError(gettext('account_check_ar.'
                        'msg_missing_third_check_account'))
                for check in self.third_pay_checks:
                    move_lines.append({
                        'account': account.id,
                        'move': self.move.id,
                        'debit': _ZERO,
                        'credit': check.amount,
                        'maturity_date': check.date,
                        'party': (
                            account.party_required and
                            self.party.id or None),
                        })

        return move_lines

    @classmethod
    @ModelView.button
    def post(cls, vouchers):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        IssuedCheck = pool.get('account.issued.check')
        Date = pool.get('ir.date')

        super().post(vouchers)

        today = Date.today()
        for voucher in vouchers:
            if voucher.issued_check:
                for check in voucher.issued_check:
                    number = (check.checkbook and
                        check.checkbook.sequence.get() or check.name)
                    check_exists = IssuedCheck.search([
                        ('name', '=', number),
                        ('bank_account', '=', check.bank_account.id),
                        ('id', '!=', check.id),
                        ])
                    if check_exists:
                        raise UserError(gettext(
                            'account_check_ar.msg_check_already_exists',
                            number=number))
                    IssuedCheck.write([check], {
                        'receiving_party': voucher.party.id,
                        'state': 'issued',
                        'name': number,
                        })
                IssuedCheck.issued(voucher.issued_check)
            if voucher.third_check:
                ThirdCheck.write(list(voucher.third_check), {
                    'source_party': voucher.party.id,
                    'state': 'held',
                    })
            if voucher.third_pay_checks:
                ThirdCheck.write(list(voucher.third_pay_checks), {
                    'destiny_party': voucher.party.id,
                    'date_out': today,
                    'state': 'delivered',
                    })

    @classmethod
    @ModelView.button
    def cancel(cls, vouchers):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        IssuedCheck = pool.get('account.issued.check')

        for voucher in vouchers:
            if voucher.issued_check:
                for check in voucher.issued_check:
                    if check.state != 'issued':
                        raise UserError(gettext(
                            'account_check_ar.msg_issued_check_not_issued',
                            check=check.name))
                IssuedCheck.write(list(voucher.issued_check), {
                    'receiving_party': None,
                    'state': 'draft',
                    })
            if voucher.third_check:
                for check in voucher.third_check:
                    if check.state not in ['held', 'reverted']:
                        raise UserError(gettext(
                            'account_check_ar.msg_third_check_not_held',
                            check=check.name))
                ThirdCheck.write(list(voucher.third_check), {
                    'source_party': None,
                    'state': 'draft',
                    })
            if voucher.third_pay_checks:
                for check in voucher.third_pay_checks:
                    if check.state != 'delivered':
                        raise UserError(gettext('account_check_ar.'
                            'msg_third_pay_check_not_delivered',
                            check=check.name))
                ThirdCheck.write(list(voucher.third_pay_checks), {
                    'destiny_party': None,
                    'date_out': None,
                    'state': 'held',
                    })

        super().cancel(vouchers)
