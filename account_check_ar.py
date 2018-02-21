# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.transaction import Transaction
from trytond.pyson import Eval, In
from trytond.pool import Pool

__all__ = ['AccountIssuedCheck', 'AccountThirdCheck',
    'AccountVoucherThirdCheck', 'Journal', 'ThirdCheckHeldStart',
    'ThirdCheckHeld', 'ThirdCheckDepositStart', 'ThirdCheckDeposit',
    'ThirdCheckRevertDepositStart', 'ThirdCheckRevertDeposit',
    'IssuedCheckDebitStart', 'IssuedCheckDebit',
    'IssuedCheckRevertDebitStart', 'IssuedCheckRevertDebit']

_STATES = {
    'readonly': Eval('state') != 'draft',
    }
_DEPENDS = ['state']

_ZERO = Decimal('0.0')


class AccountIssuedCheck(ModelSQL, ModelView):
    'Account Issued Check'
    __name__ = 'account.issued.check'

    name = fields.Char('Number', required=True, states=_STATES,
        depends=_DEPENDS)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_STATES, depends=_DEPENDS)
    date_out = fields.Date('Date Out', states=_STATES, depends=_DEPENDS)
    date = fields.Date('Date', required=True, states=_STATES, depends=_DEPENDS)
    debit_date = fields.Date('Debit Date', readonly=True,
        states={
            'invisible': Eval('state') != 'debited',
            }, depends=_DEPENDS)
    receiving_party = fields.Many2One('party.party', 'Receiving Party',
        states={
            'invisible': Eval('state') == 'draft',
            'readonly': Eval('state') != 'draft',
            }, depends=_DEPENDS)
    on_order = fields.Char('On Order', states=_STATES, depends=_DEPENDS)
    signatory = fields.Char('Signatory', states=_STATES, depends=_DEPENDS)
    clearing = fields.Selection([
        (None, ''),
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_STATES, depends=_DEPENDS)
    origin = fields.Char('Origin', states=_STATES, depends=_DEPENDS)
    voucher = fields.Many2One('account.voucher', 'Voucher', readonly=True,
        states={
            'invisible': Eval('state') == 'draft',
            }, depends=_DEPENDS)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('debited', 'Debited'),
        ], 'State', readonly=True)
    bank_account = fields.Many2One('bank.account', 'Bank Account',
        required=True, domain=[('owners', 'in', [1])],
        states=_STATES, depends=_DEPENDS)

    @classmethod
    def __setup__(cls):
        super(AccountIssuedCheck, cls).__setup__()
        cls._error_messages.update({
            'delete_check': 'You can not delete a check that is used!',
        })
        cls._buttons.update({
                'issued': {
                    'invisible': Eval('state') != 'draft',
                    },
                'debited': {
                    'invisible': Eval('state') != 'issued',
                    },
                })

    @staticmethod
    def default_date_out():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_amount():
        return _ZERO

    @classmethod
    def issued(cls, checks):
        pass

    @classmethod
    @ModelView.button
    def debited(cls, checks):
        pass

    @classmethod
    def delete(cls, checks):
        if not checks:
            return True
        for check in checks:
            if check.state != 'draft':
                cls.raise_user_error('delete_check')
        return super(AccountIssuedCheck, cls).delete(checks)


class AccountThirdCheck(ModelSQL, ModelView):
    'Account Third Check'
    __name__ = 'account.third.check'

    name = fields.Char('Number', required=True, states=_STATES,
        depends=_DEPENDS)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_STATES, depends=_DEPENDS)
    date_in = fields.Date('Date In', required=True, states=_STATES,
        depends=_DEPENDS)
    date = fields.Date('Date', required=True, states=_STATES, depends=_DEPENDS)
    date_out = fields.Date('Date Out', readonly=True,
        states={
            'invisible': In(Eval('state'), ['draft', 'held']),
            }, depends=_DEPENDS)
    debit_date = fields.Date('Debit Date', readonly=True,
        states={
            'invisible': In(Eval('state'), ['draft', 'held']),
            }, depends=_DEPENDS)
    source_party = fields.Many2One('party.party', 'Source Party',
        readonly=True, states={
            'invisible': Eval('state') == 'draft',
            }, depends=_DEPENDS)
    destiny_party = fields.Many2One('party.party', 'Destiny Party',
        readonly=True, states={
            'invisible': Eval('state') != 'delivered',
            }, depends=_DEPENDS)
    not_to_order = fields.Boolean('Not to order', states=_STATES,
        depends=_DEPENDS)
    on_order = fields.Char('On Order', states=_STATES, depends=_DEPENDS)
    signatory = fields.Char('Signatory', states=_STATES, depends=_DEPENDS)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('held', 'Held'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
        ], 'State', readonly=True)
    vat = fields.Char('Vat', states=_STATES, depends=_DEPENDS)
    clearing = fields.Selection([
        (None, ''),
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_STATES, depends=_DEPENDS)
    origin = fields.Char('Origin', states=_STATES, depends=_DEPENDS)
    voucher_in = fields.Many2One('account.voucher', 'Origin Voucher',
        readonly=True, states={
            'invisible': Eval('state') == 'draft',
            }, depends=_DEPENDS)
    voucher_out = fields.Many2One('account.voucher', 'Target Voucher',
        readonly=True, states={
            'invisible': Eval('state') != 'delivered',
            }, depends=_DEPENDS)
    reject_debit_note = fields.Many2One('account.invoice', 'Debit Note',
        readonly=True, depends=_DEPENDS)  # TODO
    bank = fields.Many2One('bank', 'Bank', required=True,
        states=_STATES, depends=_DEPENDS)
    account_bank_out = fields.Many2One('bank.account', 'Bank Account',
        readonly=True, states={
            'invisible': Eval('state') != 'deposited',
            }, depends=_DEPENDS)

    @classmethod
    def __setup__(cls):
        super(AccountThirdCheck, cls).__setup__()
        cls._error_messages.update({
            'delete_check': 'You can not delete a check that is used!',
        })
        cls._buttons.update({
                'held': {
                    'invisible': Eval('state') != 'draft',
                    },
                'deposited': {
                    'invisible': Eval('state') != 'held',
                    },
                'delivered': {
                    'invisible': Eval('state') != 'held',
                    },
                'rejected': {
                    'invisible': ~Eval('state').in_([
                        'deposited', 'delivered']),
                    },
                })

    @staticmethod
    def default_date_in():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_amount():
        return _ZERO

    @staticmethod
    def default_not_to_order():
        return False

    @classmethod
    @ModelView.button_action('account_check_ar.wizard_third_check_held')
    def held(self, checks):
        pass

    @classmethod
    @ModelView.button_action('account_check_ar.wizard_third_check_deposit')
    def deposited(self, checks):
        pass

    @classmethod
    def delivered(self, checks):
        pass

    @classmethod
    @ModelView.button
    def rejected(self, checks):
        pass

    @classmethod
    def delete(cls, checks):
        if not checks:
            return True
        for check in checks:
            if check.state != 'draft':
                cls.raise_user_error('delete_check')
        return super(AccountThirdCheck, cls).delete(checks)


class AccountVoucherThirdCheck(ModelSQL):
    'Account Voucher - Account Third Check'
    __name__ = 'account.voucher-account.third.check'
    _table = 'account_voucher_account_third_check'

    voucher = fields.Many2One('account.voucher', 'Voucher', required=True,
        select=True, ondelete='CASCADE')
    third_check = fields.Many2One('account.third.check', 'Third Check',
        required=True, ondelete='RESTRICT')


class Journal(ModelSQL, ModelView):
    __name__ = 'account.journal'

    third_check_account = fields.Many2One('account.account',
        'Third Check Account')
    issued_check_account = fields.Many2One('account.account',
        'Issued Check Account')


class ThirdCheckHeldStart(ModelView):
    'Third Check Held'
    __name__ = 'account.third.check.held.start'

    journal = fields.Many2One('account.journal', 'Journal', required=True)


class ThirdCheckHeld(Wizard):
    'Third Check Held'
    __name__ = 'account.third.check.held'

    start = StateView('account.third.check.held.start',
        'account_check_ar.view_third_check_held', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Held', 'held', 'tryton-ok', default=True),
            ])
    held = StateTransition()

    @classmethod
    def __setup__(cls):
        super(ThirdCheckHeld, cls).__setup__()
        cls._error_messages.update({
            'check_not_draft': 'Check "%s" is not draft',
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s"',
            })

    def transition_held(self):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Date = pool.get('ir.date')
        Period = pool.get('account.period')

        date = Date.today()
        period_id = Period.find(1, date)
        for check in ThirdCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state != 'draft':
                self.raise_user_error('check_not_draft',
                    error_args=(check.name,))
            if not self.start.journal.third_check_account:
                self.raise_user_error('no_journal_check_account',
                    error_args=(self.start.journal.name,))

            move, = Move.create([{
                'journal': self.start.journal.id,
                'period': period_id,
                'date': date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account': self.start.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': date,
                'maturity_date': check.date,
                })
            lines.append({
                'account': self.start.journal.credit_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': date,
                })
            MoveLine.create(lines)
            ThirdCheck.write([check], {'state': 'held'})
            Move.post([move])
        return 'end'


class ThirdCheckDepositStart(ModelView):
    'Third Check Deposit'
    __name__ = 'account.third.check.deposit.start'

    bank_account = fields.Many2One('bank.account', 'Bank Account',
        required=True)
    date = fields.Date('Date', required=True)

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()


class ThirdCheckDeposit(Wizard):
    'Third Check Deposit'
    __name__ = 'account.third.check.deposit'

    start = StateView('account.third.check.deposit.start',
        'account_check_ar.view_third_check_deposit', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Deposit', 'deposit', 'tryton-ok', default=True),
            ])
    deposit = StateTransition()

    @classmethod
    def __setup__(cls):
        super(ThirdCheckDeposit, cls).__setup__()
        cls._error_messages.update({
            'check_not_held': 'Check "%s" is not in held',
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s"',
            })

    def transition_deposit(self):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        period_id = Period.find(1, date=self.start.date)
        for check in ThirdCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state != 'held':
                self.raise_user_error('check_not_held',
                    error_args=(check.name,))
            if not self.start.bank_account.journal.third_check_account:
                self.raise_user_error('no_journal_check_account',
                    error_args=(self.start.bank_account.journal.name,))

            move, = Move.create([{
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    self.start.bank_account.journal.debit_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': self.start.date,
                })
            lines.append({
                'account':
                    self.start.bank_account.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': self.start.date,
                })
            MoveLine.create(lines)
            ThirdCheck.write([check], {
                'account_bank_out': self.start.bank_account.id,
                'state': 'deposited',
                })
            Move.post([move])
        return 'end'


class ThirdCheckRevertDepositStart(ModelView):
    'Revert Third Check Deposit'
    __name__ = 'account.third.check.revert_deposit.start'

    date = fields.Date('Date', required=True)

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()


class ThirdCheckRevertDeposit(Wizard):
    'Revert Third Check Deposit'
    __name__ = 'account.third.check.revert_deposit'

    start = StateView('account.third.check.revert_deposit.start',
        'account_check_ar.view_third_check_revert_deposit', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert Deposit', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()

    @classmethod
    def __setup__(cls):
        super(ThirdCheckRevertDeposit, cls).__setup__()
        cls._error_messages.update({
            'check_not_deposited': 'Check "%s" is not deposited',
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s"',
            })

    def transition_revert(self):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        period_id = Period.find(1, date=self.start.date)
        for check in ThirdCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state != 'deposited':
                self.raise_user_error('check_not_deposited',
                    error_args=(check.name,))
            if not check.account_bank_out.journal.third_check_account:
                self.raise_user_error('no_journal_check_account',
                    error_args=(check.account_bank_out.journal.name,))

            move, = Move.create([{
                'journal': check.account_bank_out.journal.id,
                'period': period_id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    check.account_bank_out.journal.debit_account.id,
                'move': move.id,
                'journal': check.account_bank_out.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': self.start.date,
                })
            lines.append({
                'account':
                    check.account_bank_out.journal.third_check_account.id,
                'move': move.id,
                'journal': check.account_bank_out.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': self.start.date,
                })
            MoveLine.create(lines)
            ThirdCheck.write([check], {
                'account_bank_out': None,
                'state': 'held',
                })
            Move.post([move])
        return 'end'


class IssuedCheckDebitStart(ModelView):
    'Issued Check Debit'
    __name__ = 'account.issued.check.debit.start'

    bank_account = fields.Many2One('bank.account', 'Bank Account',
        required=True)
    date = fields.Date('Date', required=True)

    @staticmethod
    def default_date():
        date_obj = Pool().get('ir.date')
        return date_obj.today()


class IssuedCheckDebit(Wizard):
    'Issued Check Debit'
    __name__ = 'account.issued.check.debit'

    start = StateView('account.issued.check.debit.start',
        'account_check_ar.view_issued_check_debit', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Debit', 'debit', 'tryton-ok', default=True),
            ])
    debit = StateTransition()

    @classmethod
    def __setup__(cls):
        super(IssuedCheckDebit, cls).__setup__()
        cls._error_messages.update({
            'check_not_issued': 'Check "%s" is not issued',
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s"',
            })

    def transition_debit(self):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        period_id = Period.find(1, date=self.start.date)
        for check in IssuedCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state != 'issued':
                self.raise_user_error('check_not_issued',
                    error_args=(check.name,))
            if not self.start.bank_account.journal.issued_check_account:
                self.raise_user_error('no_journal_check_account',
                    error_args=(self.start.bank_account.journal.name,))

            move, = Move.create([{
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    self.start.bank_account.journal.issued_check_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': self.start.date,
                })
            lines.append({
                'account': self.start.bank_account.journal.debit_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': self.start.date,
                })
            MoveLine.create(lines)
            IssuedCheck.write([check], {'state': 'debited'})
            Move.post([move])
        return 'end'


class IssuedCheckRevertDebitStart(ModelView):
    'Revert Issued Check Debit'
    __name__ = 'account.issued.check.revert_debit.start'

    date = fields.Date('Date', required=True)

    @staticmethod
    def default_date():
        date_obj = Pool().get('ir.date')
        return date_obj.today()


class IssuedCheckRevertDebit(Wizard):
    'Revert Issued Check Debit'
    __name__ = 'account.issued.check.revert_debit'

    start = StateView('account.issued.check.revert_debit.start',
        'account_check_ar.view_issued_check_revert_debit', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert Debit', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()

    @classmethod
    def __setup__(cls):
        super(IssuedCheckRevertDebit, cls).__setup__()
        cls._error_messages.update({
            'check_not_debited': 'Check "%s" is not debited',
            'no_journal_check_account': 'You need to define a check account '
                'in the journal "%s"',
            })

    def transition_revert(self):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        period_id = Period.find(1, date=self.start.date)
        for check in IssuedCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state != 'debited':
                self.raise_user_error('check_not_debited',
                    error_args=(check.name,))
            if not check.bank_account.journal.issued_check_account:
                self.raise_user_error('no_journal_check_account',
                    error_args=(check.bank_account.journal.name,))

            move, = Move.create([{
                'journal': check.bank_account.journal.id,
                'period': period_id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    check.bank_account.journal.issued_check_account.id,
                'move': move.id,
                'journal': check.bank_account.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': self.start.date,
                })
            lines.append({
                'account': check.bank_account.journal.debit_account.id,
                'move': move.id,
                'journal': check.bank_account.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': self.start.date,
                })
            MoveLine.create(lines)
            IssuedCheck.write([check], {'state': 'issued'})
            Move.post([move])
        return 'end'
