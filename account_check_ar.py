# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.modules.currency.fields import Monetary
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool
from trytond.pyson import Bool, Eval, In, And, Or, Id
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

_STATES = {
    'readonly': Eval('state') != 'draft',
    }
_ZERO = Decimal('0.0')


class AccountCheckbook(Workflow, ModelSQL, ModelView):
    'Account Checkbook'
    __name__ = 'account.checkbook'

    name = fields.Char('Name', states=_STATES)
    bank_account = fields.Many2One('bank.account', 'Bank Account',
        required=True, domain=[('owners', 'in', [Eval('party_company', 0)])],
        context={'owners': [Eval('party_company')]},
        depends={'party_company'}, states=_STATES)
    party_company = fields.Function(fields.Many2One('party.party', 'Company'),
        'get_party_company')
    sequence = fields.Many2One('ir.sequence', "Sequence", required=True,
        domain=[('sequence_type', '=',
            Id('account_check_ar', 'sequence_type_account_checkbook'))])
    electronic = fields.Boolean('e-Checkbook', states=_STATES)
    last_number = fields.Integer('Last Number', states={
        'invisible': Bool(Eval('electronic')),
        'required': ~Bool(Eval('electronic')),
        })
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(AccountCheckbook, cls).__setup__()
        cls._order = [
            ('id', 'DESC'),
            ]
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'draft'),
            ('active', 'closed'),
            ('closed', 'active'),
            ))
        cls._buttons.update({
            'draft': {
                'invisible': Eval('state').in_(['draft', 'closed']),
                'depends': ['state'],
                },
            'activate': {
                'invisible': Eval('state') == 'active',
                'depends': ['state'],
                },
            'close': {
                'invisible': Eval('state') != 'active',
                'depends': ['state'],
                },
            })

    @staticmethod
    def default_party_company():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            return Company(Transaction().context['company']).party.id

    @staticmethod
    def default_electronic():
        return False

    @staticmethod
    def default_state():
        return 'draft'

    def get_party_company(self, name=None):
        return self.default_party_company()

    @classmethod
    def copy(cls, checkbooks, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('name', None)
        return super(AccountCheckbook, cls).copy(checkbooks, default=default)

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, checkbooks):
        IssuedCheck = Pool().get('account.issued.check')

        for checkbook in checkbooks:
            checks = IssuedCheck.search([('checkbook', '=', checkbook.id)])
            if checks:
                raise UserError(
                    gettext('account_check_ar.msg_checkbook_to_draft'))

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, checkbooks):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('closed')
    def close(cls, checkbooks):
        pass

    @classmethod
    def delete(cls, checkbooks):
        for c in checkbooks:
            if c.state != 'draft':
                raise UserError(
                    gettext('account_check_ar.msg_delete_checkbook'))
        return super(AccountCheckbook, cls).delete(checkbooks)


class AccountIssuedCheck(ModelSQL, ModelView):
    'Account Issued Check'
    __name__ = 'account.issued.check'

    _states = {'readonly': Eval('state') != 'draft'}

    name = fields.Char('Number', states={
        'required': Eval('state') != 'draft',
        'readonly': Eval('state') != 'draft',
        'invisible': And(Bool(Eval('checkbook')), Eval('state') == 'draft'),
        })
    amount = Monetary("Amount", currency='currency', digits='currency',
        required=True, states=_states, depends={'checkbook', 'bank_account'})
    checkbook = fields.Many2One('account.checkbook', 'Checkbook',
        ondelete='RESTRICT', domain=[('state', 'in', ['active'])],
        states=_states)
    electronic = fields.Boolean('e-Check', states={
        'readonly': Or(Bool(Eval('checkbook')), Eval('state') != 'draft'),
        })
    date_out = fields.Date('Date Out', states=_states)
    date = fields.Date('Date', required=True, states=_states)
    debit_date = fields.Date('Debit Date', readonly=True,
        states={'invisible': Eval('state') != 'debited'})
    receiving_party = fields.Many2One('party.party', 'Receiving Party',
        states={
            'invisible': Eval('state') == 'draft',
            'readonly': Eval('state') != 'draft',
            })
    on_order = fields.Char('On Order', states=_states)
    signatory = fields.Char('Signatory', states=_states)
    clearing = fields.Selection([
        (None, ''),
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_states)
    origin = fields.Char('Origin', states=_states)
    voucher = fields.Many2One('account.voucher', 'Voucher', readonly=True,
        states={'invisible': Eval('state') == 'draft'})
    cash_move = fields.Many2One('account.move', 'Cash Move', readonly=True,
        states={'invisible': Eval('state') == 'draft'})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('debited', 'Debited'),
        ('canceled', 'Canceled'),
        ], 'State', readonly=True)
    bank_account = fields.Many2One('bank.account', 'Bank Account',
        required=True, domain=[('owners', 'in', [Eval('party_company', 0)])],
        context={'owners': [Eval('party_company')]},
        states=_states, depends={'party_company'})
    party_company = fields.Function(fields.Many2One('party.party', 'Company'),
        'get_party_company')
    currency = fields.Function(fields.Many2One(
        'currency.currency', "Currency"), 'on_change_with_currency')

    del _states

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
            'calculate_remaining_amount': {
                'invisible': ~Eval('_parent_voucher.state').in_(
                    ['draft', 'calculated']),
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

    @fields.depends('checkbook')
    def on_change_checkbook(self):
        self.bank_account = None
        self.name = None
        if self.checkbook:
            if self.checkbook.electronic is False and \
                    self.checkbook.sequence.number_next > \
                    self.checkbook.last_number:
                raise UserError(
                    gettext(
                        'account_check_ar.msg_checkbook_last_number_reached'))
            self.bank_account = self.checkbook.bank_account
            self.electronic = self.checkbook.electronic

    @fields.depends('checkbook', 'bank_account')
    def on_change_with_currency(self, name=None):
        if self.bank_account:
            return self.bank_account.currency.id

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

    @ModelView.button_change('voucher',
        '_parent_voucher.amount_invoices', '_parent_voucher.amount')
    def calculate_remaining_amount(self):
        self.amount = self.voucher.amount_invoices - self.voucher.amount


class AccountThirdCheck(ModelSQL, ModelView):
    'Account Third Check'
    __name__ = 'account.third.check'

    _states = {'readonly': Eval('state') != 'draft'}

    name = fields.Char('Number',
        states={'required': Eval('state') != 'draft'})
    currency = fields.Many2One('currency.currency', 'Currency', required=True)
    amount = Monetary("Amount", currency='currency', digits='currency',
        required=True, states=_states)
    date_in = fields.Date('Date In', required=True, states=_states)
    date = fields.Date('Date', required=True, states=_states)
    date_out = fields.Date('Date Out', readonly=True,
        states={'invisible': In(Eval('state'), ['draft', 'held'])})
    debit_date = fields.Date('Debit Date', readonly=True,
        states={'invisible': In(Eval('state'), ['draft', 'held'])})
    source_party = fields.Many2One('party.party', 'Source Party',
        readonly=True, states={'invisible': Eval('state') == 'draft'})
    destiny_party = fields.Many2One('party.party', 'Destiny Party',
        readonly=True, states={'invisible': Eval('state') != 'delivered'})
    not_to_order = fields.Boolean('Not to order', states=_states)
    electronic = fields.Boolean('e-Check', states=_states)
    on_order = fields.Char('On Order', states=_states)
    signatory = fields.Char('Signatory', states=_states)
    endorsed = fields.Char('Endorsed', states=_states)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('held', 'Held'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
        ('reverted', 'Reverted'),
        ], 'State', readonly=True)
    vat = fields.Char('Vat', states=_states)
    clearing = fields.Selection([
        (None, ''),
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_states)
    origin = fields.Char('Origin', states=_states)
    voucher_in = fields.Many2One('account.voucher', 'Origin Voucher',
        readonly=True, states={'invisible': Eval('state') == 'draft'})
    voucher_out = fields.Many2One('account.voucher', 'Target Voucher',
        readonly=True, states={'invisible': Eval('state') != 'delivered'})
    reject_debit_note = fields.Many2One('account.invoice', 'Debit Note',
        readonly=True)  # TODO
    bank = fields.Many2One('bank', 'Bank', required=True, states=_states)
    account_bank_out = fields.Many2One('bank.account', 'Bank Account',
        readonly=True, states={'invisible': Eval('state') != 'deposited'})

    del _states

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order = [
            ('date', 'ASC'),
            ]
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
    def validate(cls, checks):
        cls.check_duplicate_check(checks)

    @classmethod
    def check_duplicate_check(cls, checks):
        for check in checks:
            if cls.search_count([
                    ('id', '!=', check.id),
                    ('bank', '=', check.bank),
                    ('name', '=', check.name),
                    ('source_party', '=', check.source_party),
                    ]) > 0:
                raise UserError(gettext(
                    'account_check_ar.msg_third_check_already_exists',
                    check=check.name))

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
        required=True, ondelete='CASCADE')
    third_check = fields.Many2One('account.third.check', 'Third Check',
        required=True, ondelete='CASCADE')


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

        company = Transaction().context.get('company')
        date = Date.today()
        period = Period.find(company, date=date)
        for check in self.records:
            if check.state != 'draft':
                raise UserError(gettext(
                    'account_check_ar.msg_check_not_draft', check=check.name))
            if not self.start.journal.third_check_account:
                raise UserError(gettext(
                    'account_voucher_ar.msg_no_journal_check_account',
                    journal=self.start.journal.name))

            move, = Move.create([{
                'journal': self.start.journal.id,
                'period': period.id,
                'date': date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account': self.start.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period.id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': date,
                'maturity_date': check.date,
                })
            lines.append({
                'account': self.start.credit_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period.id,
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

        company = Transaction().context.get('company')
        period = Period.find(company, date=self.start.date)
        for check in self.records:
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
                'period': period.id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    self.start.bank_account.debit_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period.id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': self.start.date,
                })
            lines.append({
                'account':
                    self.start.bank_account.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period.id,
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

        company = Transaction().context.get('company')
        period = Period.find(company, date=self.start.date)
        for check in self.records:
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
                'period': period.id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    check.account_bank_out.debit_account.id,
                'move': move.id,
                'journal': check.account_bank_out.journal.id,
                'period': period.id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': self.start.date,
                })
            lines.append({
                'account':
                    check.account_bank_out.journal.third_check_account.id,
                'move': move.id,
                'journal': check.account_bank_out.journal.id,
                'period': period.id,
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


class IssuedCheckDebit(Wizard):
    'Issued Check Debit'
    __name__ = 'account.issued.check.debit'

    start = StateView('account.issued.check.debit.start',
        'account_check_ar.view_issued_check_debit', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Debit', 'debit', 'tryton-ok', default=True),
            ])
    debit = StateTransition()

    def default_start(self, fields):
        Date = Pool().get('ir.date')
        return {
            'bank_account': self.record.bank_account.id,
            'date': Date.today(),
            }

    def transition_debit(self):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        company = Transaction().context.get('company')
        period = Period.find(company, date=self.start.date)
        for check in self.records:
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
                'period': period.id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    self.start.bank_account.journal.issued_check_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period.id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': self.start.date,
                })
            lines.append({
                'account': self.start.bank_account.debit_account.id,
                'move': move.id,
                'journal': self.start.bank_account.journal.id,
                'period': period.id,
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

        company = Transaction().context.get('company')
        period = Period.find(company, date=self.start.date)
        for check in self.records:
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
                'period': period.id,
                'date': self.start.date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account':
                    check.bank_account.journal.issued_check_account.id,
                'move': move.id,
                'journal': check.bank_account.journal.id,
                'period': period.id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': self.start.date,
                })
            lines.append({
                'account': check.bank_account.debit_account.id,
                'move': move.id,
                'journal': check.bank_account.journal.id,
                'period': period.id,
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

        company = Transaction().context.get('company')
        date = Date.today()
        period = Period.find(company, date=date)
        for check in self.records:
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
                'period': period.id,
                'date': date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account': self.start.journal.rejected_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period.id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': date,
                })
            lines.append({
                'account': self.start.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period.id,
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

        company = Transaction().context.get('company')
        date = Date.today()
        period = Period.find(company, date=date)
        for check in self.records:
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
                'period': period.id,
                'date': date,
                'description': 'Cheque: ' + check.name,
                }])
            lines = []
            lines.append({
                'account': self.start.journal.rejected_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period.id,
                'debit': _ZERO,
                'credit': check.amount,
                'date': date,
                })
            lines.append({
                'account': self.start.journal.third_check_account.id,
                'move': move.id,
                'journal': self.start.journal.id,
                'period': period.id,
                'debit': check.amount,
                'credit': _ZERO,
                'date': date,
                })
            MoveLine.create(lines)
            ThirdCheck.write([check], {'state': 'reverted'})
            Move.post([move])
        return 'end'


class IssuedCheckCashStart(ModelView):
    'Issued Check Cash Start'
    __name__ = 'account.issued.check.cash.start'

    checkbook = fields.Many2One('account.checkbook', 'Checkbook',
        required=True, domain=[('state', 'in', ['active'])])
    bank_account = fields.Function(fields.Many2One('bank.account',
        'Bank Account'), 'on_change_with_bank_account')
    number = fields.Integer('Number', required=True)
    date_out = fields.Date('Date Out', required=True)
    date = fields.Date('Date', required=True)
    amount = Monetary("Amount", currency='currency', digits='currency',
        required=True, depends={'checkbook', 'bank_account'})
    currency = fields.Function(fields.Many2One(
        'currency.currency', "Currency"), 'on_change_with_currency')
    cash_account = fields.Many2One('account.account',
        'Cash Account', domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ('company', '=', Eval('context', {}).get('company', -1)),
            ], required=True)

    @staticmethod
    def default_date_out():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @fields.depends('checkbook')
    def on_change_with_bank_account(self, name=None):
        if self.checkbook:
            return self.checkbook.bank_account.id

    @fields.depends('checkbook')
    def on_change_with_number(self, name=None):
        if self.checkbook:
            return self.checkbook.sequence.number_next

    @staticmethod
    def default_amount():
        return _ZERO

    @fields.depends('checkbook', 'bank_account')
    def on_change_with_currency(self, name=None):
        if self.bank_account:
            return self.bank_account.currency.id


class IssuedCheckCash(Wizard):
    'Issued Check Cash'
    __name__ = 'account.issued.check.cash'

    start = StateView('account.issued.check.cash.start',
        'account_check_ar.view_issued_check_cash_start', [
            Button('Abort', 'end', 'tryton-cancel'),
            Button('Proceed', 'cash', 'tryton-ok', default=True),
            ])
    cash = StateTransition()

    def transition_cash(self):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')

        company = Transaction().context.get('company')
        period = Period.find(company, date=self.start.date)
        checkbook = self.start.checkbook
        number = self.start.number
        if checkbook.sequence.number_next == int(number):
            # Clean number to get next one from sequence
            number = None
        elif checkbook.sequence.number_next < int(number):
            number = '%%0%sd' % checkbook.sequence.padding % number
            raise UserError(
                gettext('account_check_ar.msg_number_not_valid',
                    number=number))
        if number:
            # Previous number: not from sequence
            number = '%%0%sd' % checkbook.sequence.padding % number
            check_exists = IssuedCheck.search([
                    ('name', '=', number),
                    ('bank_account', '=', checkbook.bank_account.id),
                    ])
            if check_exists:
                raise UserError(
                    gettext('account_check_ar.msg_check_already_exists',
                        number=number))
        check, = IssuedCheck.create([{
            'name': number and number or checkbook.sequence.get(),
            'checkbook': checkbook.id,
            'bank_account': self.start.bank_account.id,
            'amount': self.start.amount,
            'date_out': self.start.date_out,
            'date': self.start.date,
            'debit_date': self.start.date,
            'electronic': checkbook.electronic,
            'state': 'issued',
            }])

        move, = Move.create([{
            'journal': self.start.bank_account.journal.id,
            'period': period.id,
            'date': self.start.date,
            'description': 'Cobro Cheque propio: ' + check.name,
            }])
        lines = []
        lines.append({
            'account':
                self.start.bank_account.credit_account.id,
            'move': move.id,
            'debit': _ZERO,
            'credit': check.amount,
            })
        lines.append({
            'account': self.start.cash_account.id,
            'move': move.id,
            'debit': check.amount,
            'credit': _ZERO,
            })

        MoveLine.create(lines)
        Move.post([move])
        IssuedCheck.write([check], {
            'state': 'debited',
            'cash_move': move
            })

        return 'end'


class IssuedCheckCancelStart(ModelView):
    'Issued Check Cancel Start'
    __name__ = 'account.issued.check.cancel.start'

    checkbook = fields.Many2One('account.checkbook', 'Checkbook',
        required=True, domain=[('state', 'in', ['active'])])
    bank_account = fields.Function(fields.Many2One('bank.account',
        'Bank Account'), 'on_change_with_bank_account')
    from_number = fields.Integer('From Number', required=True)
    to_number = fields.Integer('To Number', required=True)
    date = fields.Date('Date', required=True)

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @fields.depends('checkbook')
    def on_change_with_bank_account(self, name=None):
        if self.checkbook:
            return self.checkbook.bank_account.id


class IssuedCheckCancel(Wizard):
    'Issued Check Cancel'
    __name__ = 'account.issued.check.cancel'

    start = StateView('account.issued.check.cancel.start',
        'account_check_ar.view_issued_check_cancel_start', [
            Button('Abort', 'end', 'tryton-cancel'),
            Button('Proceed', 'cancel', 'tryton-ok', default=True),
            ])
    cancel = StateTransition()

    def transition_cancel(self):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')

        if self.start.from_number > self.start.to_number:
            raise UserError(
                gettext('account_check_ar.msg_checkbook_to_number_lower'))
        numbers = range(self.start.from_number, self.start.to_number + 1)
        checkbook = self.start.checkbook
        if self.start.from_number != checkbook.sequence.number_next:
            raise UserError(
                gettext('account_check_ar.msg_checkbook_must_be_next_number'))
        for number in numbers:
            name = '%%0%sd' % checkbook.sequence.padding % number
            check_exists = IssuedCheck.search([
                    ('name', '=', name),
                    ('bank_account', '=', checkbook.bank_account.id),
                    ])
            if check_exists:
                continue
            check, = IssuedCheck.create([{
                'name': checkbook.sequence.get(),
                'checkbook': checkbook.id,
                'bank_account': self.start.bank_account.id,
                'date': self.start.date,
                'state': 'canceled',
                }])

        return 'end'
