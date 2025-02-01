# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.tools import float_compare, float_round, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_picking_incoming(self):
        for invoice in self:
            if invoice.move_type in ['in_invoice', 'in_refund']:
                pickings = self.env['stock.picking'].search([('vendorbill_id', '=', invoice.id)])
                invoice.picking_incoming_ids = pickings
                invoice.picking_incoming_count = len(set(pickings and pickings.ids or []))
            else:
                invoice.picking_incoming_ids = False
                invoice.picking_incoming_count = 0

    picking_incoming_count = fields.Integer(compute='_compute_picking_incoming', string='Reception Count', default=0)
    picking_incoming_ids = fields.Many2many('stock.picking', compute='_compute_picking_incoming', string='Receptions', copy=False)

    def action_view_picking_incoming(self):
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        action['context'] = {}

        pick_ids = self.mapped('picking_incoming_ids').ids

        if len(pick_ids) > 1:
            action['domain'] = [('id', 'in', pick_ids)]
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            action['views'] = [(res and res.id or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False
        return action

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=True)
        self.mapped('invoice_line_ids.notice_line_id.notice_id').action_invoice()
        self.filtered(lambda x: x.move_type == 'in_invoice').merge_receptions()
        self.action_send_quantities_to_reception()
        return res

    def action_send_quantities_to_reception(self):
        invoice_lines_with_po_line = self.mapped('line_ids').filtered(lambda x: x.purchase_line_id)
        res = invoice_lines_with_po_line.send_quantities_to_reception()

        if res.get('sent'):
            moves = self.env['account.move']
            #ugly, but we need unique invoices (for 100 lines on a single invoice we want to send only one message)
            for move in res['sent'].mapped('move_id'):
                moves |= move
            moves.message_post(body=_("Quantities have been set on reception"))

        if res.get('not_sent'):
            moves = self.env['account.move']
            #ugly, but we need unique invoices (for 100 lines on a single invoice we want to send only one message)
            for move in res['not_sent'].mapped('move_id'):
                moves |= move
            moves.message_post(body=_("Quantities not updated, reception not found/not in the correct state"))

        return True

    def merge_receptions(self):
        for invoice in self:
            if not invoice._should_merge_receptions():
                continue

            receptions_to_merge = self._get_receptions_to_merge()
            if receptions_to_merge:
                receptions_to_merge.action_merge_by_invoice(vendorbill_id=invoice)

        return True

    def _should_merge_receptions(self):
        self.ensure_one()
        return self.move_type == 'in_invoice' and self.company_id.merge_receptions_by_invoice and True or False

    def _get_receptions_to_merge(self):
        self.ensure_one()

        purchases = self.mapped('line_ids.purchase_line_id.order_id').filtered(lambda x: x.reception_mode=='bill_reception')
        unique_purchases = self.env['purchase.order']
        for pur in purchases:
            unique_purchases |= pur

        if len(unique_purchases) <= 1:
            return self.env['stock.picking']

        all_receptions = unique_purchases.mapped('picking_ids').filtered(lambda x: x.state in ['assigned'])
        receptions = self.env['stock.picking']
        for pick in all_receptions:
            receptions |= pick

        return receptions if len(receptions) > 1 else self.env['stock.picking']

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        """ Load from either an old purchase order, either an old vendor bill.

        When setting a 'purchase.bill.union' in 'purchase_vendor_bill_id':
        * If it's a vendor bill, 'invoice_vendor_bill_id' is set and the loading is done by '_onchange_invoice_vendor_bill'.
        * If it's a purchase order, 'purchase_id' is set and this method will load lines.

        /!\ All this not-stored fields must be empty at the end of this function.

        TODO: maybe find a better way than to override the entire method
        """
        if self.purchase_vendor_bill_id.vendor_bill_id:
            self.invoice_vendor_bill_id = self.purchase_vendor_bill_id.vendor_bill_id
            self._onchange_invoice_vendor_bill()
        elif self.purchase_vendor_bill_id.purchase_order_id:
            self.purchase_id = self.purchase_vendor_bill_id.purchase_order_id
        self.purchase_vendor_bill_id = False

        if not self.purchase_id:
            return

        # Copy data from PO
        invoice_vals = self.purchase_id.with_company(self.purchase_id.company_id)._prepare_invoice()
        invoice_vals['currency_id'] = self.line_ids and self.currency_id or invoice_vals.get('currency_id')
        del invoice_vals['ref']
        self.update(invoice_vals)

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line - self.line_ids.mapped('purchase_line_id')
        new_lines = self.env['account.move.line']
        for line in po_lines.filtered(lambda l: not l.display_type and not float_is_zero(l.qty_to_invoice, precision_rounding=l.product_uom.rounding)):
            new_line = new_lines.new(line._prepare_account_move_line(self))
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()
            new_lines += new_line
        new_lines._onchange_mark_recompute_taxes()

        # Compute invoice_origin.
        origins = set(self.line_ids.mapped('purchase_line_id.order_id.name'))
        self.invoice_origin = ','.join(list(origins))

        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ', '.join(refs)

        # Compute payment_reference.
        if len(refs) == 1:
            self.payment_reference = refs[0]

        self.purchase_id = False
        self._onchange_currency()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(AccountMoveLine, self).create(vals_list)

        for line in lines.filtered(lambda x: x.notice_line_id and x.move_id):
            line.mapped('notice_line_id.notice_id.picking_ids').filtered(lambda x: not x.vendorbill_id).write({'vendorbill_id': line.move_id.id})

        for line in lines.filtered(lambda x: x.purchase_line_id and x.move_id and not x.notice_line_id):
            pickings = line.mapped('purchase_line_id.move_ids').filtered(lambda x: x.state == 'assigned').mapped(
                'picking_id').filtered(lambda x: not x.vendorbill_id)
            if pickings:
                pickings[0].write({'vendorbill_id': line.move_id.id})

        return lines

    def send_quantities_to_reception(self):
        res = {'sent': self.env['account.move.line'], 'not_sent': self.env['account.move.line']}
        for line in self:
            move = line._get_stock_move_for_send_quantities()
            if not move:
                res['not_sent'] |= line
                continue
            move.quantity_done = line.product_uom_id._compute_quantity(line.quantity, move.product_uom, round=False)
            res['sent'] |= line
        return res

    def _get_stock_move_for_send_quantities(self):
        self.ensure_one()
        move_id = self.mapped('purchase_line_id.move_ids').filtered(lambda x: x.state not in ['cancel', 'done'])
        return move_id if move_id and len(move_id.move_line_ids) == 1 else self.env['stock.move']

    def modify_stock_valuation(self, price_unit_val_dif):
        self.ensure_one()

        pickings = self.env['stock.picking'].search([('vendorbill_id', '=', self.move_id.id)])
        valuation_stock_moves = pickings.mapped('move_lines').filtered(lambda x: x.purchase_line_id and x.purchase_line_id.id == self.purchase_line_id.id and x.state=='done' and x.product_qty != 0.0)

        stock_receptions = self.env['stock.reception']
        #we need unique stock receptions
        for stock_recep in valuation_stock_moves.mapped('stock_valuation_layer_ids.stock_reception_id'):
            stock_receptions |= stock_recep

        pickings.set_stock_move_workflow_price_unit()
        stock_receptions.write({'to_update': True})
