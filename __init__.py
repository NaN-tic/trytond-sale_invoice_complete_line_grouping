#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import sale


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        sale.SaleInvoiceGroup,
        sale.Sale,
        sale.SaleLine,
        module='sale_invoice_complete_line_grouping', type_='model')
