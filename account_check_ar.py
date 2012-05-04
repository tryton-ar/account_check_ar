#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelWorkflow, ModelView, ModelSQL, fields
from decimal import Decimal
from trytond.pyson import Eval, Not, In
from trytond.pool import Pool

_STATES = {
    'readonly': In(Eval('state'), ['posted']),
}


class AccountIssuedCheck(ModelSQL, ModelView):
    'Account Issued Check'
    _name = 'account.issued.check'
    _description = __doc__

    name = fields.Char('Number')
    amount = fields.Float('Amount')
    date_out = fields.Date('Date Out')
    date = fields.Date('Date')
    debit_date = fields.Date('Debit Date')
    receiving_party_id = fields.Many2One('party.party', 'Receiving Party')
    on_order = fields.Char('On Order')
    signatory = fields.Char('Signatory')
    clearing = fields.Selection([
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing')
    origin = fields.Char('Origin')
    voucher_id = fields.Many2One('account.voucher', 'Voucher')
    issued = fields.Boolean('Issued')

AccountIssuedCheck()


class AccountThirdCheck(ModelWorkflow, ModelSQL, ModelView):
    'Account Third Check'
    _name = 'account.third.check'
    _description = __doc__

    name = fields.Char('Number')
    amount = fields.Float('Amount')
    date_in = fields.Date('Date')
    date = fields.Date('Date')
    date_out = fields.Date('Date Out')
    debit_date = fields.Date('Debit Date')
    source_party_id = fields.Many2One('party.party', 'Source Party')
    destiny_party_id = fields.Many2One('party.party', 'Destiny Party')
    on_order = fields.Char('On Order')
    signatory = fields.Char('Signatory')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('C', 'Cartera'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
        ], 'State', readonly=True)
    vat = fields.Char('Vat')
    clearing = fields.Selection([
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
        ], 'Clearing')
    origin = fields.Char('Origin')
    voucher_id = fields.Many2One('account.voucher', 'Voucher')
    issued = fields.Boolean('Issued')
    reject_debit_note = fields.Many2One('account.invoice', 'Debit Note')  # TODO

    def wkf_draft(self, check_id):
        self.write(check_id.id, {'state': 'draft'})
        return True

    def wkf_cartera(self, check_id):
        self.write(check_id.id, {'state': 'C'})
        return True

    def wkf_deposited(self, check_id):
        return True

    def wkf_delivered(self, check_id):
        self.write(check_id.id, {'state': 'delivered'})
        return True

    def default_state(self):
        return 'draft'

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


class VoucherCheck(ModelSQL, ModelView):
    'Account Check Voucher'
    _name = 'account.voucher'
    _description = __doc__

    def amount_total(self, ids, name):
        check_amount = 0
        amount = super(VoucherCheck, self).amount_total(ids, name)
        for voucher in self.browse(ids):
            if voucher.third_check:
                for t_check in voucher.third_check:
                    check_amount += t_check.amount
            if voucher.issued_check:
                for i_check in voucher.issued_check:
                    check_amount += i_check.amount
            if voucher.third_pay_checks:
                for check in voucher.third_pay_checks:
                    check_amount += check.amount
            amount[voucher.id] = amount[voucher.id] + check_amount
        return amount

    def on_change_pay_amount_1(self, vals):
        data = super(VoucherCheck, self).on_change_pay_amount_1(vals)
        third_check_amount = 0
        issued_check_amount = 0
        third_pay_check_amount = 0
        if vals.get('third_check'):
            third_check_amount = self.check_amount(vals.get('third_check'))
        if vals.get('issued_check'):
            issued_check_amount = self.check_amount(vals.get('issued_check'))
        if vals.get('third_pay_checks'):
            third_pay_checks_amount = self.check_amount(
                    vals.get('third_pay_checks'))
        data['amount'] = data['amount'] + third_check_amount \
                + issued_check_amount
        return data

    def on_change_pay_amount_2(self, vals):
        data = super(VoucherCheck, self).on_change_pay_amount_2(vals)
        third_check_amount = 0
        issued_check_amount = 0
        third_pay_check_amount = 0
        if vals.get('third_check'):
            third_check_amount = self.check_amount(vals.get('third_check'))
        if vals.get('issued_check'):
            issued_check_amount = self.check_amount(vals.get('issued_check'))
        if vals.get('third_pay_checks'):
            third_pay_checks_amount = self.check_amount(
                    vals.get('third_pay_checks'))
        data['amount'] = data['amount'] + third_check_amount \
                + issued_check_amount
        return data

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

    def on_change_third_check(self, vals):
        res = {}
        third_pay_check_amount = self.check_amount(
                vals.get('third_pay_checks'))
        third_check_amount = self.check_amount(vals.get('third_check'))
        issued_check_amount = self.check_amount(vals.get('issued_check'))
        res['total_checks'] = third_check_amount + issued_check_amount \
                + third_pay_check_amount
        res['amount'] = vals.get('pay_amount_1') + vals.get('pay_amount_2') \
                + third_check_amount + issued_check_amount \
                + third_pay_check_amount
        return res

    def on_change_issued_check(self, vals):
        res = {}
        third_pay_check_amount = self.check_amount(
                vals.get('third_pay_checks'))
        third_check_amount = self.check_amount(vals.get('third_check'))
        issued_check_amount = self.check_amount(vals.get('issued_check'))
        res['total_checks'] = third_check_amount + issued_check_amount \
                + third_pay_check_amount
        res['amount'] = vals.get('pay_amount_1') + vals.get('pay_amount_2') \
                + third_check_amount + issued_check_amount \
                + third_pay_check_amount
        return res

    def on_change_third_pay_checks(self, vals):
        res = {}
        third_pay_check_amount = self.check_amount(
                vals.get('third_pay_checks'))
        third_check_amount = self.check_amount(vals.get('third_check'))
        issued_check_amount = self.check_amount(vals.get('issued_check'))
        res['total_checks'] = third_check_amount + issued_check_amount \
                + third_pay_check_amount
        res['amount'] = vals.get('pay_amount_1') + vals.get('pay_amount_2') \
                + third_check_amount + issued_check_amount \
                + third_pay_check_amount
        return res

    def prepare_moves(self, voucher_id):
        pre_move = super(VoucherCheck, self).prepare_moves(voucher_id)
        voucher = self.browse(voucher_id.id)
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
                    'account': voucher.journal_id.third_check_account.id,
                    'move': pre_move.get('move_id'),
                    'journal': voucher.journal_id.id,
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
                    'account': voucher.journal_id.issued_check_account.id,
                    'move': pre_move.get('move_id'),
                    'journal': voucher.journal_id.id,
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
                    'account': voucher.journal_id.third_check_account.id,
                    'move': pre_move.get('move_id'),
                    'journal': voucher.journal_id.id,
                    'period': period_obj.find(1, date=voucher.date),
                    'party': voucher.party.id,
                })

        return pre_move

    def action_paid(self, voucher_id):
        super(VoucherCheck, self).action_paid(voucher_id)
        voucher = self.browse(voucher_id.id)
        if voucher.third_check:
            third_check_obj = Pool().get('account.third.check')
            for check in voucher.third_check:
                check.write(check.id, {'source_party_id': voucher.party.id})
                third_check_obj.workflow_trigger_validate(check.id,
                        'draft_cartera')
        if voucher.third_pay_checks:
            third_check_obj = Pool().get('account.third.check')
            for check in voucher.third_pay_checks:
                check.write(check.id, {
                    'destiny_party_id': voucher.party.id,
                    'issued': True,
                })
                third_check_obj.workflow_trigger_validate(check.id,
                        'cartera_delivered')
        return True

    def __init__(self):
        super(VoucherCheck, self).__init__()
        self.pay_amount_1.on_change.extend(['issued_check',
            'third_check', 'third_pay_checks'])
        self.pay_amount_2.on_change.extend(['issued_check',
            'third_check', 'third_pay_checks'])

    issued_check = fields.One2Many('account.issued.check', 'voucher_id',
        'Issued Checks',
        on_change=['pay_amount_1', 'pay_amount_2',
            'issued_check', 'third_check', 'third_pay_checks'],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
        })

    third_pay_checks = fields.Many2Many('account.voucher-account.third.check',
        'voucher', 'third_check', 'Third Checks',
        on_change=['pay_amount_1', 'pay_amount_2', 'issued_check',
            'third_check', 'third_pay_checks'],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
        })

    third_check = fields.One2Many('account.third.check', 'voucher_id',
        'Third Checks',
        on_change=['pay_amount_1', 'pay_amount_2',
            'third_check', 'issued_check', 'third_pay_checks'],
        states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
        })

    total_checks = fields.Function(fields.Float('Checks'), 'amount_checks')

VoucherCheck()


class JournalCheck(ModelSQL, ModelView):
    'Account Check Voucher'
    _name = 'account.journal'
    _description = __doc__

    third_check_account = fields.Many2One('account.account',
        'Third Check Account')
    issued_check_account = fields.Many2One('account.account',
        'Issued Check Account')

JournalCheck()
