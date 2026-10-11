# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class RentBill(models.Model):
    """Rent Contract Bills"""

    _name = "rent.bill"
    _description = "Crete Bills for Rented property"
    _rec_name = "tenancy_id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    tenancy_id = fields.Many2one("tenancy.details", string="Rent No.")
    customer_id = fields.Many2one(
        related="tenancy_id.tenancy_id", string="Customer", store=True
    )
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    bill_type = fields.Char(string="Payment")
    invoice_date = fields.Date(string="Bill Date")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    installment_type = fields.Selection(related="tenancy_id.type")

    # Calculation
    amount = fields.Monetary(string="Amount ")
    rent_amount = fields.Monetary(string="Rent Amount")

    description = fields.Char(string="Description", translate=True)
    rent_bill_id = fields.Many2one("account.move", string="Bill")
    payment_state = fields.Selection(
        related="rent_bill_id.payment_state", string="Payment Status"
    )
    landlord_id = fields.Many2one(
        related="tenancy_id.property_id.landlord_id", store=True
    )
    tenancy_type = fields.Selection(related="tenancy_id.type", string="Rent Type")
    service_amount = fields.Monetary(
        string="Extra Amount",
        help="Recurring Utility Service (if any) + Recurring Maintenance Service (if any)",
    )
    is_extra_service = fields.Boolean(related="tenancy_id.is_extra_service")
