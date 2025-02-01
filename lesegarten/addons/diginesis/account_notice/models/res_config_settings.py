# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_notice_journal_id = fields.Many2one('account.journal', string='Vendor Notice Journal', related="company_id.vendor_notice_journal_id", readonly=False, help="Journal for Vendor Notice")
    vendor_notice_account_id = fields.Many2one('account.account', string='Vendor Notice Account', related="company_id.vendor_notice_account_id", readonly=False, help="Account for Vendor Notice")
    customer_notice_journal_id = fields.Many2one('account.journal', string='Customer Notice Journal', related="company_id.customer_notice_journal_id", readonly=False, help="Journal for Customer Notice")
    customer_notice_account_id = fields.Many2one('account.account', string='Customer Notice Account', related="company_id.customer_notice_account_id", readonly=False, help="Account for Customer Notice")
    do_account_entries_for_customer_notice = fields.Boolean(related="company_id.do_account_entries_for_customer_notice", readonly=False,)
    print_notice_custom_reference = fields.Boolean(related="company_id.print_notice_custom_reference", readonly=False)