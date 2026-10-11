# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PropertyPayment(models.TransientModel):
    """Rent contract extra payment"""

    _name = "property.payment.wizard"
    _description = "Create Invoice For Rent"

    tenancy_id = fields.Many2one("tenancy.details", string="Tenancy No.")
    customer_id = fields.Many2one(related="tenancy_id.tenancy_id", string="Customer")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    type = fields.Selection(
        [
            ("deposit", "Deposit"),
            ("maintenance", "Maintenance"),
            ("penalty", "Penalty"),
            ("extra_service", "Extra Service"),
            ("other", "Other"),
        ],
        string="Payment For",
    )
    description = fields.Char(string="Description", translate=True)
    invoice_date = fields.Date(string="Date", default=fields.Date.today())
    rent_amount = fields.Monetary(string="Rent Amount", related="tenancy_id.total_rent")
    amount = fields.Monetary(string="Amount")
    rent_invoice_id = fields.Many2one("account.move", string="Invoice")
    # service
    service_id = fields.Many2one(
        "product.product",
        string="Service",
        default=lambda self: self.env.ref(
            "rental_management.property_product_1", raise_if_not_found=False
        ),
    )
    tax_ids = fields.Many2many("account.tax", string="Taxes")

    is_invoice = fields.Boolean()
    is_bill = fields.Boolean()
    bill_type = fields.Char(string="Payment For ")
    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        default=lambda self: self.tenancy_id.property_landlord_id,
    )
    vendor_phone = fields.Char(string="Phone", related="vendor_id.phone")
    vendor_email = fields.Char(string="Email", related="vendor_id.email")

    # Default Get
    @api.model
    def default_get(self, fields_list):
        """Default get"""
        res = super(PropertyPayment, self).default_get(fields_list)
        current_context = self.env.context
        active_id = current_context.get("active_id")
        is_invoice = current_context.get("is_invoice")
        is_bill = current_context.get("is_bill")
        tenancy = self.env["tenancy.details"].sudo().browse(active_id)
        res["tenancy_id"] = active_id
        res["is_invoice"] = is_invoice
        res["is_bill"] = is_bill
        if tenancy.exists():
            res["vendor_id"] = tenancy.property_landlord_id.id
        return res

    @api.constrains("amount")
    def _check_amount_not_negative(self):
        """Raise validation if amount is negative"""
        for rec in self:
            if rec.amount and rec.amount < 0:
                raise ValidationError(_("Please enter a valid (non-negative) amount."))

    @api.onchange("type")
    def _onchange_type_service(self):
        """Onchange service type"""
        for rec in self:
            if rec.type == "extra_service":
                rec.service_id = False
            else:
                rec.service_id = self.env.ref(
                    "rental_management.property_product_1", raise_if_not_found=False
                )

    def property_payment_action(self):
        """Process rent contract payment"""
        if self.type == "extra_service":
            invoice_id = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "partner_id": self.customer_id.id,
                        "tenancy_id": self.tenancy_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": self.invoice_date,
                        "invoice_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "product_id": self.service_id.id,
                                    "name": self.description,
                                    "quantity": 1,
                                    "price_unit": self.amount,
                                    "tax_ids": self.tax_ids.ids,
                                },
                            )
                        ],
                    }
                )
            )
            self.env["contract.extra.service.line"].sudo().create(
                {
                    "contract_id": self.tenancy_id.id,
                    "service_id": self.service_id.id,
                    "price": invoice_id.amount_total,
                    "invoice_id": invoice_id.id,
                }
            )
            if not self.tenancy_id.is_added_services:
                self.tenancy_id.is_added_services = True
        else:
            self.process_contract_invoice()

    def process_contract_invoice(self):
        """Process contract payment invoice"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer_id.id,
                    "tenancy_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_date,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.service_id.id,
                                "name": self.description,
                                "quantity": 1,
                                "price_unit": self.amount,
                                "tax_ids": self.tax_ids.ids,
                            },
                        )
                    ],
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        self.env["rent.invoice"].create(
            {
                "tenancy_id": self.tenancy_id.id,
                "type": self.type,
                "invoice_date": self.invoice_date,
                "amount": self.amount,
                "description": self.description,
                "rent_invoice_id": invoice_id.id,
            }
        )

    def property_bill_action(self):
        """Property Rent contract bill"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        data = {
            "partner_id": self.vendor_id.id,
            "tenancy_id": self.tenancy_id.id,
            "move_type": "in_invoice",
            "invoice_date": self.invoice_date,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.service_id.id,
                        "name": self.description,
                        "quantity": 1,
                        "price_unit": self.amount,
                        "tax_ids": self.tax_ids.ids,
                    },
                )
            ],
        }
        bill_id = self.env["account.move"].sudo().create(data)
        if invoice_post_type == "automatically":
            bill_id.action_post()

        self.env["rent.bill"].create(
            {
                "tenancy_id": self.tenancy_id.id,
                "bill_type": self.bill_type,
                "invoice_date": self.invoice_date,
                "amount": self.amount,
                "description": self.description,
                "rent_bill_id": bill_id.id,
                "vendor_id": self.vendor_id.id,
            }
        )
