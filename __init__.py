# This file is part of the account_check_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .account_check_ar import *
from .account_voucher_ar import *


def register():
    Pool.register(
        AccountIssuedCheck,
        AccountThirdCheck,
        AccountVoucherThirdCheck,
        Journal,
        ThirdCheckHeldStart,
        ThirdCheckDepositStart,
        ThirdCheckRevertDepositStart,
        IssuedCheckDebitStart,
        IssuedCheckRevertDebitStart,
        AccountVoucher,
        module='account_check_ar', type_='model')
    Pool.register(
        ThirdCheckHeld,
        ThirdCheckDeposit,
        ThirdCheckRevertDeposit,
        IssuedCheckDebit,
        IssuedCheckRevertDebit,
        module='account_check_ar', type_='wizard')
