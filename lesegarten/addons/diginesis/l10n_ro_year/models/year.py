# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_round

MONTHS_OF_YEAR = [('1', 'January'),
                    ('2', 'February'),
                    ('3', 'March'),
                    ('4', 'April'),
                    ('5', 'May'),
                    ('6', 'June'),
                    ('7', 'July'),
                    ('8', 'August'),
                    ('9', 'September'),
                    ('10', 'October'),
                    ('11', 'November'),
                    ('12', 'December')]


class L10nYear(models.Model):
    _name = 'l10n.year'
    _description = "Localization Year"

    name = fields.Char(string="Name", required=True)
    year = fields.Integer(string="Year", required=True)
    active = fields.Boolean(string="Active", default=True,
                            help="If unchecked, it will allow you to hide the product without removing it.")
