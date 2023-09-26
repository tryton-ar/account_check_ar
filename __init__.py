# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import account_check_ar
from . import account_voucher_ar
from . import statement


def register():
    Pool.register(
        account_check_ar.AccountCheckbook,
        account_check_ar.AccountIssuedCheck,
        account_check_ar.AccountThirdCheck,
        account_check_ar.AccountVoucherThirdCheck,
        account_check_ar.Journal,
        account_check_ar.ThirdCheckHeldStart,
        account_check_ar.ThirdCheckDepositStart,
        account_check_ar.ThirdCheckRevertDepositStart,
        account_check_ar.IssuedCheckDebitStart,
        account_check_ar.IssuedCheckRevertDebitStart,
        account_check_ar.ThirdCheckRejectStart,
        account_check_ar.ThirdCheckRevertRejectStart,
        account_check_ar.IssuedCheckCancelStart,
        account_voucher_ar.AccountVoucher,
        module='account_check_ar', type_='model')
    Pool.register(
        statement.AccountIssuedCheck,
        statement.AccountThirdCheck,
        statement.Statement,
        statement.StatementLine,
        module='account_check_ar', type_='model',
        depends=['account_statement'])
    Pool.register(
        account_check_ar.ThirdCheckHeld,
        account_check_ar.ThirdCheckDeposit,
        account_check_ar.ThirdCheckRevertDeposit,
        account_check_ar.IssuedCheckDebit,
        account_check_ar.IssuedCheckRevertDebit,
        account_check_ar.ThirdCheckReject,
        account_check_ar.ThirdCheckRevertReject,
        account_check_ar.IssuedCheckCancel,
        module='account_check_ar', type_='wizard')
