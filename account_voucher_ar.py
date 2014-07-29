#This file is part of the account_check_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelView, fields
from trytond.pyson import Eval, Not, In
from trytond.pool import Pool, PoolMeta

__all__ = ['AccountVoucher']
__metaclass__ = PoolMeta


class AccountVoucher:
    __name__ = 'account.voucher'

    issued_check = fields.One2Many('account.issued.check', 'voucher',
        'Issued Checks', states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': In(Eval('state'), ['posted']),
        })
    third_pay_checks = fields.Many2Many('account.voucher-account.third.check',
        'voucher', 'third_check', 'Third Checks',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': In(Eval('state'), ['posted']),
            },
        domain=[
            ('state', '=', 'held'),
            ])
    third_check = fields.One2Many('account.third.check', 'voucher_in',
        'Third Checks', states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
            'readonly': In(Eval('state'), ['posted']),
        })

    @classmethod
    def __setup__(cls):
        super(AccountVoucher, cls).__setup__()
        cls._error_messages.update({
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s",',
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
                    move_lines.append({
                        'debit': check.amount,
                        'credit': Decimal('0.00'),
                        'account': self.journal.third_check_account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': self.party.id,
                        'maturity_date': check.date,
                    })

        if self.voucher_type == 'payment':
            if self.issued_check:
                if not self.journal.issued_check_account:
                    self.raise_user_error('no_journal_check_account',
                        error_args=(self.journal.name,))
                for check in self.issued_check:
                    move_lines.append({
                        'debit': Decimal('0.00'),
                        'credit': check.amount,
                        'account': self.journal.issued_check_account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': self.party.id,
                        'maturity_date': check.date,
                })
            if self.third_pay_checks:
                for check in self.third_pay_checks:
                    move_lines.append({
                        'debit': Decimal('0.00'),
                        'credit': check.amount,
                        'account': self.journal.third_check_account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': self.party.id,
                        'maturity_date': check.date,
                    })

        return move_lines

    @classmethod
    @ModelView.button
    def post(cls, vouchers):
        super(AccountVoucher, cls).post(vouchers)
        ThirdCheck = Pool().get('account.third.check')
        IssuedCheck = Pool().get('account.issued.check')
        Date = Pool().get('ir.date')

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
                    'date_out': Date.today(),
                    'state': 'delivered',
                })
