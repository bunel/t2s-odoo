# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_ro_landed_cost = fields.Boolean("Romania - Landed Costs",
                                               help="Affect landed costs on reception operations and split them among products to update their cost price.")
    lc_journal_id = fields.Many2one('account.journal', string='Default Journal', related='company_id.lc_journal_id', readonly=False)

