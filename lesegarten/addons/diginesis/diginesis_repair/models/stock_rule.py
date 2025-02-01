# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, html_escape


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['repair_id']
        return fields
