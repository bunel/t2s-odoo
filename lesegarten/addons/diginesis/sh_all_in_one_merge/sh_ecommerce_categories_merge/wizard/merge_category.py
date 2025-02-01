# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MergeEcommerceCategoryWizard(models.Model):
    _name = "merge.po.category.wizard"
    _description = "Merge Ecommerce Category"

    operation = fields.Selection([
        ("create_category", "Create All remaining categories on Ecommerce."),
        ("assign_category", "Linked all products with corresponding Ecommerce category.")],
        string="Select Operation to Do.", default="create_category")

    category_ids = fields.Many2many(
        "product.category", string="Remaining Categories", domain=[
            ("ecommerce_category_id", "=", False)])

    # create ecommerce category if not exist
    def create_ecommerce_category(self, category_id=False):
        product_category = self.env["product.category"]
        ecommerce_category = self.env["product.public.category"]
        category_obj = product_category.browse(category_id)
        pos_parent_id = False
        if category_obj and category_obj.parent_id:
            child_ecommerce_category = ecommerce_category.search(
                [["product_category_id", "=", category_obj.parent_id.id]], limit=1)
            if not child_ecommerce_category:
                pos_parent_id = self.create_ecommerce_category(
                    category_obj.parent_id.id).id
            else:
                pos_parent_id = child_ecommerce_category.id
        if category_obj:
            value = {"parent_id": pos_parent_id,
                     "name": category_obj.name,
                     "product_category_id": category_id
                     }
            ecommerce_category = ecommerce_category.create(value)
            category_obj.write(
                {"ecommerce_category_id": ecommerce_category.id})
        return ecommerce_category

    def fetch_products_with_missing_category(self):
        return self.env["product.template"].search([
            ("categ_id", "!=", False),
            ("public_categ_ids", "=", False)])

    def fetch_related_ecommerce_category(self, categ_id=False):
        if categ_id and categ_id.ecommerce_category_id:
            return categ_id.ecommerce_category_id.id

    def button_apply(self):
        # check operation and based on that perform operation
        if self.operation == "create_category":
            if not self.category_ids:
                raise UserError(
                    _("Please select categories to merge with Ecommerce !")
                )

            for category in self.category_ids:
                if category:
                    self.create_ecommerce_category(category.id)
        elif self.operation == "assign_category":
            products = self.fetch_products_with_missing_category()
            if products:
                for product in products:
                    ecommerce_category = self.fetch_related_ecommerce_category(
                        product.categ_id)
                    if ecommerce_category:
                        product.write(
                            {"public_categ_ids": [(6, 0, [ecommerce_category])]})
