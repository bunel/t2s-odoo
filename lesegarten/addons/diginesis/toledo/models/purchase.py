# -*- coding: utf-8 -*-

from datetime import datetime, time
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = "purchase.order"

    transported_purchases = fields.Many2many('purchase.order', 'purchase_order_transported_purchases_rel', 'order_id', 'transported_order_id',
                                             string="Transported Purchases")
    transport_order_count = fields.Integer(string="Transport Order Count", compute='_compute_transport_orders')

    def _compute_transport_orders(self):
        self.env.cr.execute(""" SELECT transported_order_id, count(order_id) 
                                    FROM purchase_order_transported_purchases_rel 
                                    WHERE transported_order_id IN %s
                                    GROUP BY transported_order_id""", (tuple(self.ids),))
        res_pur = self.env.cr.fetchall()
        res = res_pur and dict(res_pur) or {}

        for purchase in self:
            purchase.transport_order_count = res.get(purchase.id) or 0

    def action_view_transport_orders(self):
        self.env.cr.execute(""" SELECT array_agg(order_id) FROM purchase_order_transported_purchases_rel WHERE transported_order_id IN %s """, (tuple(self.ids), ))

        res_ord = self.env.cr.fetchone()
        res_ids = res_ord and res_ord[0] or []

        action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')
        action['context'] = {}
        if len(res_ids) <= 0:
            action['domain'] = [('id', '=', False)]
        elif len(res_ids) > 0:
            action['domain'] = [('id', 'in', res_ids)]

        if len(res_ids) == 1:
            action['res_id'] = res_ids[0]
            action['views'] = [[False, 'form']]

        return action

    def action_view_transported_purchases(self):
        self.env.cr.execute(""" SELECT array_agg(transported_order_id) FROM purchase_order_transported_purchases_rel WHERE order_id IN %s """, (tuple(self.ids), ))

        res_ord = self.env.cr.fetchone()
        res_ids = res_ord and res_ord[0] or []

        action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')
        action['context'] = {}
        action['name'] = _('Served Purchases')
        if len(res_ids) <= 0:
            action['domain'] = [('id', '=', False)]
        elif len(res_ids) > 0:
            action['domain'] = [('id', 'in', res_ids)]

        if len(res_ids) == 1:
            action['res_id'] = res_ids[0]
            action['views'] = [[False, 'form']]

        return action
