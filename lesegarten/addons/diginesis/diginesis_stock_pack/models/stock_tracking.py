# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class StockTracking(models.Model):
    _name ='stock.tracking'
    _inherit = ['mail.thread']
    _description = "Stock Tracking"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)

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

    move_ids = fields.One2many('stock.move', 'stock_tracking_id', string="Stock Moves", help="Moves for this pack")

    _sql_constraints = [
        ('product_pack_count_gt_zero', 'CHECK (product_pack_count>0)', _('Pack Number must be greater than 0') ),
        ('product_pallet_count_gt_zero', 'CHECK (product_pallet_count>=0)', _('Pallet Number must be positive!') ),
    ]
