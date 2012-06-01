#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.transaction import Transaction
from trytond.pyson import Eval, Not, In
from trytond.pool import Pool

_STATES = {
    'readonly': Eval('state') != 'draft',
}
_DEPENDS = ['state']

class AccountIssuedCheck(Workflow, ModelSQL, ModelView):
    'Account Issued Check'
    _name = 'account.issued.check'
    _description = __doc__

    name = fields.Char('Number', states=_STATES, depends=_DEPENDS, 
        required=True)
    amount = fields.Numeric('Amount', digits=(16, 2), states=_STATES, 
        depends=_DEPENDS, required=True)
    date_out = fields.Date('Date Out', states=_STATES, depends=_DEPENDS)
    date = fields.Date('Date', states=_STATES, depends=_DEPENDS, required=True)
    debit_date = fields.Date('Debit Date', depends=_DEPENDS,
        states={'invisible': Eval('state') != 'debited'})
    receiving_party = fields.Many2One('party.party', 'Receiving Party', 
        depends=_DEPENDS, states={'invisible': Eval('state') == 'draft'})
    on_order = fields.Char('On Order', states=_STATES, depends=_DEPENDS)
    signatory = fields.Char('Signatory', states=_STATES, depends=_DEPENDS)
    clearing = fields.Selection([
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing', states=_STATES, depends=_DEPENDS)
    origin = fields.Char('Origin', states=_STATES, depends=_DEPENDS)
    voucher = fields.Many2One('account.voucher', 'Voucher', depends=_DEPENDS,
        states={'invisible': Eval('state') == 'draft'})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('debited', 'Debited'),
        ], 'State', readonly=True)

    def __init__(self):
        super( AccountIssuedCheck, self).__init__()
        self._transitions |= set((
                ('draft', 'issued'),
                ('issued', 'debited'),
                ))    
        self._buttons.update({
                'issued': {
                    'invisible': Eval('state') != 'draft',
                    },
                'debited': {
                    'invisible': Eval('state') != 'issued',
                    },
                })    

    def default_date_out(self):
        date_obj = Pool().get('ir.date')
        return date_obj.today()

    def default_state(self):
        return 'draft'

    @Workflow.transition('issued')
    def issued(self, ids):
        pass
        
    @ModelView.button
    @Workflow.transition('debited')
    def debited(self, ids):
        pass

AccountIssuedCheck()


class AccountThirdCheck(Workflow, ModelSQL, ModelView):
    'Account Third Check'
    _name = 'account.third.check'
    _description = __doc__

    name = fields.Char('Number', states=_STATES, depends=_DEPENDS, 
        required=True)
    amount = fields.Numeric('Amount', digits=(16, 2), states=_STATES, 
        depends=_DEPENDS, required=True)
    date_in = fields.Date('Date In', states=_STATES, depends=_DEPENDS, 
        required=True)
    date = fields.Date('Date', states=_STATES, depends=_DEPENDS, required=True)
    date_out = fields.Date('Date Out', depends=_DEPENDS, readonly=True,
        states={'invisible': In(Eval('state'), ['draft', 'held'])})
    debit_date = fields.Date('Debit Date', depends=_DEPENDS, readonly=True,
        states={'invisible': In(Eval('state'), ['draft', 'held'])})
    source_party = fields.Many2One('party.party', 'Source Party', 
        depends=_DEPENDS, readonly=True,
        states={'invisible': Eval('state') == 'draft'})
    destiny_party = fields.Many2One('party.party', 'Destiny Party', 
        depends=_DEPENDS, readonly=True,
        states={'invisible': Eval('state') != 'delivered'})
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
    voucher_in = fields.Many2One('account.voucher', 'Origin Voucher', depends=_DEPENDS, 
        readonly=True, states={'invisible': Eval('state') == 'draft'})
    voucher_out = fields.Many2One('account.voucher', 'Target Voucher', depends=_DEPENDS, 
        readonly=True, states={'invisible': Eval('state') != 'delivered'})
    reject_debit_note = fields.Many2One('account.invoice', 'Debit Note', 
        depends=_DEPENDS, readonly=True)  # TODO
    bank = fields.Many2One('account.bank', 'Bank', states=_STATES,
        depends=_DEPENDS, required=True)
    account_bank_out = fields.Many2One('account.party.bank', 'Bank Account', 
        depends=_DEPENDS, states={'invisible': Eval('state') != 'deposited'},
        readonly=True)

    def __init__(self):
        super(AccountThirdCheck, self).__init__()
        self._transitions |= set((
                ('draft', 'held'),
                ('held', 'deposited'),
                ('held', 'delivered'),
                ('deposited', 'rejected'),
                ('delivered', 'rejected'),
                ))    
        self._buttons.update({
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
                    'invisible': ~Eval('state').in_(['deposited', 'delivered']),
                    },
                })    

    def default_date_in(self):
        date_obj = Pool().get('ir.date')
        return date_obj.today()

    def default_state(self):
        return 'draft'

    @Workflow.transition('held')
    def held(self, ids):
        pass
        
    @ModelView.button
    @Workflow.transition('deposited')
    def deposited(self, ids):
        pass

    @Workflow.transition('delivered')
    def delivered(self, ids):
        pass

    @ModelView.button
    @Workflow.transition('rejected')
    def rejected(self, ids):
        pass

AccountThirdCheck()


class AccountVoucherThirdCheck(ModelSQL):
    'Invoice Line - Tax'
    _name = 'account.voucher-account.third.check'
    _table = 'account_voucher_account_third_check'
    _description = __doc__

    voucher = fields.Many2One('account.voucher', 'Voucher',
        ondelete='CASCADE', select=True, required=True)
    third_check = fields.Many2One('account.third.check', 'Third Check',
        ondelete='RESTRICT', required=True)

AccountVoucherThirdCheck()


class AccountVoucher(ModelSQL, ModelView):
    'Account Check Voucher'
    _name = 'account.voucher'
    _description = __doc__

    def amount_total(self, ids, name):
        amount = super(AccountVoucher, self).amount_total(ids, name)
        for voucher in self.browse(ids):
            if voucher.third_check:
                for t_check in voucher.third_check:
                    amount[voucher.id] += t_check.amount
            if voucher.issued_check:
                for i_check in voucher.issued_check:
                    amount[voucher.id] += i_check.amount
            if voucher.third_pay_checks:
                for check in voucher.third_pay_checks:
                    amount[voucher.id] += check.amount
        return amount

    def amount_checks(self, ids, name):
        res = {}
        amount = 0
        for voucher in self.browse(ids):
            if voucher.issued_check:
                for i_check in voucher.issued_check:
                    amount += i_check.amount
            if voucher.third_check:
                for t_check in voucher.third_check:
                    amount += t_check.amount
            if voucher.third_pay_checks:
                for check in voucher.third_pay_checks:
                    amount += check.amount
            res[voucher.id] = amount
        return res

    def check_amount(self, checks):
        check_amount = 0
        for check in checks:
            check_amount += check.get('amount')
        return check_amount

    def prepare_moves(self, voucher_id):
        pre_move = super(AccountVoucher, self).prepare_moves(voucher_id)
        voucher = self.browse(voucher_id)
        period_obj = Pool().get('account.period')
        if voucher.voucher_type == 'receipt':
            if voucher.third_check:
                third_check_amount = 0
                for t_check in voucher.third_check:
                    third_check_amount += t_check.amount

                debit = Decimal(str(third_check_amount))
                credit = Decimal('0.00')

                pre_move['new_moves'].append({
                    'name': voucher.number,
                    'debit': debit,
                    'credit': credit,
                    'account': voucher.journal.third_check_account.id,
                    'move': pre_move.get('move_id'),
                    'journal': voucher.journal.id,
                    'period': period_obj.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })

        if voucher.voucher_type == 'payment':
            if voucher.issued_check:
                issued_check_amount = 0
                for i_check in voucher.issued_check:
                    issued_check_amount += i_check.amount
                debit = Decimal('0.00')
                credit = Decimal(str(issued_check_amount))
                pre_move['new_moves'].append({
                    'name': voucher.number,
                    'debit': debit,
                    'credit': credit,
                    'account': voucher.journal.issued_check_account.id,
                    'move': pre_move.get('move_id'),
                    'journal': voucher.journal.id,
                    'period': period_obj.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })
            if voucher.third_pay_checks:
                third_paycheck_amount = 0
                for tp_check in voucher.third_pay_checks:
                    third_paycheck_amount += tp_check.amount
                debit = Decimal('0.00')
                credit = Decimal(str(third_paycheck_amount))
                pre_move['new_moves'].append({
                    'name': voucher.number,
                    'debit': debit,
                    'credit': credit,
                    'account': voucher.journal.third_check_account.id,
                    'move': pre_move.get('move_id'),
                    'journal': voucher.journal.id,
                    'period': period_obj.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })

        return pre_move

    @ModelView.button
    def post(self, voucher_id):
        super(AccountVoucher, self).post(voucher_id)
        third_check_obj = Pool().get('account.third.check')
        issued_check_obj = Pool().get('account.issued.check')
        date_obj = Pool().get('ir.date')
        
        voucher = self.browse(voucher_id[0])
        if voucher.issued_check:
            check_ids = [x.id for x in voucher.issued_check]
            issued_check_obj.write(check_ids, {
                'receiving_party': voucher.party.id,
            })
            issued_check_obj.issued(check_ids)
        if voucher.third_check:
            check_ids = [x.id for x in voucher.third_check]
            third_check_obj.write(check_ids, {
                'source_party': voucher.party.id,
            })
            third_check_obj.held(check_ids)
        if voucher.third_pay_checks:
            check_ids = [x.id for x in voucher.third_pay_checks]
            third_check_obj.write(check_ids, {
                'destiny_party': voucher.party.id,
                'date_out': date_obj.today(),
            })
            third_check_obj.delivered(check_ids)
        return True

    issued_check = fields.One2Many('account.issued.check', 'voucher',
        'Issued Checks',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': In(Eval('state'), ['posted']),
        })
    third_pay_checks = fields.Many2Many('account.voucher-account.third.check',
        'voucher', 'third_check', 'Third Checks',
        domain=[('state', '=', 'held')],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': In(Eval('state'), ['posted']),
        })
    third_check = fields.One2Many('account.third.check', 'voucher_in',
        'Third Checks',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
            'readonly': In(Eval('state'), ['posted']),
        })
    total_checks = fields.Function(fields.Float('Checks'), 'amount_checks')

AccountVoucher()


class JournalCheck(ModelSQL, ModelView):
    'Account Check Voucher'
    _name = 'account.journal'
    _description = __doc__

    third_check_account = fields.Many2One('account.account',
        'Third Check Account')
    issued_check_account = fields.Many2One('account.account',
        'Issued Check Account')

JournalCheck()


class ThirdCheckDepositStart(ModelView):
    _name = 'account.third.check.deposit.start'

    bank_account = fields.Many2One('account.party.bank', 'Bank Account',
        required=True)
    date = fields.Date('Date', required=True)

    def default_date(self):
        date_obj = Pool().get('ir.date')
        return date_obj.today()
    
ThirdCheckDepositStart()


class ThirdCheckDeposit(Wizard):
    'Third Check Deposit'
    _name = 'account.third.check.deposit'

    start = StateView('account.third.check.deposit.start',
        'account_check_ar.view_third_check_deposit', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Deposit', 'deposit', 'tryton-ok', default=True),
            ])
    deposit = StateTransition()
    
    def __init__(self):
        super( ThirdCheckDeposit, self).__init__()
        self._error_messages.update({
            'check_not_held': 'Check "%s" is not in held,',
            })

    def transition_deposit(self, session):
        third_check_obj = Pool().get('account.third.check')
        move_obj = Pool().get('account.move')
        move_line_obj = Pool().get('account.move.line')
        period_id = Pool().get('account.period').find(1, 
            date=session.start.date)

        for check in third_check_obj.browse(Transaction().context.get(
            'active_ids')):
            if check.state != 'held':
                self.raise_user_error('check_not_held', 
                    error_args=(check.name,))
            else:
                move_id = move_obj.create({
                    'journal': check.voucher_in.journal.id,
                    'state': 'draft',
                    'period': period_id,
                    'date': session.start.date,
                })
                move_line_obj.create({
                    'name': 'Check Deposit ' + check.name,
                    'account': session.start.bank_account.journal.debit_account.id,
                    'move': move_id,
                    'journal': check.voucher_in.journal.id,
                    'period': period_id,
                    'debit': check.amount,
                    'credit': Decimal('0.0'),
                    'date': session.start.date,
                })
                move_line_obj.create({
                    'name': 'Check Deposit ' + check.name,
                    'account': check.voucher_in.journal.third_check_account.id,
                    'move': move_id,
                    'journal': check.voucher_in.journal.id,
                    'period': period_id,
                    'debit': Decimal('0.0'),
                    'credit': check.amount,
                    'date': session.start.date,
                })
                third_check_obj.write([check.id], {
                    'account_bank_out': session.start.bank_account.id
                })
                third_check_obj.deposited([check.id])
                move_obj.write([move_id], {'state': 'posted'})
        return 'end'
        
ThirdCheckDeposit()
