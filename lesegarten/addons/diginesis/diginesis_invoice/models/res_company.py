# -*- coding: utf-8 -*-
from odoo import fields, models


class Company(models.Model):
	_inherit = 'res.company'

	add_invoice_allocate_difference_line = fields.Boolean(string='Add Difference Line at Invoice Allocate')
