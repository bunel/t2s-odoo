# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class AccountGroup(models.Model):
    _inherit = "account.group"
    _name = "account.group"

    functionality_id = fields.Many2one('account.account.functionality', 'Functionality',
                                       help="Account Group functionality will influence the balance")
    off_balancesheet = fields.Boolean('Extrabilantier', default=False)


class AccountAccount(models.Model):
    _inherit = "account.account"
    _name = "account.account"

    functionality_id = fields.Many2one('account.account.functionality', 'Functionality',
                                       help="Account functionality will influence the balance")
    off_balancesheet = fields.Boolean('Extrabilantier', default=False)


class AccountAccountFunctionality(models.Model):
    _name = "account.account.functionality"
    _description = "Account Functionality"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    account_ids = fields.One2many('account.account', 'functionality_id', 'Accounts')
    account_group_ids = fields.One2many('account.group', 'functionality_id', 'Account Groups')

    def _set_accounts(self, account_domain):
        """ called from account_functionality.xml"""

        if account_domain:
            accounts = self.env['account.account'].search(account_domain)
            if accounts:
                self.write({'account_ids': [(5, False), (6, 0, accounts.ids)]})

    def _set_account_groups(self, account_group_domain):
        """ called from account_functionality.xml"""
        if account_group_domain:
            account_groups = self.env['account.group'].search(account_group_domain)
            if account_groups:
                self.write({'account_group_ids': [(5, False), (6, 0, account_groups.ids)]})