#This file is part of the account_check_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.transaction import Transaction
from trytond.pyson import Eval, Not, In
from trytond.pool import Pool

__all__ = ['AccountIssuedCheck', 'AccountThirdCheck',
    'AccountVoucherThirdCheck', 'AccountVoucher', 'Journal',
    'ThirdCheckHeldStart', 'ThirdCheckHeld', 'ThirdCheckDepositStart',
    'ThirdCheckDeposit']

_STATES = {
    'readonly': Eval('state') != 'draft',
}
_DEPENDS = ['state']


class AccountIssuedCheck(Workflow, ModelSQL, ModelView):
    'Account Issued Check'
    __name__ = 'account.issued.check'

    name = fields.Char('Number', required=True, states=_STATES,
        depends=_DEPENDS)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_STATES, depends=_DEPENDS)
    date_out = fields.Date('Date Out', states=_STATES, depends=_DEPENDS)
    date = fields.Date('Date', required=True, states=_STATES, depends=_DEPENDS)
    debit_date = fields.Date('Debit Date',
        states={
            'invisible': Eval('state') != 'debited',
            }, depends=_DEPENDS)
    receiving_party = fields.Many2One('party.party', 'Receiving Party',
        states={
            'invisible': Eval('state') == 'draft',
            }, depends=_DEPENDS)
    on_order = fields.Char('On Order', states=_STATES, depends=_DEPENDS)
    signatory = fields.Char('Signatory', states=_STATES, depends=_DEPENDS)
    clearing = fields.Selection([
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_STATES, depends=_DEPENDS)
    origin = fields.Char('Origin', states=_STATES, depends=_DEPENDS)
    voucher = fields.Many2One('account.voucher', 'Voucher',
        states={
            'invisible': Eval('state') == 'draft',
            }, depends=_DEPENDS)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('debited', 'Debited'),
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(AccountIssuedCheck, cls).__setup__()
        cls._transitions |= set((
                ('draft', 'issued'),
                ('issued', 'debited'),
                ))
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

    @classmethod
    @Workflow.transition('issued')
    def issued(cls, checks):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('debited')
    def debited(self, checks):
        pass


class AccountThirdCheck(Workflow, ModelSQL, ModelView):
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
    bank = fields.Many2One('account.bank', 'Bank', required=True,
        states=_STATES, depends=_DEPENDS)
    account_bank_out = fields.Many2One('account.party.bank', 'Bank Account',
        readonly=True, states={
            'invisible': Eval('state') != 'deposited',
            }, depends=_DEPENDS)

    @classmethod
    def __setup__(cls):
        super(AccountThirdCheck, cls).__setup__()
        cls._transitions |= set((
                ('draft', 'held'),
                ('held', 'deposited'),
                ('held', 'delivered'),
                ('deposited', 'rejected'),
                ('delivered', 'rejected'),
                ))
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

    @classmethod
    @Workflow.transition('held')
    def held(self, checks):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('deposited')
    def deposited(self, checks):
        pass

    @classmethod
    @Workflow.transition('delivered')
    def delivered(self, checks):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('rejected')
    def rejected(self, checks):
        pass


class AccountVoucherThirdCheck(ModelSQL):
    'Account Voucher - Account Third Check'
    __name__ = 'account.voucher-account.third.check'
    _table = 'account_voucher_account_third_check'

    voucher = fields.Many2One('account.voucher', 'Voucher', required=True,
        select=True, ondelete='CASCADE')
    third_check = fields.Many2One('account.third.check', 'Third Check',
        required=True, ondelete='RESTRICT')


class AccountVoucher(ModelSQL, ModelView):
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
    total_checks = fields.Function(fields.Float('Checks'), 'amount_checks')

    def amount_total(self, name):
        amount = super(AccountVoucher, self).amount_total(name)
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

    def amount_checks(self, name):
        amount = 0
        if self.issued_check:
            for i_check in self.issued_check:
                amount += i_check.amount
        if self.third_check:
            for t_check in self.third_check:
                amount += t_check.amount
        if self.third_pay_checks:
            for check in self.third_pay_checks:
                amount += check.amount
        return amount

    @classmethod
    def prepare_moves(cls, voucher):
        pre_move = super(AccountVoucher, cls).prepare_moves(voucher)
        Period = Pool().get('account.period')
        if voucher.voucher_type == 'receipt':
            if voucher.third_check:
                third_check_amount = 0
                for t_check in voucher.third_check:
                    third_check_amount += t_check.amount

                debit = Decimal(str(third_check_amount))
                credit = Decimal('0.00')

                pre_move['move_lines'].append({
                    'debit': debit,
                    'credit': credit,
                    'account': voucher.journal.third_check_account.id,
                    'move': pre_move.get('move').id,
                    'journal': voucher.journal.id,
                    'period': Period.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })

        if voucher.voucher_type == 'payment':
            if voucher.issued_check:
                issued_check_amount = 0
                for i_check in voucher.issued_check:
                    issued_check_amount += i_check.amount
                debit = Decimal('0.00')
                credit = Decimal(str(issued_check_amount))
                pre_move['move_lines'].append({
                    'debit': debit,
                    'credit': credit,
                    'account': voucher.journal.issued_check_account.id,
                    'move': pre_move.get('move').id,
                    'journal': voucher.journal.id,
                    'period': Period.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })
            if voucher.third_pay_checks:
                third_paycheck_amount = 0
                for tp_check in voucher.third_pay_checks:
                    third_paycheck_amount += tp_check.amount
                debit = Decimal('0.00')
                credit = Decimal(str(third_paycheck_amount))
                pre_move['move_lines'].append({
                    'debit': debit,
                    'credit': credit,
                    'account': voucher.journal.third_check_account.id,
                    'move': pre_move.get('move').id,
                    'journal': voucher.journal.id,
                    'period': Period.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })

        return pre_move

    @classmethod
    @ModelView.button
    def post(cls, vouchers):
        super(AccountVoucher, cls).post(vouchers)
        ThirdCheck = Pool().get('account.third.check')
        IssuedCheck = Pool().get('account.issued.check')
        Date = Pool().get('ir.date')

        voucher = vouchers[0]
        if voucher.issued_check:
            IssuedCheck.write(voucher.issued_check, {
                'receiving_party': voucher.party.id,
            })
            IssuedCheck.issued(voucher.issued_check)
        if voucher.third_check:
            ThirdCheck.write(voucher.third_check, {
                'source_party': voucher.party.id,
            })
            ThirdCheck.held(voucher.third_check)
        if voucher.third_pay_checks:
            ThirdCheck.write(voucher.third_pay_checks, {
                'destiny_party': voucher.party.id,
                'date_out': Date.today(),
            })
            ThirdCheck.delivered(voucher.third_pay_checks)


class Journal(ModelSQL, ModelView):
    __name__ = 'account.journal'

    third_check_account = fields.Many2One('account.account',
        'Third Check Account')
    issued_check_account = fields.Many2One('account.account',
        'Issued Check Account')


class ThirdCheckHeldStart(ModelView):
    'Third Check Held Start'
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
            })

    def transition_held(self, session):
        ThirdCheck = Pool().get('account.third.check')
        Move = Pool().get('account.move')
        MoveLine = Pool().get('account.move.line')
        Date = Pool().get('ir.date')

        date = Date.today()
        period_id = Pool().get('account.period').find(1, date)
        for check in ThirdCheck(Transaction().context.get('active_ids')):
            if check.state != 'draft':
                self.raise_user_error('check_not_draft',
                    error_args=(check.name,))
            else:
                move_id = Move.create({
                    'journal': session.start.journal.id,
                    'state': 'draft',
                    'period': period_id,
                    'date': date,
                })
                MoveLine.create({
                    'name': 'Check Held ' + check.name,
                    'account': session.start.journal.third_check_account.id,
                    'move': move_id,
                    'journal': session.start.journal.id,
                    'period': period_id,
                    'debit': check.amount,
                    'credit': Decimal('0.0'),
                    'date': date,
                })
                MoveLine.create({
                    'name': 'Check Held ' + check.name,
                    'account': session.start.journal.credit_account.id,
                    'move': move_id,
                    'journal': session.start.journal.id,
                    'period': period_id,
                    'debit': Decimal('0.0'),
                    'credit': check.amount,
                    'date': date,
                })
                ThirdCheck.held([check.id])
                Move.write([move_id], {'state': 'posted'})
        return 'end'


class ThirdCheckDepositStart(ModelView):
    'Third Check Deposit Start'
    __name__ = 'account.third.check.deposit.start'

    bank_account = fields.Many2One('account.party.bank', 'Bank Account',
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
            'check_not_held': 'Check "%s" is not in held,',
            })

    def transition_deposit(self, session):
        ThirdCheck = Pool().get('account.third.check')
        Move = Pool().get('account.move')
        MoveLine = Pool().get('account.move.line')
        period_id = Pool().get('account.period').find(1,
            date=session.start.date)

        for check in ThirdCheck(Transaction().context.get('active_ids')):
            if check.state != 'held':
                self.raise_user_error('check_not_held',
                    error_args=(check.name,))
            else:
                move_id = Move.create({
                    'journal': session.start.bank_account.journal.id,
                    'state': 'draft',
                    'period': period_id,
                    'date': session.start.date,
                })
                MoveLine.create({
                    'name': 'Check Deposit ' + check.name,
                    'account': \
                        session.start.bank_account.journal.debit_account.id,
                    'move': move_id,
                    'journal': session.start.bank_account.journal.id,
                    'period': period_id,
                    'debit': check.amount,
                    'credit': Decimal('0.0'),
                    'date': session.start.date,
                })
                MoveLine.create({
                    'name': 'Check Deposit ' + check.name,
                    'account': \
                        session.start.bank_account.journal.third_check_account.id,
                    'move': move_id,
                    'journal': session.start.bank_account.journal.id,
                    'period': period_id,
                    'debit': Decimal('0.0'),
                    'credit': check.amount,
                    'date': session.start.date,
                })
                ThirdCheck.write([check.id], {
                    'account_bank_out': session.start.bank_account.id
                })
                ThirdCheck.deposited([check.id])
                Move.write([move_id], {'state': 'posted'})
        return 'end'
