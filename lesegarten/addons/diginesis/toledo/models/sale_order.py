# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.tools.misc import get_lang
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round
import math

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	offer_validity = fields.Char(string="Offer validity", help="How many working days this offer is valid for")
