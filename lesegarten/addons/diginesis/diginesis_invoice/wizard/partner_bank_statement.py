# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, datetime


class PartnerBankStatement(models.TransientModel):
    _name = "partner.bank.statement"
    _description = "Partner Bank Statement"

    date = fields.Date("Date", required=True, default=lambda self: fields.Date.today())
    invoice_type = fields.Selection([('vendor', 'Vendor Bill'), ('customer', 'Customer'), ('vendor_customer', 'Vendor and Customer')], string="Invoice Type", default='vendor_customer')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    account_ids = fields.Many2many('account.account', string='Accounts', required=True)

    def _prepare_report_data(self):
        data = {'form': self.read(['date', 'invoice_type', 'currency_id', 'account_ids'])[0]}
        data['form']['partner_ids'] = self.env.context.get('active_ids') or []
        data['form']['currency_id'] = data['form']['currency_id'] and data['form']['currency_id'][0] or False
        data['form']['invoice_type'] = 'vendor_customer'
        data['form']['doc_model'] = 'res.partner'

        return data

    def action_print(self):
        self.ensure_one()

        data = self._prepare_report_data()
        report_action = self.env.ref('diginesis_invoice.report_partner_bank_statement').with_context(
            discard_logo_check=True).report_action(None, data=data)

        return report_action
