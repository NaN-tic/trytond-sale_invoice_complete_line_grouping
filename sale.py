# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['SaleInvoiceGroup', 'Sale', 'SaleLine']


class SaleInvoiceGroup(ModelSQL, ModelView):
    'Sale Invoice Group'
    __name__ = 'sale.invoice.group'
    code = fields.Char('Code', required=True, readonly=True)
    name = fields.Char('Name')

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('sale.configuration')

        company_id = Transaction().context.get('company')

        config = Config(1)
        vlist = [x.copy() for x in vlist]
        for value in vlist:
            if not 'code' in value:
                value['code'] = config.get_multivalue(
                    'invoice_group_sequence', company=company_id).get()
        return super(SaleInvoiceGroup, cls).create(vlist)

    def get_rec_name(self, name):
        name = self.code
        if self.name:
            name += '- %s' % self.name
        return name

    @classmethod
    def search_rec_name(cls, name, clause):
        ids = [x.id for x in cls.search([('code',) + tuple(clause[1:])],
                order=[])]
        if ids:
            ids += [x.id for x in cls.search([('name',) + tuple(clause[1:])],
                    order=[])]
            return [('id', 'in', ids)]
        return [('name',) + tuple(clause[1:])]


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    def get_completed_groups(self):
        'Returns a list of completed groups'
        groups = {}
        completed_groups = []
        for line in self.lines:
            group = line.invoice_group
            value = groups[group] if group in groups else []
            value.append(line.moves_progress or 0)
            groups[group] = value

        for group, lines_completed in groups.items():
            if all(x >= 1.0 for x in lines_completed):
                completed_groups.append(group)

        return completed_groups

    def is_sale_complete(self):
        ' Returns true if the sale is considered complete, false otherwise '
        if self.invoice_method == 'shipment':
            return len(self.get_completed_groups()) > 0
        return True


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'
    invoice_group = fields.Many2One('sale.invoice.group', 'Invoice Grouping',
        ondelete='RESTRICT', states={
            'invisible': Eval('type') != 'line',
            })

    def get_invoice_line(self):
        sale = self.sale
        completed_groups = sale.get_completed_groups()
        invoice_lines = []
        if not sale.invoice_complete or self.invoice_group in completed_groups:
            invoice_lines.extend(super(SaleLine, self).get_invoice_line())
        return invoice_lines
