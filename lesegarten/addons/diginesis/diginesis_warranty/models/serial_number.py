# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SerialNumber(models.Model):
	_name = "serial.number"
	_inherit = ['mail.thread']
	_description = "Serial Number"

	name = fields.Char('Name')
	note = fields.Char('Note')
	partner_id = fields.Many2one('res.partner', string="Client")
	product_id = fields.Many2one('product.product', 'Product', required=True, tracking=True)
	warranty = fields.Float('Warranty Period', tracking=True, help="Warranty period in months")
	warranty_expiration_date = fields.Date('Warranty Expiration Date', tracking=True)
	state = fields.Selection([('sold', 'Sold'), ('available', 'Available')], string="Status", default='available')
	invoice_date = fields.Datetime('Invoice Date')
	
	_sql_constraints = [
		('nameprod_uniq', 'unique(name, product_id)', 'Serial Number must be unique per Product!'),
	]