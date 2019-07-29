# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pyson import Eval, Not, In, Or
from trytond.pool import Pool, PoolMeta

__all__ = ['AccountVoucher']

_ZERO = Decimal('0.0')


class AccountVoucher:
    __name__ = 'account.voucher'
    __metaclass__ = PoolMeta

    issued_check = fields.One2Many('account.issued.check', 'voucher',
        'Issued Checks',
        add_remove=[
                ('state', '=', 'draft'),
                ],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': Or(
                            In(Eval('state'), ['posted']),
                            Not(In(Eval('currency_code'), ['ARS']))),
            })
    third_pay_checks = fields.Many2Many('account.voucher-account.third.check',
        'voucher', 'third_check', 'Third Checks',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': Or(
                            In(Eval('state'), ['posted']),
                            Not(In(Eval('currency_code'), ['ARS']))),
            },
        domain=[
            ('state', 'in', ['held', 'reverted']),
            ('not_to_order', '=', False),
            ])
    third_check = fields.One2Many('account.third.check', 'voucher_in',
        'Third Checks',
        add_remove=[
                ('state', '=', 'draft'),
                ],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
            'readonly': Or(
                            In(Eval('state'), ['posted']),
                            Not(In(Eval('currency_code'), ['ARS']))),
            })

    @classmethod
    def __setup__(cls):
        super(AccountVoucher, cls).__setup__()
        cls._error_messages.update({
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s",',
            'check_not_in_draft': 'Check "%s" is not in draft state',
            'issued_check_not_issued': ('Issued check "%s" is not in '
                'Issued state'),
            'third_check_not_held': 'Third check "%s" is not in Held state',
            'third_pay_check_not_delivered': ('Third check "%s" is not in '
                'Delivered state'),
            })

    @fields.depends('party', 'pay_lines', 'lines_credits', 'lines_debits',
        'issued_check', 'third_check', 'third_pay_checks')
    def on_change_with_amount(self, name=None):
        amount = super(AccountVoucher, self).on_change_with_amount(name)
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
        move_lines = super(AccountVoucher, self).prepare_move_lines()
        Period = Pool().get('account.period')
        if self.voucher_type == 'receipt':
            if self.third_check:
                if not self.journal.third_check_account:
                    self.raise_user_error('no_journal_check_account',
                        error_args=(self.journal.name,))
                for check in self.third_check:
                    if check.state != 'draft':
                        self.raise_user_error('check_not_in_draft',
                            error_args=(check.name,))
                    move_lines.append({
                        'debit': check.amount,
                        'credit': _ZERO,
                        'account': self.journal.third_check_account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': (
                            self.journal.third_check_account.party_required
                            and self.party.id or None),
                        'maturity_date': check.date,
                    })

        if self.voucher_type == 'payment':
            if self.issued_check:
                if not self.journal.issued_check_account:
                    self.raise_user_error('no_journal_check_account',
                        error_args=(self.journal.name,))
                for check in self.issued_check:
                    move_lines.append({
                        'debit': _ZERO,
                        'credit': check.amount,
                        'account': self.journal.issued_check_account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': (
                            self.journal.issued_check_account.party_required
                            and self.party.id or None),
                        'maturity_date': check.date,
                        })
            if self.third_pay_checks:
                for check in self.third_pay_checks:
                    move_lines.append({
                        'debit': _ZERO,
                        'credit': check.amount,
                        'account': self.journal.third_check_account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': (
                            self.journal.third_check_account.party_required
                            and self.party.id or None),
                        'maturity_date': check.date,
                        })

        return move_lines

    @classmethod
    @ModelView.button
    def post(cls, vouchers):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        IssuedCheck = pool.get('account.issued.check')
        Date = pool.get('ir.date')

        super(AccountVoucher, cls).post(vouchers)

        today = Date.today()
        for voucher in vouchers:
            if voucher.issued_check:
                IssuedCheck.write(list(voucher.issued_check), {
                    'receiving_party': voucher.party.id,
                    'state': 'issued',
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

        super(AccountVoucher, cls).cancel(vouchers)

        for voucher in vouchers:
            if voucher.issued_check:
                for check in voucher.issued_check:
                    if check.state != 'issued':
                        cls.raise_user_error('issued_check_not_issued',
                            (check.name,))
                IssuedCheck.write(list(voucher.issued_check), {
                    'receiving_party': None,
                    'state': 'draft',
                    })
            if voucher.third_check:
                for check in voucher.third_check:
                    if check.state not in ['held', 'reverted']:
                        cls.raise_user_error('third_check_not_held',
                            (check.name,))
                ThirdCheck.write(list(voucher.third_check), {
                    'source_party': None,
                    'state': 'draft',
                    })
            if voucher.third_pay_checks:
                for check in voucher.third_pay_checks:
                    if check.state != 'delivered':
                        cls.raise_user_error('third_pay_check_not_delivered',
                            (check.name,))
                ThirdCheck.write(list(voucher.third_pay_checks), {
                    'destiny_party': None,
                    'date_out': None,
                    'state': 'held',
                    })
