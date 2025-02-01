# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools import float_compare

class Repair(models.Model):
	_inherit = 'repair.order'

	repair_notes = fields.Text('Repair Notes')
	client_ref = fields.Char('Client Reference', size=64, help="Please fill client reference")
	schedule_date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
	picking_id = fields.Many2one('stock.picking', copy=False)
	to_deliver = fields.Boolean('Deliver', default=False)	
	invoice_method = fields.Selection(default="after_repair")
	management_id = fields.Many2one('stock.picking.type', string="Management", required=True)
	
	@api.onchange('guarantee_limit')
	def onchange_guarantee_limit(self):
		to_invoice = False if (self.guarantee_limit and self.guarantee_limit >= fields.Date.today()) else True
		self.operations.write({'to_invoice': to_invoice})
		self.fees_lines.write({'to_invoice': to_invoice})
		
	@api.onchange('management_id')
	def onchange_management(self):
				
		if not self.management_id:
			for operation in self.operations:
				operation.onchange_operation_type()
			return 
					
		for operation in self.operations:
			if operation.type == 'add':	
				operation.location_id = self.management_id.default_location_src_id or False
				operation.location_dest_id = self.management_id.default_location_dest_id or False
			else:
				return_management_id = self.management_id.return_picking_type_id				
				operation.location_id = return_management_id and return_management_id.default_location_src_id or False
				operation.location_dest_id = return_management_id and return_management_id.default_location_dest_id or False
		
	def action_validate(self):
		self.ensure_one()
		if self.location_id and self.location_id.usage != 'internal':
			return self.action_repair_confirm()
			
		res = super(Repair, self).action_validate()
		
		#workaround for not showing wizard named stock.warn.insufficient.qty.repair because we can repair without having the repairing product in stock
		#we also want to call super()
		if res and isinstance(res, dict) and res.get('res_model') == 'stock.warn.insufficient.qty.repair':
			return self.action_repair_confirm()
			
		return res
	
	def action_repair_confirm(self):
		res = super(Repair, self).action_repair_confirm()
		self.mapped('operations')._action_launch_stock_rule()
		return res
	
	def action_repair_cancel(self):
		res = super(Repair, self).action_repair_cancel()
		
		pickings = self.mapped('picking_id')
		if pickings: 
			pickings.action_cancel()

		procurement_groups = self.env['procurement.group']
		for op in self.mapped('operations'):
			proc = op._get_procurement_group()
			if proc:
				procurement_groups |= proc

		if procurement_groups:
			procurement_groups.mapped('stock_move_ids').filtered(lambda x: x.state not in ['done', 'cancel'])._action_cancel()
			
		return res
	
	def action_repair_end(self):
		res = super(Repair, self).action_repair_end()

		StockMove = self.env['stock.move']
		StockPicking = self.env['stock.picking']
		
		pickings = self.env['stock.picking']
		
		picking_type_id = self.env.company.repair_delivery_picking_type
		repairs_to_deliver = self.filtered(lambda x: x.to_deliver and (not x.picking_id or x.picking_id.state in ['cancel']))
		
		if repairs_to_deliver and not picking_type_id:
			raise UserError(_('Please configure Repair Delivery Operation'))
		
		location_id = picking_type_id.default_location_src_id and picking_type_id.default_location_src_id.id or False
		location_dest_id = picking_type_id.default_location_dest_id and picking_type_id.default_location_dest_id.id or False
		
		for repair in repairs_to_deliver:			
			picking = StockPicking.create({
				'origin': repair.name,
				'state': 'draft',
				'move_type': 'one',
				'partner_id': repair.address_id and repair.address_id.id or False,
				'note': repair.internal_notes,
				'location_id': location_id,
				'location_dest_id': location_dest_id,
				'picking_type_id': picking_type_id.id				
			})	
			
			move = StockMove.create({'name': repair.name,
									'picking_id': picking and picking.id or False,
									'product_id': repair.product_id.id,
									'product_uom': repair.product_id.uom_id.id,
									'product_uom_qty': repair.product_qty,
									'partner_id': repair.address_id and repair.address_id.id or False,
									'location_id': location_id,
									'location_dest_id': location_dest_id,
									})
						
			pickings += picking
			repair.write({'picking_id': picking.id, 'move_id': move.id})

		if pickings:
			pickings.action_assign()
			
		return res
	
	def action_repair_done(self):		
		if self.filtered(lambda repair: not repair.repaired):
			raise UserError(_("Repair must be repaired in order to make the product moves."))
		
		StockQuant = self.env['stock.quant']

		self._check_company()
		self.operations._check_company()
		self.fees_lines._check_company()

		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		
		res = {}
		
		for repair in self:
			# Try to create move with the appropriate owner
			owner_id = False
			available_qty_owner = StockQuant._get_available_quantity(repair.product_id, repair.location_id, repair.lot_id, owner_id=repair.partner_id, strict=True)
			if float_compare(available_qty_owner, repair.product_qty, precision_digits=precision) >= 0:
				owner_id = repair.partner_id.id

			moves = self.env['stock.move']
			for operation in repair.operations.filtered(lambda x: x.product_id and x.product_id.type != 'service' and x.move_id):
				procurement_group = operation._get_procurement_group()
				group_moves = procurement_group.mapped('stock_move_ids').filtered(lambda x: x.state not in ['done', 'cancel'])
				if not group_moves:
					continue

				moves |= group_moves

				for group_move in group_moves:
					product_qty = group_move.product_uom._compute_quantity(
							operation.product_uom_qty, group_move.product_id.uom_id, rounding_method='HALF-UP')
					available_quantity = StockQuant._get_available_quantity(
						group_move.product_id,
						group_move.location_id,
						lot_id=operation.lot_id,
						strict=False,
					)
					group_move._update_reserved_quantity(
						product_qty,
						available_quantity,
						group_move.location_id,
						lot_id=operation.lot_id,
						strict=False,
					)
					# Then, set the quantity done. If the required quantity was not reserved, negative
					# quant is created in operation.location_id.
					group_move._set_quantity_done(operation.product_uom_qty)

					if operation.lot_id:
						group_move.move_line_ids.lot_id = operation.lot_id
				
			if moves:
				moves._action_done()
				
				moves_not_done_message = [_('Repair cannot be ended - transfer move [{0}] for product {1}.').format(m.name or '',
																													m.product_id and m.product_id.name_get()[0][1] or '')\
										  for m in moves.filtered(lambda x: x.state not in ['done'])]
				if moves_not_done_message:
					raise UserError("\n".join(moves_not_done_message))

		self.mapped('operations').write({'state': 'done'})
		
		return res
	
class RepairLine(models.Model):
	_inherit = 'repair.line'

	sequence = fields.Integer('Sequence', help="Gives the sequence of this line when displaying the repair estimate.", default=10)
	to_invoice = fields.Boolean('To Invoice', default=True)
	type = fields.Selection(default='add')
	
	@api.onchange('repair_id', 'product_id', 'product_uom_qty')
	def onchange_product_id(self):
		result = super(RepairLine, self).onchange_product_id()
		
		company_partner_fpos = self.env['account.fiscal.position'].get_fiscal_position(self.env.user.company_id.partner_id.id)
		
		taxes = self.product_id and (self.product_id.taxes_id.filtered(lambda x: x.company_id == self.repair_id.company_id) or self.product_id.product_tmpl_id.get_product_accounts()['stock_input']) or False
		
		if taxes and company_partner_fpos:
			self.tax_id = company_partner_fpos.map_tax(taxes)
		elif taxes:
			self.tax_id = taxes
		else:
			self.tax_id = False
			
		return result
	
	@api.onchange('type', 'repair_id')
	def onchange_operation_type(self):
		result = super(RepairLine, self).onchange_operation_type()
		
		if self.repair_id and self.repair_id.management_id and self.type:
			self.repair_id.onchange_management()
			
		self.repair_id.onchange_guarantee_limit()
		return result
	
	def _action_launch_stock_rule(self, previous_product_uom_qty=False):
		"""
		Launch procurement group run method with required/custom fields genrated by a
		sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
		depending on the sale order line product rule.
		"""
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		ProcurementGroup = self.env['procurement.group']
		procurements = []
		line_procurement_map = {}#94616
		for line in self:
			if not line.product_id or line.product_id.type not in ('product', 'consu'):
				continue
			
			qty = line._get_qty_procurement(previous_product_uom_qty)
			if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
				continue
			
			group_id = line._get_procurement_group()
			if not group_id: 
				group_id = ProcurementGroup.create(line._prepare_procurement_group_vals()) 
			else:
				updated_vals = {}
				if group_id.partner_id != line.repair_id.partner_id:
					updated_vals.update({'partner_id': line.repair_id.partner_id.id})
				if updated_vals:
					group_id.write(updated_vals)
					
			values = line._prepare_procurement_values(group_id=group_id)
			product_qty = line.product_uom_qty - qty
			line_uom = line.product_uom
			quant_uom = line.product_id.uom_id
			product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
			procure_group = ProcurementGroup.Procurement(
				line.product_id, product_qty, procurement_uom,
				line.location_dest_id,
				line.name, line.repair_id.name, line.repair_id.company_id, values)
			procurements.append(procure_group)
			
			line_procurement_map[line] = procure_group and procure_group.values and procure_group.values.get('group_id') or False
			
		if procurements:
			ProcurementGroup.run(procurements)
		
		for line, proc_group in line_procurement_map.items():
			if proc_group and proc_group.stock_move_ids:
				line.write({'move_id': proc_group.stock_move_ids[-1].id})
		
		return True
	
	def _get_qty_procurement(self, previous_product_uom_qty=False):
		self.ensure_one()
		qty = 0.0
		outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
		for move in outgoing_moves:
			qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
		for move in incoming_moves:
			qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
		return qty		
	   
	def _get_outgoing_incoming_moves(self):
		outgoing_moves = self.env['stock.move']
		incoming_moves = self.env['stock.move']

		moves = self.move_id.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id)
		if self._context.get('accrual_entry_date'):
			moves = moves.filtered(lambda r: fields.Date.to_date(r.date) <= self._context['accrual_entry_date'])

		for move in moves:
			if move.location_dest_id.usage == "customer":
				if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
					outgoing_moves |= move
			elif move.location_dest_id.usage != "customer" and move.to_refund:
				incoming_moves |= move

		return outgoing_moves, incoming_moves
	
	def _get_procurement_group(self):
		self.ensure_one()		
		return self.move_id and self.move_id.group_id or False
	
	def _prepare_procurement_group_vals(self):
		return {'partner_id': self.repair_id.partner_id and self.repair_id.partner_id.id or False, }
	
	def _prepare_procurement_values(self, group_id=False):
		self.ensure_one()
		
		return {
			'group_id': group_id,
			'name': self.name,
			'product_id': self.product_id.id,
			'date': fields.Datetime.now() + relativedelta(days=self.product_id.sale_delay or 0),
			'repair_id': self.repair_id.id,
			'origin': self.repair_id.name,
		}	
			
class RepairFee(models.Model):
	_inherit = 'repair.fee'

	to_invoice = fields.Boolean('To Invoice', default=True)	
	