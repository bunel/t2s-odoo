# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError

RECEPTION_MODE = [('notice_reception', 'Reception with Notice'), ('bill_reception', 'Reception with Bill'), ('bill_notice_reception', 'Invoice then Notice then Reception')]


class Partner(models.Model):
    _inherit = "res.partner"
    _name = "res.partner"

    reception_mode = fields.Selection(RECEPTION_MODE, string="Reception Mode")
    supplier_incoterm_id = fields.Many2one('account.incoterms', string='Incoterm', help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

