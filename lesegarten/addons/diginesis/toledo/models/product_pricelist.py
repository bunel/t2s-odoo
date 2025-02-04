# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr, format_datetime
from itertools import chain

class Pricelist(models.Model):
	_inherit = "product.pricelist"
	
	def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
		""" Low-level method - Mono pricelist, multi products
		Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

		Date in context can be a date, datetime, ...

			:param products_qty_partner: list of typles products, quantity, partner
			:param datetime date: validity date
			:param ID uom_id: intermediate unit of measure
		"""
		self.ensure_one()
		if not date:
			date = self._context.get('date') or fields.Datetime.now()
		if not uom_id and self._context.get('uom'):
			uom_id = self._context['uom']
		if uom_id:
			# rebrowse with uom if given
			products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
			products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in enumerate(products_qty_partner)]
		else:
			products = [item[0] for item in products_qty_partner]

		if not products:
			return {}

		categ_ids = {}
		for p in products:
			categ = p.categ_id
			while categ:
				categ_ids[categ.id] = True
				categ = categ.parent_id
		categ_ids = list(categ_ids)

		is_product_template = products[0]._name == "product.template"
		if is_product_template:
			prod_tmpl_ids = [tmpl.id for tmpl in products]
			# all variants of all products
			prod_ids = [p.id for p in
						list(chain.from_iterable([t.product_variant_ids for t in products]))]
		else:
			prod_ids = [product.id for product in products]
			prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

		items = self._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids)

		results = {}
		for product, qty, partner in products_qty_partner:
			results[product.id] = 0.0
			suitable_rule = False

			# Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
			# An intermediary unit price may be computed according to a different UoM, in
			# which case the price_uom_id contains that UoM.
			# The final price will be converted to match `qty_uom_id`.
			qty_uom_id = self._context.get('uom') or product.uom_id.id
			qty_in_product_uom = qty
			if qty_uom_id != product.uom_id.id:
				try:
					qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
				except UserError:
					# Ignored - incompatible UoM in context, use default product UoM
					pass

			# if Public user try to access standard price from website sale, need to call price_compute.
			# TDE SURPRISE: product can actually be a template
			price = product.price_compute('list_price')[product.id]

			price_uom = self.env['uom.uom'].browse([qty_uom_id])
			
			seller = False
			
			for rule in items:
				if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
					continue
				if is_product_template:
					if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
						continue
					if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
						# product rule acceptable on template if has only one variant
						continue
				else:
					if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
						continue
					if rule.product_id and product.id != rule.product_id.id:
						continue

				if rule.categ_id:
					cat = product.categ_id
					while cat:
						if cat.id == rule.categ_id.id:
							break
						cat = cat.parent_id
					if not cat:
						continue

				if rule.base == 'pricelist' and rule.base_pricelist_id:
					price_tmp = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], date, uom_id)[product.id][0]  # TDE: 0 = price, 1 = rule
					price = rule.base_pricelist_id.currency_id._convert(price_tmp, self.currency_id, self.env.company, date, round=False)
				elif rule.base == 'vendor_price':
					product_for_seller = product.product_variant_ids[0] if is_product_template else product
					seller = product_for_seller.sudo()._select_seller(quantity=qty, uom_id=price_uom)
					seller = seller and seller.sudo() or seller
					price = seller and seller.price or 0
				else:
					# if base option is public price take sale price else cost price of product
					# price_compute returns the price in the context UoM, i.e. qty_uom_id
					price = product.price_compute(rule.base)[product.id]

				if price is not False:
					price = rule._compute_price(price, price_uom, product, quantity=qty, partner=partner)
					suitable_rule = rule
				break
			# Final price conversion into pricelist currency
			if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
				if suitable_rule.base == 'standard_price':
					cur = product.cost_currency_id
				elif suitable_rule.base == 'vendor_price' and seller:
					#we don't want to convert currency if vendor's similar currency is the same as pricelist's similar currency
					#so we just make cur=self.currency_id
					if seller.currency_id.similar_currency_id and self.currency_id.similar_currency_id and \
							seller.currency_id.similar_currency_id.id  == self.currency_id.similar_currency_id.id:
						cur = self.currency_id
					else:
						cur = seller.currency_id
				else:
					cur = product.currency_id
				price = cur._convert(price, self.currency_id, self.env.company, date, round=False)
				
				if suitable_rule.base == 'vendor_price':
					if suitable_rule.override_category_addition:
						price += price * suitable_rule.override_category_addition / 100
					elif 'min_addition' in self.env.context and product.categ_id.min_addition:
						price += price * product.categ_id.min_addition / 100
					elif product.categ_id.max_addition:
						price += price * product.categ_id.max_addition / 100

			if not suitable_rule:
				cur = product.currency_id
				price = cur._convert(price, self.currency_id, self.env.company, date, round=False)

			results[product.id] = (price, suitable_rule and suitable_rule.id or False)

		return results

class PricelistItem(models.Model):
	_inherit = "product.pricelist.item"
	
	base = fields.Selection(selection_add=[('vendor_price','Vendor Price')], ondelete={'vendor_price': 'cascade'})
	override_category_addition = fields.Float(string="Override Category Addition", help="This addition will override category addition.")