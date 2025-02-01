# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShMinvMergeInvoiceWizard(models.TransientModel):
    _name = "sh.minv.merge.invoice.wizard"
    _description = "Merge Invoice Wizard"

    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True)
    invoice_id = fields.Many2one("account.move", string="Invoice")
    invoice_ids = fields.Many2many("account.move", string="Invoices")
    inv_type = fields.Char(string="Invoice Type")

    merge_type = fields.Selection([
        ("nothing", "Do Nothing"),
        ("cancel", "Cancel Other Invoices"),
        ("remove", "Remove Other Invoices"),
    ], default="nothing", string="Merge Type")

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self:
            self.invoice_id = False

    def action_merge_invoice(self):
        inv_list = []
        if self and self.partner_id and self.invoice_ids:
            if self.invoice_id:
                inv_list.append(self.invoice_id.id)
                inv_line_vals = {"move_id": self.invoice_id.id}
                sequence = 10
                if self.invoice_id.invoice_line_ids:
                    for existing_line in self.invoice_id.invoice_line_ids:
                        existing_line.sudo().write({
                            'sequence': sequence
                        })
                        sequence += 1
                invoices = self.env['account.move'].sudo().search(
                    [('id', '!=', self.invoice_id.id), ('id', 'in', self.invoice_ids.ids)], order='id asc')
                for inv in invoices:
                    if inv.invoice_line_ids:
                        for line in inv.invoice_line_ids:
                            order_line = self.env['sale.order.line'].search([('invoice_lines.id','=',line.id)])
                            if not order_line:
                                order_line = self.env['purchase.order.line'].search([('invoice_lines.id','=',line.id)])
                            merged_line = line.with_context(check_move_validity=False).copy(
                                default=inv_line_vals)
                            order_line.with_context(check_move_validity=False).invoice_lines = [(6,0,merged_line.ids)]
                            merged_line.sudo().write({
                                'sequence': sequence
                            })
                            sequence += 1
                    # finally cancel or remove order
                    if self.merge_type == "cancel":
                        inv.sudo().button_cancel()
                        inv_list.append(inv.id)
                    elif self.merge_type == "remove":
                        inv.sudo().unlink()
                self.invoice_id.with_context(
                    check_move_validity=False)._onchange_partner_id()
                self.invoice_id._onchange_invoice_line_ids()
            else:
                created_inv = self.env["account.move"].with_context({
                    "trigger_onchange": True,
                    "onchange_fields_to_trigger": [self.partner_id.id],
                    "check_move_validity": False,
                    "default_move_type": self.inv_type
                }).create({
                    "partner_id": self.partner_id.id,
                    "move_type": self.inv_type,
                    'invoice_user_id' : self.env.user.id
                })
                if created_inv:
                    inv_list.append(created_inv.id)
                    inv_line_vals = {"move_id": created_inv.id}
                    sequence = 10
                    invoices = self.env['account.move'].sudo().search(
                        [('id', 'in', self.invoice_ids.ids)], order='id asc')
                    for inv in invoices:
                        if inv.invoice_line_ids:
                            for line in inv.invoice_line_ids:
                                order_line = self.env['sale.order.line'].search([('invoice_lines.id','=',line.id)])
                                if not order_line:
                                    order_line = self.env['purchase.order.line'].search([('invoice_lines.id','=',line.id)])
                                merged_line = line.with_context(check_move_validity=False).copy(
                                    default=inv_line_vals)
                                order_line.with_context(check_move_validity=False).invoice_lines = [(6,0,merged_line.ids)]
                                merged_line.sudo().write({
                                    'sequence': sequence
                                })
                                sequence += 1

                        # finally cancel or remove order
                        if self.merge_type == "cancel":
                            inv.sudo().button_cancel()
                            inv_list.append(inv.id)
                        elif self.merge_type == "remove":
                            inv.sudo().unlink()
                    created_inv._onchange_partner_id()
                    created_inv._onchange_invoice_line_ids()

            if inv_list:
                #return action and view as per invoice type.
                view = self.env.ref("account.view_invoice_tree")
                if self.inv_type in ["out_invoice", "out_refund"]:
                    view = self.env.ref("account.view_invoice_tree")
                elif self.inv_type in ["in_invoice", "in_refund"]:
                    view = self.env.ref("account.view_invoice_tree")

                #action name
                action_name = "Customer Invoices"
                if self.inv_type == "out_invoice":
                    action_name = "Customer Invoices"
                elif self.inv_type == "out_refund":
                    action_name = "Customer Credit Notes"
                elif self.inv_type == "in_invoice":
                    action_name = "Vendor Bills"
                elif self.inv_type == "in_refund":
                    action_name = "Vendor Credit Notes"

                return {
                    "name": action_name,
                    "type": "ir.actions.act_window",
                    "view_mode": "tree,form",
                    "res_model": "account.move",
                    "views": [(view.id, "tree"), (False, "form")],
                    "view_id": view.id,
                    "domain": [("id", "in", inv_list)]
                }

    @api.model
    def default_get(self, fields):
        rec = super(ShMinvMergeInvoiceWizard, self).default_get(fields)
        active_ids = self._context.get("active_ids")

        # Check for selected invoices ids
        if not active_ids:
            raise UserError(
                _("Programming error: wizard action executed without active_ids in context.")
            )

        # Check if only one invoice selected.
        if len(self._context.get("active_ids", [])) < 2:
            raise UserError(
                _("Please Select atleast two invoices to perform merge operation.")
            )

        invoice_ids = self.env["account.move"].browse(active_ids)

        # Check all invoice are draft state
        if any(inv.state != "draft" for inv in invoice_ids):
            raise UserError(
                _("You can only merge invoices which are in draft state")
            )

        # return frist invoice partner id and invoice ids,
        rec.update({
            "partner_id": invoice_ids[0].partner_id.id if invoice_ids[0].partner_id else False,
            "invoice_ids": [(6, 0, invoice_ids.ids)],
            "inv_type": invoice_ids[0].move_type,
        })
        return rec
