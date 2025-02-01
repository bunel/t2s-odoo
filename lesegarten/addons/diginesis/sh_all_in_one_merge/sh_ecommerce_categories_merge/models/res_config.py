# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sync_with_ecommerce_category = fields.Boolean(
        "Sync new Product Category With Ecommerce Category",
        default=False)

    auto_sync_product_with_ecommerce_category = fields.Boolean(
        "Auto Sync new Product With Ecommerce Category",
        default=False)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sync_with_ecommerce_category = fields.Boolean(
        "Sync new Product Category With Ecommerce Category",
        related="company_id.sync_with_ecommerce_category", readonly=False)

    auto_sync_product_with_ecommerce_category = fields.Boolean(
        "Auto Sync new Product With Ecommerce Category",
        related="company_id.auto_sync_product_with_ecommerce_category", readonly=False)
