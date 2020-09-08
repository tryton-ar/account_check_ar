# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool
from trytond.pyson import Eval, In
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

_ZERO = Decimal('0.0')


class AccountIssuedCheck(ModelSQL, ModelView):
    'Account Issued Check'
    __name__ = 'account.issued.check'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    name = fields.Char('Number',
        states={'required': Eval('state') != 'draft'},
        depends=_depends)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_states, depends=_depends)
    date_out = fields.Date('Date Out', states=_states, depends=_depends)
    date = fields.Date('Date', required=True,
        states=_states, depends=_depends)
    debit_date = fields.Date('Debit Date', readonly=True,
        states={'invisible': Eval('state') != 'debited'},
        depends=_depends)
    receiving_party = fields.Many2One('party.party', 'Receiving Party',
        states={
            'invisible': Eval('state') == 'draft',
            'readonly': Eval('state') != 'draft',
            },
        depends=_depends)
    on_order = fields.Char('On Order', states=_states, depends=_depends)
    signatory = fields.Char('Signatory', states=_states, depends=_depends)
    clearing = fields.Selection([
        (None, ''),
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_states, depends=_depends)
    origin = fields.Char('Origin', states=_states, depends=_depends)
    voucher = fields.Many2One('account.voucher', 'Voucher', readonly=True,
        states={'invisible': Eval('state') == 'draft'},
        depends=_depends)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('debited', 'Debited'),
        ], 'State', readonly=True)
    bank_account = fields.Many2One('bank.account', 'Bank Account',
        required=True, domain=[('owners', 'in', [Eval('party_company')])],
        context={'owners': [Eval('party_company')]},
        states=_states, depends=_depends + ['party_company'])
    party_company = fields.Function(fields.Many2One('party.party', 'Company'),
        'get_party_company')
    electronic = fields.Boolean('E-Check', states=_states, depends=_depends)

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'issued': {
                'invisible': Eval('state') != 'draft',
                },
            'debited': {
                'invisible': Eval('state') != 'issued',
                },
            })

    @staticmethod
    def default_party_company():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            return Company(Transaction().context['company']).party.id

    def get_party_company(self, name=None):
        return self.default_party_company()

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

    @staticmethod
    def default_electronic():
        return False

    @classmethod
    def copy(cls, checks, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('name', None)
        default.setdefault('state', cls.default_state())
        return super().copy(checks, default=default)

    @classmethod
    def delete(cls, checks):
        if not checks:
            return True
        for check in checks:
            if check.state != 'draft':
                raise UserError(gettext('account_check_ar.msg_delete_check'))
        return super().delete(checks)

    @classmethod
    def issued(cls, checks):
        pass

    @classmethod
    @ModelView.button
    def debited(cls, checks):
        pass


class AccountThirdCheck(ModelSQL, ModelView):
    'Account Third Check'
    __name__ = 'account.third.check'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    name = fields.Char('Number',
        states={'required': Eval('state') != 'draft'},
        depends=_depends)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_states, depends=_depends)
    date_in = fields.Date('Date In', required=True,
        states=_states, depends=_depends)
    date = fields.Date('Date', required=True,
        states=_states, depends=_depends)
    date_out = fields.Date('Date Out', readonly=True,
        states={'invisible': In(Eval('state'), ['draft', 'held'])},
        depends=_depends)
    debit_date = fields.Date('Debit Date', readonly=True,
        states={'invisible': In(Eval('state'), ['draft', 'held'])},
        depends=_depends)
    source_party = fields.Many2One('party.party', 'Source Party',
        readonly=True, states={'invisible': Eval('state') == 'draft'},
        depends=_depends)
    destiny_party = fields.Many2One('party.party', 'Destiny Party',
        readonly=True, states={'invisible': Eval('state') != 'delivered'},
        depends=_depends)
    not_to_order = fields.Boolean('Not to order', states=_states,
        depends=_depends)
    electronic = fields.Boolean('E-Check', states=_states, depends=_depends)
    on_order = fields.Char('On Order', states=_states, depends=_depends)
    signatory = fields.Char('Signatory', states=_states, depends=_depends)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('held', 'Held'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
        ('reverted', 'Reverted'),
        ], 'State', readonly=True)
    vat = fields.Char('Vat', states=_states, depends=_depends)
    clearing = fields.Selection([
        (None, ''),
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_states, depends=_depends)
    origin = fields.Char('Origin', states=_states, depends=_depends)
    voucher_in = fields.Many2One('account.voucher', 'Origin Voucher',
        readonly=True, states={'invisible': Eval('state') == 'draft'},
        depends=_depends)
    voucher_out = fields.Many2One('account.voucher', 'Target Voucher',
        readonly=True, states={'invisible': Eval('state') != 'delivered'},
        depends=_depends)
    reject_debit_note = fields.Many2One('account.invoice', 'Debit Note',
        readonly=True, depends=_depends)  # TODO
    bank = fields.Many2One('bank', 'Bank', required=True,
        states=_states, depends=_depends)
    account_bank_out = fields.Many2One('bank.account', 'Bank Account',
        readonly=True, states={'invisible': Eval('state') != 'deposited'},
        depends=_depends)

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'held': {
                'invisible': Eval('state') != 'draft',
                },
            'deposited': {
                'invisible': ~Eval('state').in_(['held', 'reverted']),
                },
            'delivered': {
                'invisible': Eval('state') != 'held',
                },
            'reverted': {
                'invisible': ~Eval('state').in_(['deposited', 'delivered']),
                },
            'rejected': {
                'invisible': ~Eval('state').in_(['held', 'reverted']),
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

    @staticmethod
    def default_electronic():
        return False

    @classmethod
    def copy(cls, checks, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('name', None)
        default.setdefault('state', cls.default_state())
        return super().copy(checks, default=default)

    @classmethod
    def delete(cls, checks):
        if not checks:
            return True
        for check in checks:
            if check.state != 'draft':
                raise UserError(gettext('account_check_ar.msg_delete_check'))
        return super().delete(checks)

    @classmethod
    @ModelView.button_action('account_check_ar.wizard_third_check_held')
    def held(cls, checks):
        pass

    @classmethod
    @ModelView.button_action('account_check_ar.wizard_third_check_deposit')
    def deposited(cls, checks):
        pass

    @classmethod
    def delivered(cls, checks):
        pass

    @classmethod
    @ModelView.button
    def reverted(cls, checks):
        pass

    @classmethod
    @ModelView.button_action('account_check_ar.wizard_third_check_reject')
    def rejected(cls, checks):
        pass


class AccountVoucherThirdCheck(ModelSQL):
    'Account Voucher - Account Third Check'
    __name__ = 'account.voucher-account.third.check'
    _table = 'account_voucher_account_third_check'

    voucher = fields.Many2One('account.voucher', 'Voucher',
        required=True, select=True, ondelete='CASCADE')
    third_check = fields.Many2One('account.third.check', 'Third Check',
        required=True, select=True, ondelete='CASCADE')


class Journal(ModelSQL, ModelView):
    __name__ = 'account.journal'

    third_check_account = fields.Many2One('account.account',
        'Third Check Account', domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ])
    issued_check_account = fields.Many2One('account.account',
        'Issued Check Account', domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ])
    rejected_check_account = fields.Many2One('account.account',
        'Rejected Check Account', domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ])


class ThirdCheckHeldStart(ModelView):
    'Third Check Held'
    __name__ = 'account.third.check.held.start'

    journal = fields.Many2One('account.journal', 'Journal', required=True)
    credit_account = fields.Many2One('account.account', 'Credit Account',
        required=True, domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ('company', '=', Eval('context', {}).get('company', -1)),
            ])


class ThirdCheckHeld(Wizard):
    'Third Check Held'
    __name__ = 'account.third.check.held'

    start = StateView('account.third.check.held.start',
        'account_check_ar.view_third_check_held', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Held', 'held', 'tryton-ok', default=True),
            ])
    held = StateTransition()

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
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_draft', check=check.name))
            if not self.start.journal.third_check_account:
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=self.start.journal.name))

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
                'account': self.start.credit_account.id,
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

    def transition_deposit(self):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        period_id = Period.find(1, date=self.start.date)
        for check in ThirdCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state not in ['held', 'reverted']:
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_held',
                    check=check.name))
            if not self.start.bank_account.journal.third_check_account:
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=self.start.bank_account.journal.name))

            move, = Move.create([{
                'journal': self.start.bank_account.journal.id,
                'period': period_id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    self.start.bank_account.debit_account.id,
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

    def transition_revert(self):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        period_id = Period.find(1, date=self.start.date)
        for check in ThirdCheck.browse(Transaction().context.get(
                'active_ids')):
            if check.state not in ['deposited', 'delivered']:
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_deposited',
                    check=check.name))
            if not check.account_bank_out.journal.third_check_account:
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=check.account_bank_out.journal.name))

            move, = Move.create([{
                'journal': check.account_bank_out.journal.id,
                'period': period_id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    check.account_bank_out.debit_account.id,
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
                'state': 'reverted',
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
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_issued',
                    check=check.name))
            if not self.start.bank_account.journal.issued_check_account:
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=self.start.bank_account.journal.name))

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
                'account': self.start.bank_account.debit_account.id,
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
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_debited',
                    check=check.name))
            if not check.bank_account.journal.issued_check_account:
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=check.bank_account.journal.name))

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
                'account': check.bank_account.debit_account.id,
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


class ThirdCheckRejectStart(ModelView):
    'Third Check Reject'
    __name__ = 'account.third.check.reject.start'

    journal = fields.Many2One('account.journal', 'Journal', required=True)


class ThirdCheckReject(Wizard):
    'Third Check Reject'
    __name__ = 'account.third.check.reject'

    start = StateView('account.third.check.reject.start',
        'account_check_ar.view_third_check_reject', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Reject', 'reject', 'tryton-ok', default=True),
            ])
    reject = StateTransition()

    def transition_reject(self):
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
            if check.state not in ['held', 'reverted']:
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_held',
                    check=check.name))
            if (not self.start.journal.third_check_account or
                    not self.start.journal.rejected_check_account):
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=self.start.journal.name))

            move, = Move.create([{
                'journal': self.start.journal.id,
                'period': period_id,
                'date': date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account': self.start.journal.rejected_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': date,
                })
            lines.append({
                'account': self.start.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': date,
                })
            MoveLine.create(lines)
            ThirdCheck.write([check], {'state': 'rejected'})
            Move.post([move])
        return 'end'


class ThirdCheckRevertRejectStart(ModelView):
    'Revert Third Check Reject'
    __name__ = 'account.third.check.revert_reject.start'

    journal = fields.Many2One('account.journal', 'Journal', required=True)


class ThirdCheckRevertReject(Wizard):
    'Revert Third Check Reject'
    __name__ = 'account.third.check.revert_reject'

    start = StateView('account.third.check.revert_reject.start',
        'account_check_ar.view_third_check_revert_reject', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert Reject', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()

    def transition_revert(self):
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
            if check.state != 'rejected':
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_rejected',
                    check=check.name))
            if (not self.start.journal.third_check_account or
                    not self.start.journal.rejected_check_account):
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=self.start.journal.name))

            move, = Move.create([{
                'journal': self.start.journal.id,
                'period': period_id,
                'date': date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account': self.start.journal.rejected_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period_id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': date,
                })
            lines.append({
                'account': self.start.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period_id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': date,
                })
            MoveLine.create(lines)
            ThirdCheck.write([check], {'state': 'reverted'})
            Move.post([move])
        return 'end'
