# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, Workflow
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Bool


class AccountIssuedCheck(metaclass=PoolMeta):
    __name__ = 'account.issued.check'

    related_statement_line = fields.Many2One('account.statement.line',
        'Statement Line', readonly=True)


class AccountThirdCheck(metaclass=PoolMeta):
    __name__ = 'account.third.check'

    related_statement_line = fields.Many2One('account.statement.line',
        'Statement Line', readonly=True)


class Statement(metaclass=PoolMeta):
    __name__ = 'account.statement'

    @classmethod
    @Workflow.transition('validated')
    def validate_statement(cls, statements):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        StatementLine = Pool().get('account.statement.line')

        super(Statement, cls).validate_statement(statements)
        # Remove created draft moves when line is related to third checks
        lines = [l for s in statements for l in s.lines
            if isinstance(l.related_to, ThirdCheck)]
        StatementLine.delete_move(lines)

    @classmethod
    @Workflow.transition('posted')
    def post(cls, statements):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')

        super(Statement, cls).post(statements)
        # Change issued checks state
        lines = [l for s in statements for l in s.lines
            if isinstance(l.related_to, IssuedCheck)]
        checks = []
        for l in lines:
            check = IssuedCheck(l.related_to.id)
            check.state = 'debited'
            check.debit_date = l.date
            checks.append(check)
        IssuedCheck.save(checks)


class StatementLine(metaclass=PoolMeta):
    __name__ = 'account.statement.line'

    statement_journal_bank_account = fields.Function(
        fields.Many2One('bank.account', 'Bank Account',),
        'on_change_with_statement_journal_bank_account')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.related_to.domain['account.issued.check'] = ['OR',
            [('related_statement_line', '=', Eval('id', -1))],
            [('related_statement_line', '=', None),
                ('voucher', '!=', None),
                ('voucher.company', '=', Eval('company', -1)),
                If(Bool(Eval('voucher.party')),
                    ('voucher.party', '=', Eval('party')),
                    ()),
                ('checkbook.bank_account', '=',
                    Eval('statement_journal_bank_account', -1)),
                ('voucher.state', 'in', ['posted']),
                ('state', 'in', ['issued']),
                ('voucher.currency', '=', Eval('currency', -1)),
                ('voucher.voucher_type', '=',
                    If(Eval('amount', 0) > 0, 'receipt',
                        If(Eval('amount', 0) < 0, 'payment', ''))),
                ('amount', '=', Eval('abs_amount', 0)),
            ]]
        cls.related_to.domain['account.third.check'] = ['OR',
            [('related_statement_line', '=', Eval('id', -1))],
            [('related_statement_line', '=', None),
                ('state', 'in', ['deposited']),
                ('amount', '=', Eval('abs_amount', 0)),
            ]]
        cls.related_to.search_order['account.issued.check'] = [
            ('amount', 'ASC'),
            ]
        cls.related_to.search_order['account.third.check'] = [
            ('amount', 'ASC'),
            ]

    @fields.depends('statement')
    def on_change_with_statement_journal_bank_account(self, name=None):
        if self.statement and self.statement.journal \
                and self.statement.journal.bank_account:
            return self.statement.journal.bank_account.id
        return None

    @classmethod
    def _get_relations(cls):
        return super()._get_relations() + [
            'account.issued.check', 'account.third.check']

    @property
    @fields.depends('related_to')
    def issued_check(self):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')
        related_to = getattr(self, 'related_to', None)
        if isinstance(related_to, IssuedCheck) and related_to.id >= 0:
            return related_to

    @issued_check.setter
    def issued_check(self, value):
        self.related_to = value

    @property
    @fields.depends('related_to')
    def third_check(self):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')
        related_to = getattr(self, 'related_to', None)
        if isinstance(related_to, ThirdCheck) and related_to.id >= 0:
            return related_to

    @third_check.setter
    def third_check(self, value):
        self.related_to = value

    @fields.depends('party', 'statement',
            methods=['issued_check', 'third_check'])
    def on_change_related_to(self):
        super().on_change_related_to()
        if self.issued_check:
            if not self.party:
                self.party = self.issued_check.voucher.party
            if self.issued_check.voucher.journal.issued_check_account:
                self.account = \
                    self.issued_check.voucher.journal.issued_check_account
        if self.third_check:
            if not self.party and self.third_check.source_party:
                self.party = self.third_check.source_party
            if self.third_check.account_bank_out:
                self.account = self.third_check.account_bank_out.credit_account

    @classmethod
    def write(cls, *args):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')
        ThirdCheck = pool.get('account.third.check')

        actions = iter(args)
        update_issued = {}
        update_third = {}
        for lines, values in zip(actions, actions):
            if 'related_to' in values:
                if values['related_to'] is None:
                    if isinstance(lines[0].related_to, IssuedCheck):
                        update_issued[lines[0].related_to.id] = None
                    elif isinstance(lines[0].related_to, ThirdCheck):
                        update_third[lines[0].related_to.id] = None
                elif values['related_to'].split(',')[0] \
                        == IssuedCheck.__name__:
                    check_id = int(values['related_to'].split(',')[1])
                    update_issued[check_id] = lines[0].id
                elif values['related_to'].split(',')[0] \
                        == ThirdCheck.__name__:
                    check_id = int(values['related_to'].split(',')[1])
                    update_third[check_id] = lines[0].id
        super(StatementLine, cls).write(*args)
        cls.update_issued_checks(update_issued)
        cls.update_third_checks(update_third)

    def update_issued_checks(update_issued):
        pool = Pool()
        IssuedCheck = pool.get('account.issued.check')

        issued_checks = []
        for key in update_issued:
            check = IssuedCheck(key)
            check.related_statement_line = update_issued[key]
            issued_checks.append(check)
        IssuedCheck.save(issued_checks)

    def update_third_checks(update_third):
        pool = Pool()
        ThirdCheck = pool.get('account.third.check')

        third_checks = []
        for key in update_third:
            check = ThirdCheck(key)
            check.related_statement_line = update_third[key]
            third_checks.append(check)
        ThirdCheck.save(third_checks)
