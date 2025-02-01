# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _invoice_overdue_balance(self):
        AccountMove = self.env['account.move']
        
        domain = [('amount_residual_signed', '>', 0), 
                    ('invoice_date_due', '<', fields.Date.today()), 
                    ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])]
        
        for partner in self:
            total = 0            
            invoices = AccountMove.search(domain + [('partner_id', '=', partner.id)])
            if invoices:
                total = sum(invoices.mapped('amount_residual_signed'))
            payments_total = 0
            if partner.property_account_receivable_id:
                self.env.cr.execute("""
                SELECT sum(aml.amount_residual) from account_move_line aml
                JOIN account_move am ON am.id=aml.move_id 
                WHERE aml.partner_id=%s 
                AND aml.account_id=%s 
                AND aml.reconciled IS NOT TRUE
                AND am.move_type='entry'
                AND aml.date <= %s
                """ , (partner.id,partner.property_account_receivable_id.id, fields.Date.today()))
                payments_res = self.env.cr.fetchone()
                payments_total = payments_res and payments_res[0] or 0
            partner.total_overdue_balance = total + payments_total

    total_overdue_balance = fields.Monetary(compute='_invoice_overdue_balance', string="Total Overdue Balance")

    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['user_id']
