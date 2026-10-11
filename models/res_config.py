# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RentalConfig(models.TransientModel):
    """Real estate config settings"""

    _inherit = "res.config.settings"

    reminder_days = fields.Integer(
        string="Days", default=5, config_parameter="rental_management.reminder_days"
    )
    sale_reminder_days = fields.Integer(
        string="Days ",
        default=3,
        config_parameter="rental_management.sale_reminder_days",
    )
    invoice_post_type = fields.Selection(
        [
            ("manual", "Invoice Post Manually"),
            ("automatically", "Invoice Post Automatically"),
        ],
        string="Invoice Post",
        default="manual",
        config_parameter="rental_management.invoice_post_type",
    )
    month_days = fields.Integer(
        string="Month Days", default=30, config_parameter="rental_management.month_days"
    )
    quarter_days = fields.Integer(
        string="Quarter Days",
        default=90,
        config_parameter="rental_management.quarter_days",
    )
    year_days = fields.Integer(
        string="Year Days", default=365, config_parameter="rental_management.year_days"
    )
    half_year_days = fields.Integer(
        string="Half Year Days",
        default=183,
        config_parameter="rental_management.half_year_days",
    )

    # Default Account Product
    installment_item_id = fields.Many2one(
        "product.product",
        string="Installment Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_1", raise_if_not_found=False
        ),
        config_parameter="rental_management.account_installment_item_id",
    )
    deposit_item_id = fields.Many2one(
        "product.product",
        string="Deposit Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_2", raise_if_not_found=False
        ),
        config_parameter="rental_management.account_deposit_item_id",
    )
    broker_item_id = fields.Many2one(
        "product.product",
        string="Broker Commission Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_3", raise_if_not_found=False
        ),
        config_parameter="rental_management.account_broker_item_id",
    )
    maintenance_item_id = fields.Many2one(
        "product.product",
        string="Maintenance Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_4", raise_if_not_found=False
        ),
        config_parameter="rental_management.account_maintenance_item_id",
    )
    contract_penalty_item_id = fields.Many2one(
        "product.product",
        string="Contract Penalty Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_5", raise_if_not_found=False
        ),
        config_parameter="rental_management.contract_penalty_item_id",
    )

    # Penalty Configurations
    is_penalty_applied = fields.Boolean(
        string="Is Any Penalty?",
        config_parameter="rental_management.is_penalty_applied",
    )
    penalty_days_after_due_for_rent_contract = fields.Integer(
        string="Apply Penalty After (Days)",
        default="5",
        config_parameter="rental_management.penalty_days_after_due_for_rent_contract",
    )
    penalty_percentage_for_rent_contract = fields.Integer(
        string="Rent Contract Percentage",
        config_parameter="rental_management.penalty_percentage_for_rent_contract",
    )
    penalty_days_after_due_for_sale_contract = fields.Integer(
        string="Apply Penalty After (Days) ",
        default="5",
        config_parameter="rental_management.penalty_days_after_due_for_sale_contract",
    )
    penalty_percentage_for_sale_contract = fields.Integer(
        string="Sale Contract Percentage",
        config_parameter="rental_management.penalty_percentage_for_sale_contract",
    )

    @api.constrains(
        "reminder_days",
        "sale_reminder_days",
        "month_days",
        "quarter_days",
        "year_days",
        "half_year_days",
    )
    def _check_values_is_not_negative(self):
        """Raise Validation if value is negative"""
        for rec in self:
            if rec.reminder_days and rec.reminder_days < 0:
                raise ValidationError(
                    _(
                        "Reminder days for creating tenancy invoice must be zero or greater"
                    )
                )
            if rec.sale_reminder_days and rec.sale_reminder_days < 0:
                raise ValidationError(
                    _("Reminder days for creating invoice must be zero or greater")
                )
            if rec.month_days and rec.month_days < 0:
                raise ValidationError(_("Month days must be zero or greater"))
            if rec.quarter_days and rec.quarter_days < 0:
                raise ValidationError(_("Quarter days must be zero or greater"))
            if rec.year_days and rec.year_days < 0:
                raise ValidationError(_("Year days must be zero or greater"))
            if rec.half_year_days and rec.half_year_days < 0:
                raise ValidationError(_("Half year days must be zero or greater"))
