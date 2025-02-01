from odoo import api, fields, models, tools, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class Company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    vendor_notice_journal_id = fields.Many2one('account.journal', string="Vendor Notice Journal", help="Journal for Vendor Notice")
    vendor_notice_account_id = fields.Many2one('account.account', string="Vendor Notice Account", help="Account for Vendor Notice")
    customer_notice_journal_id = fields.Many2one('account.journal', string="Customer Notice Journal", help="Journal for Customer Notice")
    customer_notice_account_id = fields.Many2one('account.account', string="Customer Notice Account", help="Account for Customer Notice")
    do_account_entries_for_customer_notice = fields.Boolean(string="Account Entries for Customer Notice", default=False)
    print_notice_custom_reference = fields.Boolean(string="Print Only Order Reference", default=False)