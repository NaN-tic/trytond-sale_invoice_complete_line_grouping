#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.pool import Pool
from .configuration import *
from .sale import *


def register():
    Pool.register(
        Configuration,
        ConfigurationCompany,
        SaleInvoiceGroup,
        Sale,
        SaleLine,
        module='sale_invoice_complete_line_grouping', type_='model')
