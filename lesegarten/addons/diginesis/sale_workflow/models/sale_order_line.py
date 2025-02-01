# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, float_round


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'

    qty_noticed = fields.Float(compute='_compute_qty_noticed', string="Noticed", digits='Product Unit of Measure',
                               store=True, copy=False)
    noticed_to_invoice_qty = fields.Float(compute='_get_noticed_to_invoice_qty', string="Noticed to Invoice", digits='Product Unit of Measure',
                               store=True, copy=False)
    unnoticed_to_invoice_qty = fields.Float(compute='_get_unnoticed_to_invoice_qty', string="Not-Noticed to Invoice", digits='Product Unit of Measure',
                               store=True, copy=False)
    notice_line_ids = fields.Many2many('account.notice.line', 'sale_line_notice_line_rel', 'sale_line_id',
                                       'notice_line_id', string='Notice Lines', copy=False)
    original_downpayment_line_id = fields.Many2one('sale.order.line', string="Original Downpayment Line", copy=False)

    @api.depends('notice_line_ids.notice_id.state', 'notice_line_ids.quantity', 'product_uom_qty', 'order_id.state')
    def _compute_qty_noticed(self):
        for line in self:
            qty = 0.0
            notice_lines = line._get_notice_lines()
            notice_lines = notice_lines.filtered(lambda x: x.notice_id.state not in ['cancel'])
            for note_line in notice_lines:
                if note_line.notice_id.type == 'out_notice':
                    qty += note_line.uom_id._compute_quantity(note_line.quantity, line.product_uom)
                elif note_line.notice_id.type == 'out_refund':
                    qty -= note_line.uom_id._compute_quantity(note_line.quantity, line.product_uom)
            line.qty_noticed = qty

    def _get_notice_lines(self):
        self.ensure_one()
        return self.notice_line_ids

    @api.depends('qty_invoiced', 'qty_noticed', 'qty_to_invoice', 'order_id.state')
    def _get_noticed_to_invoice_qty(self):
        """
        Compute noticed quantity to invoice.
        """
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                line.noticed_to_invoice_qty = min(line.qty_noticed - line.qty_invoiced, line.qty_to_invoice)
            else:
                line.noticed_to_invoice_qty = 0

    @api.depends('qty_noticed', 'qty_delivered', 'qty_to_invoice', 'product_uom_qty', 'order_id.state')
    def _get_unnoticed_to_invoice_qty(self):
        """
        Compute the not-noticed quantity to invoice.
        """
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                if line.product_id.invoice_policy == 'order':
                    line.unnoticed_to_invoice_qty = min(line.product_uom_qty - line.qty_noticed, line.qty_to_invoice)
                else:
                    line.unnoticed_to_invoice_qty = min(line.qty_delivered - line.qty_noticed, line.qty_to_invoice)
            else:
                line.unnoticed_to_invoice_qty = 0

    def _post_prepare_invoice_line_name(self, prepared_invoice_line, name_parts):
        self.ensure_one()

        if not name_parts:
            return False

        template = self._get_invoice_line_name_template()
        new_name_parts = name_parts.copy()

        #we'll just hardcode conditions here; maybe improve
        if name_parts.get('picking_name') and not self.company_id.picking_in_invoice_line_description:
            new_name_parts['picking_name'] = ''

        res = []
        for key in sorted(template.keys()):
            if new_name_parts.get(template[key]):
                res.append(new_name_parts.get(template[key]))

        return " ".join(res)

    def _get_invoice_line_name_template(self):
        return {2: "invoice_line_name", 0: "notice_name", 1: "picking_name", }