import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate sale_invoice_complete_line_grouping
        config = activate_modules('sale_invoice_complete_line_grouping')

        # Create company
        _ = create_company()
        company = get_company()

        # Create sale user
        User = Model.get('res.user')
        Group = Model.get('res.group')
        sale_user = User()
        sale_user.name = 'Sale'
        sale_user.login = 'sale'
        sale_group, = Group.find([('name', '=', 'Sales')])
        sale_user.groups.append(sale_group)
        sale_user.save()

        # Create stock user
        stock_user = User()
        stock_user.name = 'Stock'
        stock_user.login = 'stock'
        stock_group, = Group.find([('name', '=', 'Stock')])
        stock_user.groups.append(stock_group)
        stock_user.save()

        # Create account user
        account_user = User()
        account_user.name = 'Account'
        account_user.login = 'account'
        account_group, = Group.find([('name', '=', 'Account')])
        account_user.groups.append(account_group)
        account_user.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Configure sale
        SaleConfig = Model.get('sale.configuration')
        sale_config = SaleConfig(1)
        sale_config.sale_shipment_method = 'order'
        sale_config.sale_invoice_method = 'shipment'
        sale_config.save()

        # Create parties
        Party = Model.get('party.party')
        PartyAddress = Model.get('party.address')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.save()
        address1 = PartyAddress(name='a1', party=customer, delivery=True)
        address1.save()
        address2 = PartyAddress(name='a2', party=customer, delivery=True)
        address2.save()
        self.assertEqual(len(customer.addresses), 3)

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.list_price = Decimal('10')
        template.cost_price_method = 'fixed'
        template.account_category = account_category
        template.save()
        product, = template.products
        template2 = ProductTemplate()
        template2.name = 'product2'
        template2.default_uom = unit
        template2.type = 'goods'
        template2.salable = True
        template2.list_price = Decimal('10')
        template2.cost_price_method = 'fixed'
        template2.account_category = account_category
        template2.save()
        product2, = template2.products
        template3 = ProductTemplate()
        template3.name = 'product3'
        template3.default_uom = unit
        template3.type = 'goods'
        template3.salable = True
        template3.list_price = Decimal('10')
        template3.cost_price_method = 'fixed'
        template3.account_category = account_category
        template3.save()
        product3, = template3.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create an Inventory
        config.user = stock_user.id
        Inventory = Model.get('stock.inventory')
        InventoryLine = Model.get('stock.inventory.line')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line = InventoryLine()
        inventory.lines.append(inventory_line)
        inventory_line.product = product
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory_line = InventoryLine()
        inventory.lines.append(inventory_line)
        inventory_line.product = product2
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory_line = InventoryLine()
        inventory.lines.append(inventory_line)
        inventory_line.product = product3
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory.save()
        Inventory.confirm([inventory.id], config.context)
        self.assertEqual(inventory.state, 'done')

        # Sale products without groups
        config.user = sale_user.id
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.invoice_complete = True
        sale.payment_term = payment_term
        sale.invoice_method = 'shipment'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 2.0
        sale.save()
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')

        sale.reload()
        self.assertEqual(len(sale.shipments), 1)
        self.assertEqual(len(sale.shipment_returns), 0)
        self.assertEqual(len(sale.invoices), 0)

        # Validate Shipments
        shipment, = sale.shipments
        config.user = stock_user.id
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(len(sale.shipments), 1)
        self.assertEqual(len(sale.shipment_returns), 0)
        self.assertEqual(len(sale.invoices), 1)

        # Sale 3 lines with an invoice method 'on shipment'
        config.user = sale_user.id
        SaleInvoiceGroup = Model.get('sale.invoice.group')
        group1 = SaleInvoiceGroup(name='G1')
        group1.save()
        group2 = SaleInvoiceGroup(name='G2')
        group2.save()
        sale = Sale()
        sale.party = customer
        sale.invoice_complete = True
        sale.payment_term = payment_term
        sale.invoice_method = 'shipment'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 2.0
        sale_line.invoice_group = group1
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product2
        sale_line.quantity = 3.0
        sale_line.invoice_group = group1
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product3
        sale_line.quantity = 5.0
        sale_line.invoice_group = group2
        sale.save()
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')
        sale.reload()
        self.assertEqual(len(sale.shipments), 1)
        self.assertEqual(len(sale.shipment_returns), 0)
        self.assertEqual(len(sale.invoices), 0)

        # Validate Shipments
        shipment, = sale.shipments
        config.user = stock_user.id

        for move in shipment.inventory_moves:
            move.quantity = 2.0
            move.save()

        shipment.save()
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(len(sale.shipments), 2)
        self.assertEqual(len(sale.shipment_returns), 0)
        self.assertEqual(len(sale.invoices), 0)

        shipment2, = sale.shipments.find([('state', '=', 'waiting')])
        moves_to_remove = sale.moves.find([('state', '=', 'draft'),
                                           ('product', '=', product2.id)])
        config.user = stock_user.id
        self.assertNotEqual(moves_to_remove, [])

        for move in moves_to_remove:
            shipment2.moves.remove(move)

        shipment2.save()
        shipment2.click('assign_try')
        shipment2.click('pick')
        shipment2.click('pack')
        shipment2.click('done')
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(len(sale.shipments), 3)
        self.assertEqual(len(sale.shipment_returns), 0)
        self.assertEqual(len(sale.invoices), 1)

        invoice, = sale.invoices
        self.assertEqual(len(invoice.lines), 1)

        shipment3, = sale.shipments.find([('state', '=', 'waiting')])
        config.user = stock_user.id
        shipment3.click('assign_try')
        shipment3.click('pick')
        shipment3.click('pack')
        shipment3.click('done')
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(len(sale.shipments), 3)
        self.assertEqual(len(sale.shipment_returns), 0)
        self.assertEqual(len(sale.invoices), 2)
