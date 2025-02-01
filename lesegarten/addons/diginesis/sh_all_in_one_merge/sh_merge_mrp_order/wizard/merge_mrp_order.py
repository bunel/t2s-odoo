# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShMergeMrpOrderWizard(models.TransientModel):
    _name = "sh.merge.mrp.order.wizard"
    _description = "Merge MRP Order Wizard"

    product_id = fields.Many2one('product.product', 'Product')
    mrp_order_id = fields.Many2one("mrp.production", string="Mrp Order")
    mrp_order_ids = fields.Many2many(
        "mrp.production", string="Mrp Orders")
    location_src_id = fields.Many2one('stock.location', 'Components Location')
    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location')
    merge_type = fields.Selection([
        ("nothing_new", "New Order and Do Nothing with selected mrp orders"),
        ("cancel_new", "New Order and Cancel selected mrp orders"),
        ("remove_new", "New Order and Remove selected mrp orders"),
        ("nothing_existing", "Existing Order and Do Nothing with selected mrp orders"),
        ("cancel_existing", "Existing Order and Cancel selected mrp orders"),
        ("remove_existing", "Existing Order and Remove selected mrp orders"),
    ], string="Merge Type")

    def action_merge_mrp_order(self):
        order_list = []
        if self and self.mrp_order_ids:
            if self.mrp_order_id:
                order_list.append(self.mrp_order_id.id)
                mrp_orders = []
                product_ids = []
                values = {}
                product_qty = self.mrp_order_id.product_qty
                for line in self.mrp_order_id.move_raw_ids:
                    if line.product_id.id not in product_ids:
                        product_ids.append(line.product_id.id)
                    line_vals = {
                        'product_id':line.product_id.id,
                        'product_uom':line.product_id.uom_id.id,
                        'product_uom_qty':line.product_uom_qty,
                        'name':line.product_id.name_get()[0][1],
                        'reference':self.mrp_order_id.name,
                        'origin':self.mrp_order_id.name,
                        'location_id':line.location_id.id,
                        'location_dest_id':line.location_dest_id.id,
                        }
                    if values.get(line.product_id.id,False):
                        dic_line_vals = values.get(line.product_id.id)
                        line_vals["product_uom_qty"] = dic_line_vals["product_uom_qty"] +  line.product_uom_qty
                    values.update({
                        line.product_id.id: line_vals
                    })
                for order in self.mrp_order_ids.filtered(lambda o: o.id != self.mrp_order_id.id):
                    product_qty+=order.product_qty
                    if order.move_raw_ids:
                        for line in order.move_raw_ids:
                            if line.product_id.id not in product_ids:
                                product_ids.append(line.product_id.id)
                            line_vals = {
                                'product_id':line.product_id.id,
                                'product_uom':line.product_id.uom_id.id,
                                'product_uom_qty':line.product_uom_qty,
                                'name':line.product_id.name_get()[0][1],
                                'reference':self.mrp_order_id.name,
                                'origin':self.mrp_order_id.name,
                                'location_id':line.location_id.id,
                                'location_dest_id':line.location_dest_id.id,
                                }
                            if values.get(line.product_id.id,False):
                                dic_line_vals = values.get(line.product_id.id)
                                line_vals["product_uom_qty"] = dic_line_vals["product_uom_qty"] +  line.product_uom_qty
                            values.update({
                                line.product_id.id: line_vals
                            })
                lines = []
                for k,v in values.items():
                    lines.append((0,0,v))
                self.mrp_order_id.product_qty = product_qty
                self.mrp_order_id._onchange_move_raw()
                self.mrp_order_id._onchange_move_finished()
                    # finally cancel or remove order
                for mrp in self.env['mrp.production'].sudo().browse(self.env.context.get('active_ids')):
                    if mrp.name not in mrp_orders:
                        mrp_orders.append(mrp.name)
                    if self.merge_type == "cancel_existing":
                        mrp.sudo().action_cancel()
                    elif self.merge_type == "remove_existing":
                        mrp.sudo().action_cancel()
                        mrp.sudo().unlink()
                source = ','.join(mrp_orders)
                self.mrp_order_id.origin = source
                if self.env.company.notify_in_chatter:
                    message = '<p>This Existing mrp order has been updated from '
                    message += ','.join(mrp_orders) + str('</p>')
                    self.env['mail.message'].sudo().create({
                        'subtype_id':self.env.ref('mail.mt_comment').id,
                        'date':fields.Datetime.now(),
                        'email_from':self.env.user.partner_id.email_formatted,
                        'message_type':'comment',
                        'model':'mrp.production',
                        'res_id':self.mrp_order_id.id,
                        'record_name':self.mrp_order_id.name,
                        'body':message
                        })

            else:
                first_product = self.mrp_order_ids[0].product_id
                first_picking_type = self.mrp_order_ids[0].picking_type_id.id
                first_bom_id = self.mrp_order_ids[0].bom_id.id
                product_qty = 0.0
                mrp_orders = []
                for mrp_order in self.mrp_order_ids:
                    if mrp_order.name not in mrp_orders:
                        mrp_orders.append(mrp_order.name)
                    product_qty += mrp_order.product_qty
                source = ','.join(mrp_orders)
                created_mrp_order = self.env["mrp.production"].sudo().create({
                    "product_id": first_product.id,
                    "location_src_id": self.location_src_id.id,
                    "location_dest_id": self.location_dest_id.id,
                    "picking_type_id": first_picking_type,
                    "date_deadline": fields.Datetime.now(),
                    "user_id": self.env.user.id,
                    "company_id": self.env.company.id,
                    "product_qty": product_qty,
                    "product_uom_id": first_product.uom_id.id,
                    "bom_id": first_bom_id,
                    'origin':source,
                })
                if created_mrp_order:
                    order_list.append(created_mrp_order.id)
                    product_ids = []
                    values = {}
                    for order in self.mrp_order_ids:
                        if order.move_raw_ids:
                            for line in order.move_raw_ids:
                                if line.product_id.id not in product_ids:
                                    product_ids.append(line.product_id.id)
                                line_vals = {
                                    'product_id':line.product_id.id,
                                    'product_uom':line.product_id.uom_id.id,
                                    'product_uom_qty':line.product_uom_qty,
                                    'name':line.product_id.name_get()[0][1],
                                    'reference':order.name,
                                    'origin':order.name,
                                    'location_id':line.product_id.with_context(force_company=self.env.company.id).property_stock_production.id,
                                    'location_dest_id':self.location_dest_id.id,
                                    }
                                if values.get(line.product_id.id,False):
                                    dic_line_vals = values.get(line.product_id.id)
                                    line_vals["product_uom_qty"] = dic_line_vals["product_uom_qty"] +  line.product_uom_qty
                                values.update({
                                    line.product_id.id: line_vals
                                })
                        # finally cancel or remove order
                        if self.merge_type == "cancel_new":
                            order.sudo().action_cancel()
                            order_list.append(order.id)
                        elif self.merge_type == "remove_new":
                            order.sudo().action_cancel()
                            order.sudo().unlink()
                    lines = []
                    for k,v in values.items():
                        lines.append((0,0,v))
                    created_mrp_order._onchange_move_raw()
                    created_mrp_order._onchange_move_finished()
                    if self.env.company.notify_in_chatter:
                        message = '<p>This mrp order has been created from '
                        message += ','.join(mrp_orders) + str('</p>')
                        self.env['mail.message'].sudo().create({
                            'subtype_id':self.env.ref('mail.mt_comment').id,
                            'date':fields.Datetime.now(),
                            'email_from':self.env.user.partner_id.email_formatted,
                            'message_type':'comment',
                            'model':'mrp.production',
                            'res_id':created_mrp_order.id,
                            'record_name':created_mrp_order.name,
                            'body':message
                            })

            if order_list:
                return {
                    "name": _("Manufacturing Orders"),
                    "domain": [("id", "in", order_list)],
                    "view_type": "form",
                    "view_mode": "tree,form",
                    "res_model": "mrp.production",
                    "view_id": False,
                    "type": "ir.actions.act_window",
                }

    @api.model
    def default_get(self, fields):
        rec = super(ShMergeMrpOrderWizard, self).default_get(fields)
        active_ids = self._context.get("active_ids")

        if not active_ids:
            raise UserError(
                _("Programming error: wizard action executed without active_ids in context."))

        if len(self._context.get("active_ids", [])) < 2:
            raise UserError(
                _("Please Select atleast two mrp orders to perform merge operation."))

        mrp_orders = self.env["mrp.production"].browse(active_ids)

        if any(order.state not in ["draft", "confirmed", "progress"] for order in mrp_orders):
            raise UserError(
                _("You can only merge mrp orders which are in Draft/Confirmed/In Progress state"))
        if len(mrp_orders.ids) > 0:
            first_product = mrp_orders[0].product_id
            rec.update({
                'product_id': first_product.id
            })
            for order in mrp_orders:
                if order.product_id.id != first_product.id:
                    raise UserError(
                        _("You can only merge mrp orders which are in same product/bill of material. "))
        if self.env.company.merge_type:
            rec.update({
                'merge_type':self.env.company.merge_type
                })
        rec.update({
            "mrp_order_ids": [(6, 0, mrp_orders.ids)],
        })
        return rec
