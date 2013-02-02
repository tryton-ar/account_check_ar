#This file is part of the account_check_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.


from trytond.pool import Pool
from .account_check_ar import *


def register():
    Pool.register(
        AccountIssuedCheck,
        AccountThirdCheck,
        AccountVoucherThirdCheck,
        AccountVoucher,
        Journal,
        ThirdCheckHeldStart,
        ThirdCheckDepositStart,
        module='account_check_ar', type_='model')
    Pool.register(
        ThirdCheckHeld,
        ThirdCheckDeposit,
        module='account_check_ar', type_='wizard')


