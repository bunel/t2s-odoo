# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError

class AddPickingTrackingLine(models.TransientModel):
    _name = 'add.picking.tracking.line'
    _description = "Add Picking Tracking Line"

    name = fields.Char(string="Name")
    picking_tracking_id = fields.Many2one('add.picking.tracking', string="Picking Tracking")
    quantity = fields.Float('Pack Quantity')
    stock_move_id = fields.Many2one('stock.move', string="Stock move")
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string="Product UoM")
    stock_tracking_id = fields.Many2one('stock.tracking', string='Pack')
    product_qty = fields.Float(string='Move Quantity')
    company_id = fields.Many2one('res.company', string="Company")


class AddPickingTracking(models.TransientModel):
    _name = 'add.picking.tracking'
    _description = "Add Picking Tracking"

    name = fields.Char(string="Name", required=True)
    picking_id = fields.Many2one('stock.picking', string='Picking')
    move_id = fields.Many2one('stock.move', string='Move')

    line_ids = fields.One2many('add.picking.tracking.line', 'picking_tracking_id', string='Lines')

    stock_tracking_id = fields.Many2one('stock.tracking', string="Pack")

    pack_address = fields.Char('Address')
    pack_note = fields.Char('Note')
    serial = fields.Char('Additional Reference')
    date = fields.Datetime('Date', required=True)

    gross_weight = fields.Float('Pack Brut Weight', help="Weight in kg")
    net_weight = fields.Float('Pack Net Weight', help="Weight in kg")

    product_pack_id = fields.Many2one('product.pack', 'Pack Type', required=True)
    product_pack_count = fields.Float('Pack Number', required=True, default=1)

    product_pallet_id = fields.Many2one('product.pallet', 'Pallet Type')
    product_pallet_count = fields.Float('Pallet Number')

    @api.model
    def default_get(self, my_fields):
        res = super(AddPickingTracking, self).default_get(my_fields)
        picking = False
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'stock.picking':
            res.update({'picking_id': active_id, 'move_id': False,})
            picking = self.env['stock.picking'].browse(active_id)
        elif active_model == 'stock.move':
            res.update({'picking_id': False, 'move_id': active_id,})
            move = self.env['stock.move'].browse(active_id)
            picking = move and move.picking_id or False

        name_sequence = self.env.ref('diginesis_stock_pack.seq_pack_name')._next()
        res.update({'name': name_sequence, 'date': picking and picking.state in ['done'] and picking.date or fields.Datetime.now()})

        return res

    @api.onchange('picking_id', 'move_id')
    def onchange_picking_move(self):
        if self.move_id:
            move = self.move_id
            product = move.product_id
            self.line_ids = [(5, False), (0, 0, {
                                'stock_move_id': move.id,
                                'product_id': product and product.id or False,
                                'uom_id': product.uom_id and product.uom_id.id or False,
                                'stock_tracking_id': move.stock_tracking_id and move.stock_tracking_id.id or False,
                                'product_qty': move.product_qty or 0,
                                'company_id': move.company_id and move.company_id.id or False,
                                'quantity':  0 if self.move_id.stock_tracking_id else self.move_id.product_qty,
                                })]

            #self.net_weight = self.move_id.product_id.weight * self.move_id.product_qty
        elif self.picking_id:
            lines = [(5, False)]
            for move in self.picking_id.move_lines.filtered(lambda x: not x.stock_tracking_id):
                product = move.product_id
                lines.append((0, 0, {
                        'stock_move_id': move.id,
                        'product_id': product and product.id or False,
                        'uom_id': product.uom_id and product.uom_id.id or False,
                        'stock_tracking_id': move.stock_tracking_id and move.stock_tracking_id.id or False,
                        'product_qty': move.product_qty or 0,
                        'company_id': move.company_id and move.company_id.id or False,
                        'quantity': 0 if move.stock_tracking_id else move.product_qty,
                    }))
            self.line_ids = lines
            #self.net_weight = sum([m.product_id.weight * m.product_qty for m in self.picking_id.move_lines])
        else:
            self.line_ids = False
            #self.net_weight = 0

    @api.onchange('line_ids')
    def onchange_lines(self):
        if self.line_ids:
            self.net_weight = sum([l.product_id.weight * l.quantity for l in self.line_ids])
        else:
            self.net_weight = 0

    def _action_check(self):
        self.ensure_one()

        if all(float_is_zero(line.quantity, precision_rounding=line.uom_id.rounding) for line in self.line_ids):
            raise UserError(_('Cannot create empty pack'))

        for line in self.line_ids:
            compare = float_compare(line.quantity, line.product_qty, precision_rounding=line.uom_id.rounding)
            if line.stock_move_id.state == 'done' and compare != 0:
                raise UserError(_('Pack Split can not be used on done moves'))
            if compare > 0:
                raise UserError(_('New pack quantity can not be bigger than stock move quantity'))

        return True

    def action_split(self):
        self.ensure_one()

        self._action_check()

        new_pack_tracking = self.env['stock.tracking'].create(self._prepare_pack())

        for line in self.line_ids.filtered(lambda x: x.quantity):
            stock_move = line.stock_move_id
            remaining_qty = stock_move.product_qty - line.quantity

            if not float_is_zero(remaining_qty, precision_rounding=stock_move.product_uom.rounding):
                stock_move.write({'product_uom_qty': line.uom_id._compute_quantity(remaining_qty, stock_move.product_uom), })
                new_stock_move = stock_move.copy(default={'product_uom_qty':  line.uom_id._compute_quantity(line.quantity, stock_move.product_uom),
                                                          'stock_tracking_id': new_pack_tracking.id,
                                                          'price_unit': stock_move.price_unit or 0
                                                        })
                new_stock_move._action_confirm()
            else:
                stock_move.write({'stock_tracking_id': new_pack_tracking.id})

        return {'type': 'ir.actions.act_window_close'}

    def _prepare_pack(self):
        return {
            'name': self.name,
            'pack_address': self.pack_address,
            'pack_note': self.pack_note,
            'serial': self.serial,
            'date': self.date,
            'gross_weight': self.gross_weight,
            'net_weight': self.net_weight,
            'product_pack_id': self.product_pack_id and self.product_pack_id.id or False,
            'product_pack_count': self.product_pack_count,
            'product_pallet_id': self.product_pallet_id and self.product_pallet_id.id or False,
            'product_pallet_count': self.product_pallet_count,
        }
