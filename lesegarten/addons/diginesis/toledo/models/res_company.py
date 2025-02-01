from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError

class Company(models.Model):
	_name = 'res.company'
	_inherit = 'res.company'

	invoice_drafter_partner_id = fields.Many2one('res.partner', string='Invoice Drafter',help="Invoice drafter, it will appear in invoice print")
	company_currency_pricelist = fields.Many2one('product.pricelist', string="Default Pricelist", help="Default pricelist in company currency")