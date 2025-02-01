# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models


class InternalCategory(models.Model):
    _inherit = "product.category"

    @api.model
    def get_sync_with_ecommerce(self):
        # get default value from config file
        return self.env.user.company_id.sync_with_ecommerce_category

    @api.depends("sync_with_ecommerce_category")
    def _compute_sync_field(self):
        for rec in self:
            if not self.env.user.company_id.sync_with_ecommerce_category:
                rec.hide_sync_field = True
            else:
                rec.hide_sync_field = False

    ecommerce_category_id = fields.Many2one(
        "product.public.category", string="Ecommerce Category")
    sync_with_ecommerce_category = fields.Boolean(
        "Sync with Ecommerce Category", default=get_sync_with_ecommerce)
    hide_sync_field = fields.Boolean(
        "Hide Sync Fields", compute="_compute_sync_field")

    @api.model
    def create(self, vals):
        res = super(InternalCategory, self).create(vals)
        if vals.get("sync_with_ecommerce_category") and vals.get("sync_with_ecommerce_category"):
            ecommerce_category = self.env["merge.po.category.wizard"]
            # create ecommerce category if sync boolean is true
            ecommerce_category.create_ecommerce_category(res.id)
        elif "sync_with_ecommerce_category" not in vals and self.env.user.company_id.sync_with_ecommerce_category:
            ecommerce_category = self.env["merge.po.category.wizard"]
            # create ecommerce category if sync boolean is true
            ecommerce_category.create_ecommerce_category(res.id)
        return res

    def write(self, vals):
        res = super(InternalCategory, self).write(vals)
        for rec in self:
            if rec.sync_with_ecommerce_category and rec.ecommerce_category_id:
                if vals.get("name"):
                    rec.ecommerce_category_id.write({"name": vals.get("name")})
                if vals.get("parent_id"):
                    ecommerce_category = self.env["product.public.category"].search(
                        [("product_category_id", "=", vals.get("parent_id"))], limit=1)
                    created_ecommerce_category = False
                    if not ecommerce_category:
                        ecommerce_category = self.env["merge.po.category.wizard"]
                        # created_ecommerce_category = ecommerce_categ_obj.create_ecommerce_category(rec.id)
                    else:
                        created_ecommerce_category = ecommerce_category
                    if created_ecommerce_category:
                        rec.ecommerce_category_id.write(
                            {"parent_id": created_ecommerce_category.id})
        return res

    def unlink(self):
        for rec in self:
            if rec.ecommerce_category_id:
                rec.ecommerce_category_id.unlink()  # Delete related ecommerce category
        return super(InternalCategory, self).unlink()


class Product(models.Model):
    _inherit = "product.template"

    @api.model
    def create(self, vals):
        res = super(Product, self).create(vals)
        if self.env.user.company_id.auto_sync_product_with_ecommerce_category and vals.get("categ_id"):
            related_ecommerce_category = self.env["product.public.category"].search(
                [("product_category_id", "=", vals.get("categ_id"))], limit=1)
            if related_ecommerce_category:
                res.write(
                    {"public_categ_ids": [(6, 0, [related_ecommerce_category.id])]})
            # assign ecommerce category if sync boolean is true in config
        return res

    def write(self, vals):
        for _ in self:
            if self.env.user.company_id.auto_sync_product_with_ecommerce_category and vals.get("categ_id"):
                ecommerce_category = self.env["product.public.category"].search(
                    [("product_category_id", "=", vals.get("categ_id"))], limit=1)
                if ecommerce_category:
                    # assign ecommerce_category if sync boolean is true in config
                    vals.update(
                        {"public_categ_ids": [(6, 0, [ecommerce_category.id])]})
        return super(Product, self).write(vals)


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    product_category_id = fields.Many2one(
        "product.category", string="product Category")
