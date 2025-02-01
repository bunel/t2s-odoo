# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round, float_is_zero


class RepairBarcodeScan(models.TransientModel):
    _name = 'repair.barcode.scan'
    _inherit = 'barcodes.barcode_events_mixin'
    _description = 'Repair Barcode Scan'

    def on_barcode_scanned(self, barcode):

        action = self.env['ir.actions.act_window']._for_xml_id('diginesis_warranty.diginesis_serial_number_tree_action')
        action['res_id'] = barcode and int(barcode) or False

        return action

    def go_serial_number_from_barcode(self, barcode):
        action = self.env['ir.actions.act_window']._for_xml_id('diginesis_warranty.diginesis_serial_number_tree_action')
        action['res_id'] = barcode and int(barcode) or False

        return action

