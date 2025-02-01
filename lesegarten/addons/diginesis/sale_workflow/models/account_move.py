# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning


class AccountMove(models.Model):
	_inherit = 'account.move'
	
	# def _compute_picking(self):
	# 	for invoice in self:
	# 		if invoice.move_type in ['out_invoice', 'out_refund']:
	# 			pickings = self.env['stock.picking'].search([('invoice_id', '=', invoice.id)])
	# 			invoice.picking_ids = pickings
	# 			invoice.picking_count = len(set(pickings and pickings.ids or []))
	# 		else:
	# 			invoice.picking_ids = False
	# 			invoice.picking_count = 0
	#
	# picking_count = fields.Integer(compute='_compute_picking', string='Delivery Count', default=0)
	# picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Delivery Orders', copy=False)
	#
	# def action_view_picking(self):
	# 	action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
	# 	action['context'] = {}
	#
	# 	pick_ids = self.mapped('picking_ids').ids
	#
	# 	if len(pick_ids) > 1:
	# 		action['domain'] = [('id', 'in', pick_ids)]
	# 	elif len(pick_ids) == 1:
	# 		res = self.env.ref('stock.view_picking_form', False)
	# 		action['views'] = [(res and res.id or False, 'form')]
	# 		action['res_id'] = pick_ids and pick_ids[0] or False
	# 	return action