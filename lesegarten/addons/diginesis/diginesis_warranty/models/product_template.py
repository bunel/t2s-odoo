# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError

class ProductTemplate(models.Model):
	_name = "product.template"
	_inherit = "product.template"

	warranty = fields.Float('Warranty', help="Warranty in months")
	