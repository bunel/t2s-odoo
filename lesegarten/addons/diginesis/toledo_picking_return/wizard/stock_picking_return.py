# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_move_default_values(self, return_line, new_picking):
        res = super(ReturnPicking, self)._prepare_move_default_values(return_line, new_picking)

        stock_move = return_line.move_id
        if stock_move.location_dest_id and stock_move.location_dest_id.usage == 'customer' and stock_move.stock_valuation_layer_ids and not res.get('price_unit'):
            res.update({'price_unit': return_line.move_id.stock_valuation_layer_ids[0].unit_cost or 0})

        return res

    def _create_returns(self):
        new_picking_id, picking_type_id = super(ReturnPicking, self)._create_returns()

        if new_picking_id:
            moves = self.env['stock.move'].search([('picking_id', '=', new_picking_id), ('location_id.usage', '=', 'customer')])
            for move in moves.filtered(lambda x: x.move_line_ids):
                move.move_line_ids.write({'price_unit': move.price_unit})

        return new_picking_id, picking_type_id

