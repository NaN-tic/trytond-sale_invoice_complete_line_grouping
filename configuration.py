#The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Id

__all__ = ['Configuration', 'ConfigurationSequence']


def default_func(field_name):
    @classmethod
    def default(cls, **pattern):
        return getattr(
            cls.multivalue_model(field_name),
            'default_%s' % field_name, lambda: None)()
    return default


class Configuration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'
    invoice_group_sequence = fields.MultiValue(fields.Many2One(
            'ir.sequence', "Invoice Group Sequence", required=True,
            domain=[
                ('company', 'in',
                    [Eval('context', {}).get('company', -1), None]),
                ('sequence_type', '=', Id('sale_invoice_complete_line_grouping',
                    'sequence_type_invoice_group')),
                ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'invoice_group_sequence':
            return pool.get('sale.configuration.sequence')
        return super(Configuration, cls).multivalue_model(field)

    default_invoice_group_sequence = default_func('invoice_group_sequence')


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'sale.configuration.sequence'
    invoice_group_sequence = fields.Many2One(
        'ir.sequence', "Invoice Group Sequence", required=True,
        domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('sequence_type', '=', Id('sale_invoice_complete_line_grouping',
                'sequence_type_invoice_group')),
            ],
        depends=['company'])

    @classmethod
    def default_invoice_group_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('sale_invoice_complete_line_grouping',
                'sequence_invoice_group')
        except KeyError:
            return None
