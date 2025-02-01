# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare

class Repair(models.Model):
    _inherit = 'repair.order'

    serial_number_id = fields.Many2one(required=True)

    def action_view_po(self):
        action = self.env.ref('purchase.purchase_rfq')
        result = action.read()[0]

        rma_names = ['%%{0}%%'.format(rma.name) for rma in self if rma.name]
        self.env.cr.execute(""" SELECT array_agg(DISTINCT id) as po_ids 
                                FROM purchase_order 
                                WHERE origin like any (array[%s]);
                                """, (tuple(rma_names), ))
        op_res = self.env.cr.fetchone()
        po_ids = op_res and op_res[0] or []

        po_count = len(po_ids)

        if po_count > 1:
            result['domain'] = [('id', 'in', po_ids)]
        elif po_count == 1:
            res = self.env.ref('purchase.purchase_order_form')
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = po_ids[0]
        else:
            result['domain'] = [('id', '=', 0)]

        return result

class RepairLine(models.Model):
    _inherit = 'repair.line'

    product_qty_onhand = fields.Float('On Hand', digits='Product Unit of Measure',
                                    compute="_compute_quantity_onhand")

    def _compute_quantity_onhand(self):
        for line in self:
            if line.product_id and line.location_id:
                line.product_qty_onhand = line.product_id.with_context(location=line.location_id.id).qty_available
            else:
                line.product_qty_onhand = 0