# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['SaleInvoiceGroup', 'Sale', 'SaleLine']
__metaclass__ = PoolMeta


class SaleInvoiceGroup(ModelSQL, ModelView):
    'Sale Invoice Group'
    __name__ = 'sale.invoice.group'

    code = fields.Char('Code', required=True, readonly=True)
    name = fields.Char('Name')

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Sequence = pool.get('ir.sequence')
        Config = pool.get('sale.configuration')

        config = Config(1)
        for value in vlist:
            if not 'code' in value:
                value['code'] = Sequence.get_id(
                    config.invoice_group_sequence.id)
        return super(SaleInvoiceGroup, cls).create(vlist)

    def get_rec_name(self, name):
        name = self.code
        if self.name:
            name += '- %s' % self.name
        return name

    @classmethod
    def search_rec_name(cls, name, clause):
        ids = map(int, cls.search([('code',) + tuple(clause[1:])], order=[]))
        if ids:
            ids += map(int,
                cls.search([('name',) + tuple(clause[1:])], order=[]))
            return [('id', 'in', ids)]
        return [('name',) + tuple(clause[1:])]


class Sale:
    __name__ = 'sale.sale'

    def get_completed_groups(self):
        'Returns a list of completed groups'
        groups = {}
        completed_groups = []
        for line in self.lines:
            group = line.invoice_group
            value = groups[group] if group in groups else []
            value.append(line.move_done)
            groups[group] = value

        for group, lines_completed in groups.iteritems():
            if all(x for x in lines_completed):
                completed_groups.append(group)

        return completed_groups

    def is_sale_complete(self):
        ' Returns true if the sale is considered complete, false otherwise '
        if self.invoice_method == 'shipment':
            return len(self.get_completed_groups()) > 0
        return True


class SaleLine:
    __name__ = 'sale.line'

    invoice_group = fields.Many2One('sale.invoice.group', 'Invoice Grouping',
        ondelete='RESTRICT', depends=['type'], states={
            'invisible': Eval('type') != 'line',
            })

    def get_invoice_line(self):
        sale = self.sale
        completed_groups = sale.get_completed_groups()
        invoice_lines = []
        if not sale.invoice_complete or self.invoice_group in completed_groups:
            invoice_lines.extend(super(SaleLine, self).get_invoice_line())
        return invoice_lines
