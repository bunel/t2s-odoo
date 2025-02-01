# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import format_date


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()

        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id and self.purchase_line_id.order_id.reception_mode:
            return self.price_unit
        return super(StockMove, self)._get_price_unit()