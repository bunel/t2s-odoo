from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ro_spv_bill_journal_id = fields.Many2one(related="company_id.l10n_ro_spv_bill_journal_id", readonly=False)
