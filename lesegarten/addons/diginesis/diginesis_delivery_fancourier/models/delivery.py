# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import requests
import math
import unicodedata
from io import StringIO
import csv
import base64
import hashlib
import xml.etree.ElementTree as ET		
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class DiginesisDeliveryFancourierStatus(models.Model):	
	_name="diginesis.delivery.fancourier.status"
	
	code = fields.Char(string='Code', required=True)
	name = fields.Char(string='Name', required=True)	
	
class DiginesisDeliveryFancourier(models.Model):
	_name = "diginesis.delivery.fancourier"
	_description = "Integration with FanCourier delivery system"	
	_inherit = ['mail.thread']
	
	
	def _get_data(self, parent, parent_type):			
		if not (parent and parent_type in ['stock_picking']):
			raise UserError(_("Invalid delivery parent. It should be a picking!"))
				
		carrier_ref = self.env.ref('diginesis_delivery_fancourier.delivery_carrier_fancourier')		
		if not carrier_ref:
			raise UserError(_('FanCourier Delivery Carrier does not exist!'))
		
		carrier_id = carrier_ref.id
		
		if not parent.mapped('picking_type_id.warehouse_id.fancourier_api_endpoint'):
			raise UserError(_('FanCourier Api Credentials not set on warehouse!'))
		
		partner = parent.partner_id
		zip = self.env['diginesis.delivery.carrier.rule'].get_value({'partner_id': partner.id}, 'zip', [('carrier_id', '=', carrier_id)])
		
		res = {
				'name': "%s Delivery FanCourier" % parent.name or '',
				'carrier_id':  carrier_id,
				'partner_id': partner and partner.id or False,
				'stock_picking_id': parent.id or False,
				'gross_weight': 0,
				'product_pack_count': 0,
				'product_envelope_count': 0,
				'type': 'standard',
				'currency_id': (parent.mapped('sale_id.currency_id').ids + [False])[0],
				'country_id': (partner.mapped('.country_id').ids + [False])[0],
				'state_name': (partner.mapped('state_id.name') + [''])[0],
				'city': partner.city or '',
				'street': "%s %s" % (partner.street or '', partner.street2 or ''),
				'zip': zip or partner.zip or '',
				'partner_name': (partner.mapped('commercial_partner_id.name') + [''])[0],
				'partner_contact': partner and partner.name or '',
				'phone': "%s  %s" % (partner.phone or '', partner.mobile or ''),
				'email': partner.email or '',				
				'recipient_identification_number': '',
				'recipient_identification_number': '',
				'recipient_identification_serial': '' ,
				'recipient_identification_serial': '' ,
				'sale_order': (parent.mapped('sale_id.name') + [''])[0],
				'salesperson': (parent.mapped('sale_id.user_id.name') + [''])[0],
				'messages': '',
				'packing_lines': [],
				'api_endpoint': (parent.mapped('picking_type_id.warehouse_id.fancourier_api_endpoint').ids + [False])[0],
				'user_id': self.env.uid,
		}
		
		if parent.partner_id and parent.partner_id.country_id and parent.company_id.country_id and parent.partner_id.country_id.id != parent.company_id.country_id.id:
			res['type'] =  'export'
				
		res['gross_weight'] = sum([x.product_id.weight * x.product_uom._compute_quantity(x.product_qty, x.product_id.uom_id) 
										for x in parent.mapped('move_lines').filtered(lambda x: x.product_id)])
				
		res['packing_lines'] = [self._prepare_packing_line(None, x, 'move_line') for x in parent.mapped('move_lines')]		
		return res		
	
	
	def _prepare_packing_line(self, delivery_fancourier_id, line, line_type):		
		if line and line_type in ['delivery_note_line', 'move_line']:
			return {
				'product_id': line.product_id and line.product_id.id or False,
				'delivery_fancourier_id': delivery_fancourier_id,
				'name': line.name or '',
				'default_code': line.product_id and line.product_id.default_code or '',
				'quantity': line.product_uom_qty or 0,
				'price_subtotal': (line.mapped('sale_line_id.price_unit') + [0])[0],
			}			
		else:
			return {
				'product_id': False,
				'delivery_fancourier_id': delivery_fancourier_id,
				'name': '',
				'default_code': '',
				'quantity': 0,
				'price_subtotal': 0
			}
	
	@api.depends('partner_name', 'partner_contact')
	def _get_partner_full_name(self):
		self.partner_full_name = u"{0} {1}".format(self.partner_name or '', self.partner_name != self.partner_contact and self.partner_contact or '')		
		
	def _get_fancourier_intermediate_status_list(self):	
		return filter(lambda x: x[0] in ['12', '30'], self._get_fancourier_status_list())
		
	def _get_fancourier_status_list(self):	
		return [
			('0','AWB-ul nu a fost predat catre FAN Courier.'),
			('1','Expeditie in livrare'),
			('2','Livrat'),
			('3','Avizat'),
			('4','Adresa incompleta'),
			('5','Adresa gresita, destinatar mutat'),
			('6','Refuz primire'),
			('7','Refuz plata transport'),
			('8','Livrare din sediul FAN Courier'),
			('9','Redirectionat'),
			('10','Adresa gresita, fara telefon'),
			('11','Avizat si trimis SMS'),
			('12','Contactat, livrare ulterioara'),
			('14', 'Restrictii acces la adresa'),
			('15','Refuz predare ramburs'),
			('16','Retur la termen'),
			('19','Adresa incompleta - trimis SMS'),
			('20','Adresa incompleta, fara telefon'),
			('21','Avizat, lipsa persoana de contact'),
			('22','Avizat, nu are bani de rbs'),
			('24','Avizat, nu are imputernicire/CI'),
			('25','Adresa gresita - trimis SMS'),
			('27','Adresa gresita, nr telefon gresit'),
			('28','Adresa incompleta,nr telefon gresit'),
			('30','Nu raspunde la telefon'),
			('33','Retur solicitat'),
			('34','Afisare'),
			('35','Retrimis in livrare'),
			('38','AWB neexpediat'),
			('42','Adresa gresita'),
			('43','Retur'),]	
	
	name = fields.Char(string="Name", size=255, readonly=True)
	awb = fields.Char(string="AWB", size=255, readonly=True)
	date = fields.Datetime('Date', readonly=True)
	stock_picking_id = fields.Many2one('stock.picking', 'Stock Picking', required=True,)
	partner_id = fields.Many2one('res.partner', 'Recipient', change_default=True, readonly=True, required=True, states={'draft':[('readonly',False)]})
	commercial_partner_id = fields.Many2one('res.partner', related='partner_id.commercial_partner_id',string='Commercial Partner')
	partner_name = fields.Char('Recipient Name', size=40, required=True)
	partner_contact = fields.Char('Recipient Contact', size=30)
	partner_full_name = fields.Char(string='Recipient', compute="_get_partner_full_name")
	state_name = fields.Char('State', size=50)
	country_id = fields.Many2one('res.country', 'Country')
	city = fields.Char('City', size=40, required=True)
	street = fields.Char('Street', size=250, required=True)
	zip = fields.Char('Zip', size=6, required=True)
	phone = fields.Char('Phone', size=25, required=True)
	email = fields.Char('Email', size=100)

	cost_center = fields.Char(string="Cost Center", size=40)
	sender_contact = fields.Char(string="Sender Contact", size=30)

	option_a = fields.Boolean('Open on Delivery')
	option_b = fields.Boolean('oPOD')
	option_x = fields.Boolean('ePOD')

	sending_mode = fields.Selection([('by_car','Car'), ('by_plane','Plane'),], 'Sending Mode', index=True)
	type = fields.Selection([
		('fancourier_service','Servicii FAN Courier'),
		('standard','Standard'),
		('redcode','RedCode'),
		('task_notebook','Caiet Sarcini'),
		('expressloco_1h','ExpressLoco 1H'),
		('expressloco_2h','ExpressLoco 2H'),
		('expressloco_4h','ExpressLoco 4H'),
		('expressloco_6h','ExpressLoco 6H'),
		('colector_accountnt','Cont Colector'),
		('expressloco_1h_collector_account','ExpressLoco 1H-Cont Colector'),
		('expressloco_2h_collector_account','ExpressLoco 2H-Cont Colector'),
		('expressloco_4h_collector_account','ExpressLoco 4H-Cont Colector'),
		('expressloco_6h_collector_account','ExpressLoco 6H-Cont Colector'),
		('redcode_collector_account','Red code-Cont Colector'),
		('export','Export'),
		],'Type', index=True, required=True)

	gross_weight = fields.Integer('Pack Brut Weight (kg)', required=True)
	product_pack_count = fields.Integer('Packs Number', required=True)
	product_envelope_count = fields.Integer('Envelopes Number', required=True)
	content_type = fields.Selection([('document','Document'),
									('non_document','Non Document'),],'Sending Type', index=True)

	height = fields.Float('Height (cm)', help='The height of the package')
	width = fields.Float('Width (cm)', help='The width of the package')
	length = fields.Float('Length (cm)', help='The length of the package')

	urgent_delivery = fields.Boolean(string='Urgent delivery', default=False)
	delivery_day = fields.Selection([('saturday', 'Deliver on saturday'), ('monday', 'Deliver on monday'),], string='Delivery day', default=False)
	delivery_hour = fields.Selection([('after_four', 'Deliver after 16:00'),('nine_to_five', 'Deliver 09:00 -17:00'),], string='Delivery hour', default=False)
	delivery_with_phonecall = fields.Boolean(string='Delivery with phonecall', default=False)
	delivery_fragile = fields.Boolean(string='Fragile delivery', default=False)
	delivery_personal = fields.Boolean(string='Personal delivery', default=False)
	delivery_with_stamp = fields.Boolean(string='Delivery with stamp', default=False)
	fancurier_delivery = fields.Boolean(string='Deliver from FanCurier Quarters', default=False)
	
	date_to_client = fields.Datetime('Date to Client', readonly=True)		
	load_to_client = fields.Integer('Load to client', readonly=True, default=0)
	delivery_time_days = fields.Integer(string='Delivery Time (days)', readonly=True)

	declared_contents = fields.Char('Declared Contents', size=36)
	notes_external = fields.Text('Notes', size=200)

	payment_location = fields.Selection([('sender','Sender'),
										('recipient','Recipient'),
										('other','Other'),
							],'Payment Location', index=True)
	recipient_payment = fields.Char('Recipient Payment', size=255)

	cash_on_delivery = fields.Float('Cash on Delivery', digits='Account')
	currency_id = fields.Many2one('res.currency', 'Currency')

	refund = fields.Char('Refund', size=50)

	cash_on_delivery_payment_type = fields.Selection([('sender','Sender'),	('recipient','Recipient'),], 'Cash on Delivery Payment Type', index=True)

	declared_value = fields.Float('Declared Value')

	recipient_identification_number = fields.Char('Recipient ID Number', size=10)
	recipient_identification_serial = fields.Char('Recipient ID Serial', size=2)
	packing_lines = fields.One2many('diginesis.delivery.fancourier.line', 'delivery_fancourier_id', 'Packing Lines')

	sale_order = fields.Char('Sale Order', size=255)
	salesperson = fields.Char('Salesperson', size=255)

	carrier_id = fields.Many2one('diginesis.delivery.carrier', 'Carrier', required=True)
	state = fields.Selection([
		('draft','Draft'),
		('pending','Pending'),
		('confirmed','Confirmed'),
		('cancel','Cancelled'),
		('delivered','Delivered'),
		],'State', index=True, readonly=True, default='draft')
		
	status_fancourier = fields.Selection(_get_fancourier_status_list,'FanCourier Status', index=True, readonly=True)
	no_compensation = fields.Boolean('No compensation', readonly=True, default=False)

	messages = fields.Text('Messages', readonly=True)
	api_endpoint = fields.Many2one('diginesis.api.endpoint', 'Endpoint Credentials')
	
	user_id = fields.Many2one('res.users', 'User', help="This is the user who created and/or confirmed this delivery.")	
	tariff = fields.Float("Tariff", digits='Account', help="Tariff given by FanCourier for current AWB.")
	payment_id = fields.Many2one('account.payment', string="Payment", readonly=True)
		
	def make_delivery(self, values):				
		parent = values.get('parent') or False
		parent_type = values.get('parent_type') or False
		if not parent or not parent_type:
			return False
		
		if not parent_type in ['stock_picking']:	
			return False
		
		vals = self._get_data(parent, parent_type)
		vals['packing_lines'] = [[0, False, x] for x in (vals.get('packing_lines') or [])]
		
		res = self.create(vals)
		delivery_ids = res._get_parent_delivery()
		
		return (delivery_ids + [False])[0]
		
	
	def create(self, vals):		
		res = super(DiginesisDeliveryFancourier, self).create(vals)
		if res:
			self.env['diginesis.delivery'].create({'res_id': res, 
													'res_model': 'diginesis.delivery.fancourier',
													'stock_picking_id': vals['stock_picking_id']})		
		return res
	
	
	def unlink(self):		
		res = super(DiginesisDeliveryFancourier, self).unlink()
		delivery_ids = self._get_parent_delivery()
		if delivery_ids:
			self.env['diginesis.delivery'].browse(delivery_ids).unlink()
		return res
		
	
	def action_cancel(self):
		self.write({'state': 'cancel'})
		
	
	def action_cancel_draft(self):
		self.write({'state': 'draft', 'awb': None, 'date': None})
		
	
	def action_confirmed_cancel(self):
		IrAttachment = self.env['ir.attachment']
		
		api_credetials, url = self._get_api_endpoint('delete_awb')
		data = {'username': api_credetials.username, 'client_id': api_credetials.clientid, 'user_pass': api_credetials.password}
		
		awb_filenames = self._get_awb_filename()
		for delivery in self.filtered(lambda x: x.awb):
			data['AWB'] = delivery.awb
			
			r = False
			try:
				r = requests.post(url, data=data)
			except Exception:
				pass 
			
			if not r or r.status_code != requests.codes.ok:
				raise UserError(_('Invalid Request!'))
				
			if self._isErrorResponse(r.text):
				raise UserError(_('Delivery cannot be Cancelled!'))
				
			if r.text.find("AWB can not be deleted") != -1:
				raise UserError(_('Delivery cannot be Cancelled! FanCourier does not allow it!'))
		
			filename = awb_filenames.get(delivery.id)				
			attach_ids = IrAttachment.search([('res_model', '=', 'diginesis.delivery.fancourier'),
											('res_id', '=', delivery.id),('name', '=', filename)])					
			if delivery.stock_picking_id:
				attach_ids += IrAttachment.search([('res_model', '=', 'stock.picking'),
													('res_id', '=', delivery.stock_picking_id.id),('name', '=', filename)])
				
			attach_ids.unlink()
			delivery.write({'state': 'cancel'})
	
	def action_confirm(self):				
		self._get_awb()	
		self.action_attach_awb()		
	
	def action_attach_awb(self):		
		self._attach_awb()
		self._get_tariff()
	
	def action_send_email(self):
		template_ref = self.env.ref('diginesis_delivery_fancourier.email_template_delivery_fancourier_delivery_sent_alert')
		template_id = template_ref and template_ref.id or False
		compose_form_ref = self.env.ref('mail.email_compose_message_wizard_form')
		compose_form_id = compose_form_ref and compose_form_ref.id or False
		
		if not (template_id and compose_form_id):
			raise UserError(_('Invalid email template!')) 
			
		partner_ids = self.mapped('stock_picking_id.partner_id').filtered(lambda x: x.email).ids		
		if not partner_ids:
			raise UserError(_('Invalid Recipients')) 
		
		context = (self.env.context or {}).copy()
		context.update({
			'default_model': 'diginesis.delivery.fancourier',
			'default_res_id': (self.ids + [False])[0],
			'default_partner_ids': partner_ids,
			'default_use_template': bool(template_id),
			'default_template_id': template_id,
			'default_composition_mode': 'comment',
		})
		return {
			'type': 'ir.actions.act_window',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',
			'context': context,
		}
	
	def close_delivery_day(self, vals):		
		res = {'warning': False, 'state': 'open', 'awbs': ''}
		return res
	
	def _get_awb_filename(self):
		filename_template = '{0}.pdf'
		return dict((delivery.id, filename_template.format(delivery.awb.strip(' '))) for delivery in self)	
	
	def _generate_file_contents(self):
		def _encode_item_notes(delivery):
			item = ''
			count = 0
			if delivery.urgent_delivery:
				item += self._encode_item(_(delivery._fields['urgent_delivery'].string))
				count += 1
			if delivery.delivery_day:
				if count:
					item += ';'
				item += self._encode_item(_(dict(self._fields['delivery_day'].selection).get(delivery.delivery_day, False)))
				count += 1
			if delivery.delivery_hour:
				if count:
					item += ';'
				item += self._encode_item(_(dict(self._fields['delivery_hour'].selection).get(delivery.delivery_hour, False)))
				count += 1
			if delivery.delivery_with_phonecall:
				if count:
					item += ';'
				item += self._encode_item(_(delivery._fields['delivery_with_phonecall'].string))
				count += 1
			if delivery.delivery_fragile:
				if count:
					item += ';'
				item += self._encode_item(_(delivery._fields['delivery_fragile'].string))
				count += 1
			if delivery.delivery_personal:
				if count:
					item += ';'
				item += self._encode_item(_(delivery._fields['delivery_personal'].string))
				count += 1
			if delivery.delivery_with_stamp:
				if count:
					item += ';'
				item += self._encode_item(_(delivery._fields['delivery_with_stamp'].string))
				count += 1
			item += ''
			return item

		order = {}
		index = 1

		contents = StringIO()
		writer = csv.writer(contents, quoting=csv.QUOTE_MINIMAL)
		
		validation = self._validate_delivery()
		if len(validation['errors']) > 0:
			raise UserError(_(u'Invalid delivery!\n{0}').format("\n".join(validation['errors']))) 		
		
		for delivery in self:	
			has_header = False
			if delivery.type in ['export']:
				if not has_header:
					writer.writerow([name.encode('utf-8') for name in ['Tip serviciu', 'Mod trimitere', 'Nr. Colete','Nr. Plicuri','Greutate','Tip continut', 'Persoana contact expeditor','Observatii','Nume destinatar',
							'Tara de destinatatie', 'Telefon','Fax','Email','Localitatea','Strada','Nr','Cod postal','Bloc','Scara','Etaj','Apartament',
							'Lungime pachet','Latime pachet','Inaltime pachet']	])
					has_header = True					
					
				row = {'type': self._encode_item(dict(self._fields['type'].selection).get(delivery.type, False)),						
						'sending_mode': (delivery.sending_mode == 'by_car' and 'rutier') or (delivery.sending_mode == 'by_plane' and 'aerian') or '',
						'product_envelope_count': delivery.product_envelope_count and str(delivery.product_envelope_count) or '',
						'product_pack_count': delivery.product_pack_count and str(delivery.product_pack_count) or '', 
						'gross_weight': delivery.gross_weight and str(delivery.gross_weight) or '', 
						'content_type': (delivery.content_type == 'document' and 'document') or (delivery.sending_mode == 'non_document' and 'non document') or '',
						'sender_contact': self._encode_item(delivery.sender_contact) or '', 
						'notes': _encode_item_notes(delivery),
						'partner_name': self._encode_item(delivery.partner_name) or '', 
						'phone': self._encode_item(delivery.phone) or '', 
						'fax': '', 
						'email': self._encode_item(delivery.email) or '',
						'country': delivery.country_id and self._encode_item(delivery.country_id.name) or '', 
						'city': self._encode_item(delivery.city) or '', 
						'street': self._encode_item(delivery.street) or '', 
						'number': '', 
						'zip': self._encode_item(delivery.zip) or '', 
						'address1': '',
						'address2': '',
						'address3': '',
						'address4': '',
						'height': delivery.height and str(delivery.height) or '', 
						'width': delivery.width and str(delivery.width) or '', 
						'length': delivery.length and str(delivery.length) or '',
				}
								
				order.update({str(index): delivery})
				writer.writerow([row['type'],row['sending_mode'],row['product_pack_count'],row['product_envelope_count'],row['gross_weight'],row['content_type'],
						row['sender_contact'],row['notes'],
						row['partner_name'],row['country'],row['phone'],row['fax'],row['email'],row['city'],row['street'],row['number'],row['zip'],row['address1'],row['address2'],row['address3'],row['address4'],
						row['length'],row['width'],row['height']])
				index = index + 1			
				
			else:
				if not has_header:
					writer.writerow([name.encode('utf-8') for name in ['Tip serviciu','Banca','IBAN','Nr. Plicuri','Nr. Colete','Greutate','Plata expeditie','Ramburs(bani)','Plata ramburs la',
							'Valoare declarata','Persoana contact expeditor','Observatii','Continut','Nume destinatar','Persoana contact',
							'Telefon','Fax','Email','Judet','Localitatea','Strada','Nr','Cod postal','Bloc','Scara','Etaj','Apartament','Inaltime pachet','Latime pachet','Lungime pachet',
							'Restituire','Centru Cost','Optiuni','Packing','Date personale']])
					has_header = True				
				
				row = {'type': self._encode_item(dict(self._fields['type'].selection).get(delivery.type, False)),
						'bank': '',
						'iban': '',
						'product_envelope_count': delivery.product_envelope_count and str(delivery.product_envelope_count) or '',
						'product_pack_count': delivery.product_pack_count and str(delivery.product_pack_count) or '', 
						'gross_weight': delivery.gross_weight and str(delivery.gross_weight) or '', 
						'payment_location': '', 
						'cash_on_delivery': delivery.cash_on_delivery and str(delivery.cash_on_delivery) or '', 
						'cash_on_delivery_payment_type': '', 
						'declared_value': delivery.declared_value and str(delivery.declared_value) or '', 
						'sender_contact': self._encode_item(delivery.sender_contact) or '', 
						'notes': _encode_item_notes(delivery),
						'declared_contents':  self._encode_item(delivery.declared_contents) or '', 
						'partner_name': self._encode_item(delivery.partner_name) or '', 
						'partner_contact': self._encode_item(delivery.partner_contact) or '', 
						'phone': self._encode_item(delivery.phone) or '', 
						'fax': '', 
						'email': self._encode_item(delivery.email) or '', 
						'state_name': self._encode_item(delivery.state_name) or '', 
						'city': self._encode_item(delivery.city) or '', 
						'street': self._encode_item(delivery.street) or '', 
						'number': '', 
						'zip': self._encode_item(delivery.zip) or '', 
						'address1': '',
						'address2': '',
						'address3': '',
						'address4': '',
						'height': delivery.height and str(delivery.height) or '', 
						'width': delivery.width and str(delivery.width) or '', 
						'length': delivery.length and str(delivery.length) or '', 
						'refund': self._encode_item(delivery.refund) or '',  
						'cost_center': self._encode_item(delivery.cost_center) or '',  
						'options': '',
						'packing': '',
						'recipient_info': ''
				}
				
				if delivery.payment_location:
					d = ((delivery.payment_location == 'sender') and 'expeditor') or ((delivery.payment_location == 'recipient') and 'destinatar') or ((delivery.payment_location == 'other') and delivery.recipient_payment or '') or ''							
					row['payment_location'] = self._encode_item(d)
					
				if delivery.cash_on_delivery_payment_type:				
					d = ((delivery.cash_on_delivery_payment_type == 'sender') and 'expeditor') or ((delivery.cash_on_delivery_payment_type == 'recipient') and 'destinatar') or ''
					row['cash_on_delivery_payment_type'] = self._encode_item(d)
			
				if delivery.option_a:				
					if len(delivery.packing_lines) > 0:
						lines = []
						for line in delivery.packing_lines:
							product_line = '/'.join([line.product_id and line.product_id.name and line.product_id.name.replace('/','').replace('|','') or '', line.name and line.name.replace('/','').replace('|','') or '', line.default_code and line.default_code.replace('/','').replace('|','') or '', str(line.quantity) or '', str(line.price_subtotal) or ''])
							lines.append(self._encode_item(product_line))
						row['packing'] = '|'.join(lines).encode("utf-8")

					row['recipient_info'] = u"{0}|{1}".format(delivery.recipient_identification_serial or '', delivery.recipient_identification_number or '')					

				options = []
				if delivery.option_a:
					options.append('Deschidere la livrare')
				if delivery.option_b:
					options.append('oPOD')
				if delivery.fancurier_delivery:
					options.append('Livrare sediu FAN')
				if delivery.option_x:
					options.append('ePOD')
				row['options'] = u'/'.join(options).encode("utf-8")

				order.update({str(index): delivery})
				writer.writerow([row['type'],row['bank'],row['iban'],row['product_envelope_count'],row['product_pack_count'],row['gross_weight'],row['payment_location'],
					row['cash_on_delivery'],row['cash_on_delivery_payment_type'],row['declared_value'],row['sender_contact'],row['notes'],row['declared_contents'],
					row['partner_name'],row['partner_contact'],row['phone'],row['fax'],row['email'],row['state_name'],row['city'],row['street'],row['number'],row['zip'],row['address1'],row['address2'],row['address3'],row['address4'],
					row['height'],row['width'],row['length'],row['refund'],row['cost_center'],row['options'],row['packing'],row['recipient_info'],])
				index = index + 1
				
		contents.seek(0)
		data = contents.read()
		contents.close()
		
		return data, order
		
	def _generate_tracking_file_contents(self):		
		domain = [('state', 'in', ['confirmed']), ('date_to_client', '=', False)]
		if self.env.context.get('api_endpoint') or False:
			domain.append(('api_endpoint', '=', self.env.context['api_endpoint']))
			
		awbs = self.search(domain)
		return u"""<?xml version="1.0" ?><AWBLIST>{0}</AWBLIST>""".format(u''.join(["<AWB><ID>{0}</ID><NRAWB>{1}</NRAWB></AWB>".format(x.id, x.awb) for x in awbs])), dict((x.awb, x) for x in awbs)
		
	def _get_tracking_api_endpoints(self):		
		awbs = self.search([('state', 'in', ['confirmed']), ('date_to_client', '=', False)])
		api_endpoints = set([x.api_endpoint for x in awbs if x.api_endpoint])
			
		res = []
		for api_credentials in api_endpoints:			
			if not (api_credentials and api_credentials.endpoint):
				continue	 			
			if not api_credentials.endpoint_lines or len(api_credentials.endpoint_lines) <= 0:
				continue	 		
			endpoint = [x.endpoint for x in api_credentials.endpoint_lines if x.name == 'get_tracking_status']
			if len(endpoint) <= 0:
				continue
			
			res.append((api_credentials, endpoint[0]))
		
		return res
		
	def _get_awb(self):
		file_contents, order = self._generate_file_contents()
		if not file_contents:
			raise UserError(_('Cannot generate Delivery Request!'))		
		
		api_credetials, url = self._get_api_endpoint('get_awb')
		
		file_contents = StringIO(file_contents)
		files = {'fisier': ('awb.csv', file_contents, 'text/csv;charset=utf-8', {'Expires': '0'})}
		data = {'username': api_credetials.username, 'client_id': api_credetials.clientid, 'user_pass': api_credetials.password}
		
		r = False
		try:
			r = requests.post(url, data=data, files=files)
		except:
			pass
		
		if not r or r.status_code != requests.codes.ok:
			raise UserError(_('Invalid Request!'))
			
		if not self._isErrorResponse(r.text):
			awbs = []			
			response_rows = r.text.split(u"\n")
			if len(response_rows) > 0:
				index = 1
				for row in response_rows:
					items = row.split(',')
					if len(items) > 1:
						status = items[1]
						if not status or status in ['0']:		
							message = [items[2]]
							#view_awb_integrat_pdf.php
							r1 = False
							try:
								r1 = requests.post("https://www.selfawb.ro/export_lista_erori_imp_awb_integrat.php", data=data)
							except:
								pass
										
							if r1 and r1.text:
								message.append(r1.text)
									
							raise UserError(_(u'Cannot generate AWB for Delivery!\n{0}').format(u"\n".join(message)))
						
						index_str = str(index)
						if index_str in order and order[index_str]:
							order[index_str].write({'awb': items[2], 'state': 'pending', 'user_id': self.env.uid})
					index = index + 1
		
	def _attach_awb(self):
		IrAttachment = self.env['ir.attachment']
				
		api_credetials, url = self._get_api_endpoint('get_print')
		data = {'username': api_credetials.username, 'client_id': api_credetials.clientid, 'user_pass': api_credetials.password, 'page': api_credetials.page_setup or 'A4'}
		if data.get('page') == 'A6':
			data.update({'type': 1})
		
		awb_filenames = self._get_awb_filename()		
		for delivery in self:
			messages = []
						
			if not delivery.awb:
				messages.append(_(u'Invalid AWB number for delivery {0}').format(delivery.name))
			else:			
				data['nr'] = delivery.awb
				r = False
				try:
					r = requests.post(url, data=data)
				except:
					pass
				
				if not r or r.status_code != requests.codes.ok:
					messages.append(_('Invalid Request! AWB pdf cannot be attached!'))
					
				if r.content:
					attach = StringIO(r.content)
					attach.seek(0)
					content = attach.read()			
					attach.close()
					
					filename = awb_filenames.get(delivery.id)
					attachment_id = IrAttachment.create({"res_model": self._name, "res_id": delivery.id, "name": filename, 
														"datas": base64.encodestring(content), "datas_fname" : filename})
					attachment_id.copy({'name': filename, 'datas_fname': filename, 'res_model': 'stock.picking', 'res_id': delivery.stock_picking_id.id})
						
					delivery.write({'state': 'confirmed', 'date': datetime.now(), 'user_id': self.env.uid})		
				else:
					messages.append(_('Invalid Response! AWB pdf cannot be attached!'))
					
			if len(messages) > 0:
				delivery.write({'messages': u"\n".join(messages)})	
	
	def _get_tariff(self):
		api_credetials, url = self._get_api_endpoint('get_tariff')
		
		for delivery in self:
			data = {'username': api_credetials.username, 
					'client_id': api_credetials.clientid, 
					'user_pass': api_credetials.password,
					'serviciu': self._encode_item(dict(self._fields['type'].selection).get(delivery.type, False)) 					
					}
			
			if delivery.type in ['export']:				
				data.update({'modtrim':(delivery.sending_mode == 'by_car' and 'rutier') or (delivery.sending_mode == 'by_plane' and 'aerian') or '',
					'greutate': delivery.gross_weight or 0, 
					'pliccolet': (delivery.product_envelope_count or 0) + (delivery.product_pack_count or 0), 
					's_inaltime': delivery.height or 0.0, 
					's_latime': delivery.width or 0.0, 
					's_lungime': delivery.length or 0.0,
					'volum': 0.0, 
					'dest_tara': delivery.country_id and self._encode_item(delivery.country_id.name) or '', 
					'tipcontinut': (delivery.content_type == 'document' and 'document') or (delivery.sending_mode == 'non_document' and 'non document') or '', 
					'kmext': 0.0, })
			else:
				data.update({'plata_la': self._encode_item(delivery.payment_location and (((delivery.payment_location == 'sender') and 'expeditor') or ((delivery.payment_location == 'recipient') and 'destinatar') or ((delivery.payment_location == 'other') and delivery.recipient_payment or '') or '') or ''),
					'localitate_dest': self._encode_item(delivery.city) or '', 
					'judet_dest': self._encode_item(delivery.state_name) or '', 
					'plicuri': delivery.product_envelope_count or 0, 
					'colete': delivery.product_pack_count or 0, 
					'greutate': delivery.gross_weight or 0, 
					'lungime': delivery.length or 0.0, 
					'latime': delivery.width or 0.0, 
					'inaltime': delivery.height or 0.0, 
					'val_decl': delivery.declared_value or 0.0, 
					'plata_ramburs': self._encode_item(delivery.cash_on_delivery_payment_type and (((delivery.payment_location == 'sender') and 'expeditor') or ((delivery.payment_location == 'recipient') and 'destinatar') or ((delivery.payment_location == 'other') and delivery.recipient_payment or '') or '') or ''),
					})
			r = False
			try:	
				r = requests.post(url, data=data)
			except:
				pass
			
			tariff = 0.0
			if not r or r.status_code != requests.codes.ok or self._isErrorResponse(r.text):
				_logger.info(_(u'Invalid Request! Tariff cannot be retrieved! {0}').format(r.text))
			else: 
				tariff = r.content
				
			delivery.write({'tariff': tariff})	
	
	def get_slip(self, api_credentials, slip_date):
				
		if not (api_credentials and api_credentials.endpoint):
			raise UserError(_('Invalid FanCourier Endpoint Credentials!'))
		if not api_credentials.endpoint_lines or len(api_credentials.endpoint_lines) <= 0:
			raise UserError(_('Invalid FanCourier Endpoints!'))
		
		endpoint = [x.endpoint for x in api_credentials.endpoint_lines if x.name == 'get_slip']
		if len(endpoint) <= 0:
			raise UserError(_(u'Invalid FanCourier <<{0}>> Endpoint!').format('get_slip'))
		
		url = "{0}{1}".format(api_credentials.endpoint, endpoint[0])
		data = {'username': api_credentials.username, 'client_id': api_credentials.clientid, 'user_pass': api_credentials.password, 'data': slip_date.strftime("%d.%m.%Y")}
		
		r = False
		try:
			r = requests.post(url, data=data)
		except:
			pass
		
		if not r or r.status_code != requests.codes.ok:
			raise UserError(_('Invalid Request!'))
		
		awb_number_index = 3
		amount_index = 2
		date_index = 8
			
		res = {}
		if not self._isErrorResponse(r.text):
			#unicode: "Oras destinatar","Data awb","Suma incasata","Numar awb","Expeditor","Destinatar","Continut","PersoanaD","Data virament","PersoanaE","Ramburs la AWB","AWB retur"
			if 'error' not in r.text.lower():
				response_rows = r.text.split(u"\n")
				if len(response_rows) > 1:# 	 				
					for row in response_rows[1::]:
						if len(row) <= 0:
							continue
						
						items = row.split('","') 					
						awb_number = items[awb_number_index].strip('"') if len(items) > awb_number_index else None
						amount = items[amount_index].strip('"') if len(items) > amount_index else None	 	
						date = items[date_index].strip('"') if len(items) > date_index else None				 
						res.update({awb_number: {'amount': amount, 'transfer_date': date}})
		return res 
		
	def get_fancourier_status(self):		
		fancourier_status_keys = dict(self._get_fancourier_status_list()).keys()
		fancourier_intermediate_status_keys = dict(self._get_fancourier_intermediate_status_list()).keys()
		no_compensation_limit_hours = 48
	
		for api_item in self._get_tracking_api_endpoints():
			api_credentials = api_item[0]	
			
			file_contents, awbs = self.with_context(api_endpoint=api_credentials.id)._generate_tracking_file_contents()
			url = "{0}{1}".format(api_credentials.endpoint, api_item[1])		
			files = {'fisier': ('awb.xml', StringIO(file_contents), 'text/xml;charset=utf-8', {'Expires': '0'})}
			data = {'username': api_credentials.username, 'client_id': api_credentials.clientid, 'user_pass': hashlib.md5(api_credentials.password).hexdigest(), 'standard': 1}
			
			r = False
			try:
				r = requests.post(url, data=data, files=files)
			except:
				pass
			
			if not r or r.status_code != requests.codes.ok:
				_logger.info(_('Get Delivered Date: Invalid Request!'))
				continue
		
			if self._isErrorResponse(r.text):
				_logger.info(_(u'Get FanCourier status error {0}').format(r.text))
			else:
				root = ET.fromstring(r.text)
				for child in root.iter('AWB'):
					awb = child.find('NRAWB').text
					delivery_state = child.find('STATUS_LIVRARE').text
					vals = {}
					if delivery_state in ['2']:
						for status in child.find('STATUS_AWB').findall('STATUS'):
							id = status.find('ID').text
							if id in ['4']:
								date = status.find('DATA').text 
								date = date and datetime.strptime(date, '%d.%m.%Y %H:%M')
								if date and awbs.get(awb, False):									
									vals.update({'date_to_client': datetime.strftime(date, DEFAULT_SERVER_DATETIME_FORMAT), 'state': 'delivered', 'load_to_client': 1})
					
					if delivery_state in fancourier_intermediate_status_keys:
						status_startdate = False
						status_enddate = False
						for status in child.find('STATUS_AWB').findall('STATUS'):
							id = status.find('ID').text
							if id in ['4']:
								status_enddate = status.find('DATA').text 
								status_enddate = status_enddate and datetime.strptime(status_enddate, '%d.%m.%Y %H:%M') or False
							if id in ['1']:
								status_startdate = status.find('DATA').text 
								status_startdate = status_startdate and datetime.strptime(status_startdate, '%d.%m.%Y %H:%M') or False								
								
						if status_startdate and status_enddate:
							hours_difference = math.floor(((status_enddate - status_startdate).total_seconds()) / 3600)
							if hours_difference <= no_compensation_limit_hours:
								vals.update({'no_compensation': True})
									
					if delivery_state in fancourier_status_keys:
						vals.update({'status_fancourier': delivery_state})
					elif not delivery_state or 'awb-ul nu a fost predat catre fan courier' in delivery_state.lower():
						vals.update({'status_fancourier': '0'})
					if vals and awbs.get(awb, False):
						awbs[awb].write(vals)
						self.env.cr.execute("UPDATE diginesis_delivery_fancourier SET delivery_time_days = (date_to_client::date - date::date) where id=%s", (awbs[awb].id,))						
			
		return True
	
	
	def _validate_delivery(self):
		res = {'errors': []}
		
		if not self.ids:
			res['errors'].append(_('Invalid Delivery'))
		
		if not self.mapped('gross_weight'):
			res['errors'].append(_('Invalid Pack Brut Weight (kg)')) 
			
		if not (self.mapped('product_envelope_count') or self.mapped('product_pack_count')):
			res['errors'].append(_('Fill in either Packs or Envelopes Count'))
		
		for delivery in self.filtered(lambda x: x.type in ['export']):
			if not delivery.height:
				res['errors'].append(_('Invalid Height'))
			if not delivery.width:
				res['errors'].append(_('Invalid Width'))
			if not delivery.length:
				res['errors'].append(_('Invalid Length'))
								
		return res
	
	
	def _get_api_endpoint(self, name):	
		
		api_credentials = None
		for delivery in self:
			if delivery.api_endpoint:
				api_credentials = delivery.api_endpoint
				break		
				
		if not (api_credentials and api_credentials.endpoint):
			raise UserError(_('Invalid FanCourier Endpoint Credentials!'))
		if not api_credentials.endpoint_lines or len(api_credentials.endpoint_lines) <= 0:
			raise UserError(_('Invalid FanCourier Endpoints!'))
		
		endpoint = [x.endpoint for x in api_credentials.endpoint_lines if x.name == name]
		if len(endpoint) <= 0:
			raise UserError(_('Invalid FanCourier <<{0}>> Endpoint!').format(name))
		
		return api_credentials, "{0}{1}".format(api_credentials.endpoint, endpoint[0])
			
	def _get_parent_delivery(self):		
		if not self.ids:
			return []

		self.env.cr.execute("SELECT array_agg(id) FROM diginesis_delivery WHERE res_id IN %s AND res_model = 'diginesis.delivery.fancourier'", (tuple(self.ids),))
		res = self.env.cr.fetchone()							
		return res and res[0] or []
	
	@api.onchange('stock_picking_id')
	def onchange_stock_picking_id(self):		
		values = {}
		if self.stock_picking_id:			
			values = self._get_data(self.stock_picking_id, 'stock_picking')
		
		return {'value' : values}
		
	def _isErrorResponse(self, response_text):		
		if not response_text:
			return True
		
		clean_response_text = response_text.strip().lower()		
		if clean_response_text.startswith('error') or clean_response_text.startswith('eroare') or clean_response_text.startswith('erori'):
			return True
		
		return False	
	
	def _encode_item(self, item):
		if isinstance(item, basestring):
			item = item.replace('\n',' ').replace('\t',' ')
			try:
				item = ''.join(c for c in unicodedata.normalize('NFD', unicode(item, 'utf8')) if unicodedata.category(c) != 'Mn')
			except UnicodeError:
				pass		
		return None if item is False else item
		
class DiginesisDeliveryFancourierLine(models.Model):
	_name = "diginesis.delivery.fancourier.line"
	_description = "Integration with FanCourier delivery system - Packing item"
	
	product_id = fields.Many2one('product.product', 'Product', )
	delivery_fancourier_id = fields.Many2one('diginesis.delivery.fancourier', 'Delivery', )
	name = fields.Text('Description', )
	default_code = fields.Char('Internal Reference', size=64,)
	quantity = fields.Float('Quantity',)
	price_subtotal = fields.Float('Amount',)
		