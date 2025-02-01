# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import format_date


class Picking(models.Model):
    _inherit = "stock.picking"

    vendorbill_id = fields.Many2one('account.move', string="Vendor Bill", copy=False)

    def _action_done(self):
        """
        we choose to set the price on stock move instead of stock_move._get_price_unit()
        """
        self.check_procurement_workflow()
        self.set_stock_move_workflow_price_unit()
        self.set_notice_state()
        return super(Picking, self)._action_done()

    def check_procurement_workflow(self):
        pickings = self.filtered(lambda x: x.purchase_id)
        if not pickings:
            return True

        reception_modes = list(set(pickings.mapped('purchase_id.reception_mode')))

        for reception_mode in reception_modes:
            sliced_pickings = pickings.filtered(lambda x: x.purchase_id.reception_mode == reception_mode)
            method = 'check_procurement_workflow_{0}'.format(reception_mode or '')
            if hasattr(self, method):
                getattr(sliced_pickings, method)()

        return True

    def check_procurement_workflow_notice_reception(self):
        if not self:
            return True

        if any([not pick.notice_id or pick.notice_id.state != 'confirm' for pick in self]):
            raise UserError(_('Please first register the Notice from the supplier'))

        for picking in self:
            move_line_ids = picking.move_line_ids.filtered(lambda x: x.product_id)
            field = 'qty_done' if any([ml.qty_done > 0 for ml in move_line_ids]) else 'product_qty'
            picking_qtys = {}
            for move_line in move_line_ids:
                product_id = move_line.product_id.id
                picking_qtys.setdefault(product_id, {'product': move_line.product_id, 'qty': 0})
                picking_qtys[product_id]['qty'] += getattr(move_line, field) or 0

            notice_line_ids = picking.notice_id.notice_line_ids.filtered(lambda x: x.product_id)
            notice_qtys = {}
            for notice_line in notice_line_ids:
                product_id = notice_line.product_id.id
                notice_qtys.setdefault(product_id, 0)
                notice_qtys[product_id] += notice_line.product_qty or 0

            errors = []
            for product_id, item in picking_qtys.items():
                item_product = item.get('product')
                item_uom = item_product.uom_id
                item_qty = item.get('qty')
                if product_id not in notice_qtys:
                    errors.append(_('Product {0}, quantity {1}, not noticed').format(item_product.name_get()[0][1], item_qty))
                    continue

                if float_compare(item_qty, notice_qtys[product_id], precision_rounding=item_uom.rounding) > 0:
                    errors.append(_('Product {0}, quantity {1}, not noticed').format(item_product.name_get()[0][1], float_round(item_qty - notice_qtys[product_id], precision_rounding=item_uom.rounding)))
                    continue

            if errors:
                raise UserError("\n".join(errors))
        return True

    def check_procurement_workflow_bill_reception(self):
        if not self:
            return True

        if any([not pick.vendorbill_id or pick.vendorbill_id.state != 'posted' for pick in self]):
            raise UserError(_('Please first register the Invoice from the supplier'))

        for picking in self:
            move_line_ids = picking.move_line_ids.filtered(lambda x: x.product_id)
            field = 'qty_done' if any([ml.qty_done > 0 for ml in move_line_ids]) else 'product_qty'
            picking_qtys = {}
            for move_line in move_line_ids:
                product_id = move_line.product_id.id
                picking_qtys.setdefault(product_id, {'product': move_line.product_id, 'qty': 0})
                picking_qtys[product_id]['qty'] += getattr(move_line, field) or 0

            invoice_line_ids = picking.vendorbill_id.invoice_line_ids.filtered(lambda x: x.product_id)
            invoice_qtys = {}
            for invoice_line in invoice_line_ids:
                product_id = invoice_line.product_id.id
                invoice_qtys.setdefault(product_id, 0)
                invoice_qtys[product_id] += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity or 0, invoice_line.product_id.uom_id)

            errors = []
            for product_id, item in picking_qtys.items():
                item_product = item.get('product')
                item_uom = item_product.uom_id
                item_qty = item.get('qty')
                if product_id not in invoice_qtys and item_qty > 0:
                    errors.append(_('Product {0}, quantity {1}, not invoiced').format(item_product.name_get()[0][1], item_qty))
                    continue

                if product_id in invoice_qtys and float_compare(item_qty, invoice_qtys[product_id], precision_rounding=item_uom.rounding) > 0:
                    errors.append(_('Product {0}, quantity {1}, not invoiced').format(item_product.name_get()[0][1], float_round(item_qty - invoice_qtys[product_id], precision_rounding=item_uom.rounding)))
                    continue

            if errors:
                raise UserError("\n".join(errors))
        return True

    def check_procurement_workflow_bill_notice_reception(self):
        if not self:
            return True

        if any([not pick.notice_id or pick.notice_id.state != 'confirm' for pick in self]):
            raise UserError(_('Please first register the Invoice then the Notice from the supplier'))

        if any([not pick.vendorbill_id or pick.vendorbill_id.state != 'posted' for pick in self]):
            raise UserError(_('Please first register the Invoice then the Notice from the supplier'))

        for picking in self:
            move_line_ids = picking.move_line_ids.filtered(lambda x: x.product_id)
            field = 'qty_done' if any([ml.qty_done > 0 for ml in move_line_ids]) else 'product_qty'
            picking_qtys = {}
            for move_line in move_line_ids:
                product_id = move_line.product_id.id
                picking_qtys.setdefault(product_id, {'product': move_line.product_id, 'qty': 0})
                picking_qtys[product_id]['qty'] += getattr(move_line, field) or 0

            notice_line_ids = picking.notice_id.notice_line_ids.filtered(lambda x: x.product_id)
            notice_qtys = {}
            for notice_line in notice_line_ids:
                product_id = notice_line.product_id.id
                notice_qtys.setdefault(product_id, 0)
                notice_qtys[product_id] += notice_line.product_qty or 0

            errors = []
            for product_id, item in picking_qtys.items():
                item_product = item.get('product')
                item_uom = item_product.uom_id
                item_qty = item.get('qty')
                if product_id not in notice_qtys:
                    errors.append(_('Product {0}, quantity {1}, not noticed').format(item_product.name_get()[0][1], item_qty))
                    continue

                if float_compare(item_qty, notice_qtys[product_id], precision_rounding=item_uom.rounding) > 0:
                    errors.append(_('Product {0}, quantity {1}, not noticed').format(item_product.name_get()[0][1], float_round(item_qty - notice_qtys[product_id], precision_rounding=item_uom.rounding)))
                    continue

            if errors:
                raise UserError("\n".join(errors))

        return True

    def set_stock_move_workflow_price_unit(self):
        pickings = self.filtered(lambda x: x.purchase_id)
        if not pickings:
            return True

        reception_modes = list(set(pickings.mapped('purchase_id.reception_mode')))

        for reception_mode in reception_modes:
            sliced_pickings = pickings.filtered(lambda x: x.purchase_id.reception_mode == reception_mode)
            method = 'set_stock_move_workflow_price_unit_{0}'.format(reception_mode or '')
            if hasattr(self, method):
                getattr(sliced_pickings, method)()

        return True

    def set_stock_move_workflow_price_unit_notice_reception(self):
        if not self:
            return True

        for picking in self.filtered(lambda x: x.notice_id):
            notice_rate = picking.notice_id.rate
            notice_unit_prices = dict((l.product_id.id, (l.price_unit or 0) * (notice_rate or 1)) for l in picking.mapped('notice_id.notice_line_ids').filtered(lambda x: x.product_id))
            for move in picking.move_lines.filtered(lambda x: x.product_id):
                price_unit = False
                notice_line_prices = dict((l.id,  (l.price_unit or 0) * (notice_rate or 1)) for l in move.mapped('purchase_line_id.notice_line_ids'))
                if notice_line_prices:
                    price_unit = list(notice_line_prices.values())[0]

                if price_unit is False:
                    product_id = move.product_id.id
                    if product_id in notice_unit_prices:
                        price_unit = notice_unit_prices.get(product_id)

                if price_unit is not False:
                    move.write({'price_unit': price_unit})
        return True

    def set_stock_move_workflow_price_unit_bill_reception(self):
        if not self:
            return True

        for picking in self.filtered(lambda x: x.vendorbill_id):
            bill_rate = picking.vendorbill_id.rate
            bill_unit_prices = dict((l.product_id.id, ((l.price_unit or 0) * (1 - (l.discount / 100.0)) if l.discount else (l.price_unit or 0)) * (bill_rate or 1))
                                    for l in picking.mapped('vendorbill_id.invoice_line_ids').filtered(lambda x: x.product_id))
            for move in picking.move_lines.filtered(lambda x: x.product_id):
                price_unit = False
                invoice_line_prices = dict((l.id, ((l.price_unit or 0) * (1 - (l.discount / 100.0)) if l.discount else (l.price_unit or 0)) * (bill_rate or 1))
                                    for l in move.mapped('purchase_line_id.invoice_lines'))
                if invoice_line_prices:
                    price_unit = list(invoice_line_prices.values())[0]
                if price_unit is False:
                    product_id = move.product_id.id
                    if product_id in bill_unit_prices:
                        price_unit = bill_unit_prices.get(product_id)

                if price_unit is not False:
                    move.write({'price_unit': price_unit})
        return True

    def set_stock_move_workflow_price_unit_bill_notice_reception(self):
        if not self:
            return True

        for picking in self.filtered(lambda x: x.notice_id):
            notice_rate = picking.notice_id.rate
            notice_unit_prices = dict((l.product_id.id, (l.price_unit or 0) * (notice_rate or 1)) for l in picking.mapped('notice_id.notice_line_ids').filtered(lambda x: x.product_id))
            for move in picking.move_lines.filtered(lambda x: x.product_id):
                price_unit = False
                notice_line_prices = dict((l.id,  (l.price_unit or 0) * (notice_rate or 1)) for l in move.mapped('purchase_line_id.notice_line_ids'))
                if notice_line_prices:
                    price_unit = list(notice_line_prices.values())[0]

                if price_unit is False:
                    product_id = move.product_id.id
                    if product_id in notice_unit_prices:
                        price_unit = notice_unit_prices.get(product_id)

                if price_unit is not False:
                    move.write({'price_unit': price_unit})
        return True

    def set_notice_state(self):
        pickings = self.filtered(lambda x: x.purchase_id)
        if not pickings:
            return True

        reception_modes = list(set(pickings.mapped('purchase_id.reception_mode')))

        for reception_mode in reception_modes:
            sliced_pickings = pickings.filtered(lambda x: x.purchase_id.reception_mode == reception_mode)
            method = 'set_notice_state_{0}'.format(reception_mode or '')
            if hasattr(self, method):
                getattr(sliced_pickings, method)()

        return True

    def set_notice_state_notice_reception(self):
        self.mapped('notice_id').action_receive()
        return True

    def set_notice_state_bill_notice_receptionn(self):
        self.mapped('notice_id').action_invoice()
        return True

    def action_merge_by_invoice(self, vendorbill_id=None):
        if not vendorbill_id:
            return self.env['stock.picking']
        if not self or len(self) <= 1:
            return self

        first_picking = self[0]

        new_picking = first_picking.copy(default={"scheduled_date": fields.Datetime.now(), "vendorbill_id": vendorbill_id.id, 'move_lines': False})

        move_line_vals = {'picking_id': new_picking.id, 'location_id': new_picking.location_id.id, 'location_dest_id': new_picking.location_dest_id.id, 'date': new_picking.scheduled_date}
        for move in self.mapped('move_lines'):
            new_move = move.copy(default=move_line_vals)
            new_move.write({'price_unit': move.price_unit})

        self.write({'vendorbill_id': False})
        self.sudo().action_cancel()
        new_picking.sudo().action_assign()

        return new_picking




