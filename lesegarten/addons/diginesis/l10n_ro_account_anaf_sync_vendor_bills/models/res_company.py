from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_spv_bill_journal_id = fields.Many2one('account.journal', string="SPV Bill Journal")
