# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, _, api, fields, models


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = "stock.picking"

    is_warranty = fields.Boolean(string="Warranty", default=False)

    def _check_incoming_cost(self):
        self_wo_warranty = self.filtered(lambda x: not x.is_warranty)

        return super(Picking, self_wo_warranty)._check_incoming_cost()
