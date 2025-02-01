# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class Picking(models.Model):
    _inherit = "stock.picking"
    _name = "stock.picking"

    stock_tracking_ids = fields.Many2many('stock.tracking', compute="_compute_operations_packs", compute_sudo=True, )

    @api.depends('move_lines', 'move_lines.stock_tracking_id')
    def _compute_operations_packs(self):
        for picking in self:
            picking.stock_tracking_ids = picking.mapped('move_lines.stock_tracking_id')
