# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount
from odoo.addons.procurement_workflow.models.res_partner import RECEPTION_MODE


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()

        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)
        res.update({'is_landed_costs_line': self.product_id and self.product_id.landed_cost_ok or False})

        return res
