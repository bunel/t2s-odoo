# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = "stock.picking"

    nir_number = fields.Char(string="NIR Number")

    def _action_done(self):
        res = super(Picking, self)._action_done()

        incoming = self.filtered(lambda x: x.location_dest_id and x.location_dest_id._should_be_valued() and x.location_id and x.location_id.usage == 'supplier' or\
                                           any(m._is_dropshipped() for m in x.move_lines if m.state != 'cancel'))
        incoming_for_nir = incoming.filtered(lambda x: x.mapped('picking_type_id.warehouse_id.nir_number_sequence_id'))
        for picking in incoming_for_nir:
            sequence = picking.picking_type_id.warehouse_id.nir_number_sequence_id
            picking.write({'nir_number': sequence.next_by_id()})

        return res