# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShMsoMergeSaleOrderWizard(models.TransientModel):
    _name = "sh.mso.merge.sale.order.wizard"
    _description = "Merge Sale Order Wizard"

    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    sale_order_ids = fields.Many2many("sale.order", string="Sale Orders")

    merge_type = fields.Selection([
        ("nothing", "Do Nothing"),
        ("cancel", "Cancel Other Sale Orders"),
        ("remove", "Remove Other Sale Orders"),
    ], default="nothing", string="Merge Type")

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self:
            self.sale_order_id = False

    def action_merge_sale_order(self):
        order_list = []
        if self and self.partner_id and self.sale_order_ids:
            if self.sale_order_id:
                order_list.append(self.sale_order_id.id)
                order_line_vals = {"order_id": self.sale_order_id.id}
                sequence = 10
                if self.sale_order_id.order_line:
                    for existing_line in self.sale_order_id.order_line:
                        existing_line.sudo().write({
                            'sequence': sequence
                        })
                        sequence += 1
                orders = self.env['sale.order'].sudo().search(
                    [('id', '!=', self.sale_order_id.id), ('id', 'in', self.sale_order_ids.ids)], order='id asc')
                for order in orders:
                    if order.order_line:
                        for line in order.order_line:
                            merged_line = line.copy(default=order_line_vals)
                            merged_line.sudo().write({
                                'sequence': sequence
                            })
                            sequence += 1

                    # finally cancel or remove order
                    if self.merge_type == "cancel":
                        order.sudo().action_cancel()
                        order_list.append(order.id)
                    elif self.merge_type == "remove":
                        order.sudo().action_cancel()
                        order.sudo().unlink()

            else:
                created_so = self.env["sale.order"].with_context({
                    "trigger_onchange": True,
                    "onchange_fields_to_trigger": [self.partner_id.id]
                }).create({"partner_id": self.partner_id.id})
                if created_so:
                    order_list.append(created_so.id)
                    order_line_vals = {"order_id": created_so.id}
                    sequence = 10
                    orders = self.env['sale.order'].sudo().search(
                        [('id', 'in', self.sale_order_ids.ids)], order='id asc')
                    for order in orders:
                        if order.order_line:
                            for line in order.order_line:
                                merged_line = line.copy(
                                    default=order_line_vals)
                                merged_line.sudo().write({
                                    'sequence': sequence
                                })
                                sequence += 1

                        # finally cancel or remove order
                        if self.merge_type == "cancel":
                            order.sudo().action_cancel()
                            order_list.append(order.id)
                        elif self.merge_type == "remove":
                            order.sudo().action_cancel()
                            order.sudo().unlink()

            if order_list:
                return {
                    "name": _("Quotations"),
                    "domain": [("id", "in", order_list)],
                    "view_type": "form",
                    "view_mode": "tree,form",
                    "res_model": "sale.order",
                    "view_id": False,
                    "type": "ir.actions.act_window",
                }

    @api.model
    def default_get(self, fields):
        rec = super(ShMsoMergeSaleOrderWizard, self).default_get(fields)
        active_ids = self._context.get("active_ids")

        # Check for selected invoices ids
        if not active_ids:
            raise UserError(
                _("Programming error: wizard action executed without active_ids in context."))

        # Check if only one sale order selected.
        if len(self._context.get("active_ids", [])) < 2:
            raise UserError(
                _("Please Select atleast two quotations to perform merge operation."))

        sale_orders = self.env["sale.order"].browse(active_ids)

        # Check all sale order are draft state
        if any(order.state not in ["draft", "sent"] for order in sale_orders):
            raise UserError(
                _("You can only merge sale orders which are in Quotation AND Quotation sent state"))

        # return frist sale order partner id and sale order ids,
        rec.update({
            "partner_id": sale_orders[0].partner_id.id if sale_orders[0].partner_id else False,
            "sale_order_ids": [(6, 0, sale_orders.ids)],
        })
        return rec
