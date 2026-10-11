# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class RentInvoice(models.Model):
    """Rent Contract Invoices"""

    _name = "rent.invoice"
    _description = "Crete Invoice for Rented property"
    _rec_name = "tenancy_id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    tenancy_id = fields.Many2one("tenancy.details", string="Rent No.")
    customer_id = fields.Many2one(
        related="tenancy_id.tenancy_id", string="Customer", store=True
    )
    type = fields.Selection(
        [
            ("deposit", "Deposit"),
            ("rent", "Rent"),
            ("maintenance", "Maintenance"),
            ("utility", "Utility"),
            ("penalty", "Penalty"),
            ("full_rent", "Full Rent"),
            ("settlement", "Settlement"),
            ("other", "Other"),
        ],
        string="Payment",
        default="rent",
    )
    invoice_date = fields.Date(string="Invoice Date")
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
    rent_invoice_id = fields.Many2one("account.move", string="Invoice")
    payment_state = fields.Selection(
        related="rent_invoice_id.payment_state", string="Payment Status"
    )
    landlord_id = fields.Many2one(
        related="tenancy_id.property_id.landlord_id", store=True
    )
    is_yearly = fields.Boolean()
    remain = fields.Integer()
    tenancy_type = fields.Selection(related="tenancy_id.type", string="Rent Type")
    service_amount = fields.Monetary(
        string="Extra Amount",
        help="Recurring Utility Service (if any) + Recurring Maintenance Service (if any)",
    )
    is_extra_service = fields.Boolean(related="tenancy_id.is_extra_service")

    is_first_installment = fields.Boolean()
    service_days = fields.Integer()

    def action_create_invoice(self):
        if self.tenancy_id.rent_unit == "Day":
            self._process_manual_daily_invoice()
        else:
            self._process_manual_invoice()
        # Process Separate Invoice
        if (
                self.tenancy_id.is_maintenance_service
                and self.tenancy_id.maintenance_service_invoice == "separate"
        ):
            self._process_separate_invoices(maintenance=True)
        if (
                self.tenancy_id.is_extra_service
                and self.tenancy_id.extra_service_invoice == "separate"
        ):
            self._process_separate_invoices(utility=True)

    def _process_manual_invoice(self):
        """Process Manual Invoice : Monthly, Quarterly Yearly"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        invoice_lines = []
        amount = 0.0
        if (
                self.tenancy_id.is_extra_service
                and self.tenancy_id.extra_service_invoice == "merge"
        ):
            if self.tenancy_id.payment_term in ["monthly", "half_year"]:
                for line in self.tenancy_id.extra_services_ids:
                    if line.service_type == "monthly":
                        amount = amount + line.price
                        service_invoice_record = {
                            "product_id": line.service_id.id,
                            "name": "Service Type : Recurring" + "\n"
                                                                 "Service : " + str(line.service_id.name),
                            "quantity": 1,
                            "price_unit": line.price,
                            "tax_ids": line.tenancy_id.tax_ids.ids
                            if line.tenancy_id.service_tax
                            else False,
                        }
                        invoice_lines.append((0, 0, service_invoice_record))
            if self.tenancy_id.payment_term == "quarterly":
                for line in self.tenancy_id.extra_services_ids:
                    if line.service_type == "monthly":
                        amount = amount + (
                                line.price * (self.remain if self.remain > 0 else 3)
                        )
                        service_invoice_record = {
                            "product_id": line.service_id.id,
                            "name": "Service Type : Recurring" + "\n"
                                                                 "Service : " + str(line.service_id.name),
                            "quantity": self.remain if self.remain > 0 else 3,
                            "price_unit": line.price,
                            "tax_ids": line.tenancy_id.tax_ids.ids
                            if line.tenancy_id.service_tax
                            else False,
                        }
                        invoice_lines.append((0, 0, service_invoice_record))
            if self.tenancy_id.payment_term == "year":
                for line in self.tenancy_id.extra_services_ids:
                    if line.service_type == "monthly":
                        amount = amount + (line.price * 12)
                        service_invoice_record = {
                            "product_id": line.service_id.id,
                            "name": "Service Type : Recurring" + "\n"
                                                                 "Service : " + str(line.service_id.name),
                            "quantity": 1,
                            "price_unit": line.price,
                            "tax_ids": line.tenancy_id.tax_ids.ids
                            if line.tenancy_id.service_tax
                            else False,
                        }
                        invoice_lines.append((0, 0, service_invoice_record))
        if (
                self.tenancy_id.is_maintenance_service
                and self.tenancy_id.maintenance_rent_type == "recurring"
                and self.tenancy_id.maintenance_service_invoice == "merge"
        ):
            maintenance_record = {
                "product_id": self.tenancy_id.maintenance_item_id.id,
                "name": "Recurring Maintenance of " + self.tenancy_id.property_id.name,
                "quantity": 1,
                "price_unit": self.tenancy_id.total_maintenance,
                "tax_ids": self.tenancy_id.tax_ids.ids
                if self.tenancy_id.instalment_tax
                else False,
            }
            if self.tenancy_id.payment_term == "quarterly":
                maintenance_record["quantity"] = self.remain if self.remain > 0 else 3
            amount = amount + (
                    maintenance_record["quantity"] * self.tenancy_id.total_maintenance
            )
            invoice_lines.append((0, 0, maintenance_record))
        record = {
            "product_id": self.tenancy_id.installment_item_id.id,
            "name": self.description,
            "quantity": 1,
            "price_unit": self.amount,
            "tax_ids": self.tenancy_id.tax_ids.ids
            if self.tenancy_id.instalment_tax
            else False,
        }
        invoice_lines.append((0, 0, record))
        rent_record = {
            "partner_id": self.customer_id.id,
            "move_type": "out_invoice",
            "invoice_date": self.invoice_date,
            "tenancy_id": self.tenancy_id.id,
            "invoice_line_ids": invoice_lines,
        }
        invoice_id = self.env["account.move"].create(rent_record)
        self.service_amount = (
            (invoice_id.amount_total - self.amount)
            if invoice_id.amount_total > 0
            else 0.0
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        self.rent_invoice_id = invoice_id.id
        self.tenancy_id.action_send_tenancy_reminder()

    def _process_manual_daily_invoice(self):
        """Process Daily Invoice"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": self.tenancy_id.installment_item_id.id,
                    "name": self.description,
                    "quantity": 1,
                    "price_unit": self.amount,
                    "tax_ids": self.tenancy_id.tax_ids.ids
                    if self.tenancy_id.instalment_tax
                    else False,
                },
            )
        ]
        if (
                self.tenancy_id.is_extra_service
                and self.tenancy_id.extra_service_invoice == "merge"
        ):
            for line in self.tenancy_id.extra_services_ids.filtered(
                    lambda line: line.service_type == "monthly"
            ):
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": "Service Type : Recurring" + "\n"
                                                                 "Service : " + str(line.service_id.name),
                            "quantity": 1,
                            "price_unit": line.price * self.service_days,
                            "tax_ids": line.tenancy_id.tax_ids.ids
                            if line.tenancy_id.service_tax
                            else False,
                        },
                    )
                )
        if (
                self.tenancy_id.is_maintenance_service
                and self.tenancy_id.maintenance_rent_type == "recurring"
                and self.tenancy_id.maintenance_service_invoice == "merge"
        ):
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": self.tenancy_id.maintenance_item_id.id,
                        "name": "Recurring Maintenance of "
                                + self.tenancy_id.property_id.name,
                        "quantity": 1,
                        "price_unit": self.tenancy_id.total_maintenance
                                      * self.service_days,
                        "tax_ids": False,
                    },
                )
            )
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_date,
                    "tenancy_id": self.tenancy_id.id,
                    "invoice_line_ids": invoice_lines,
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        self.rent_invoice_id = invoice_id.id
        self.service_amount = (
            (invoice_id.amount_total - self.amount)
            if invoice_id.amount_total > 0
            else 0.0
        )
        self.tenancy_id.action_send_tenancy_reminder()

    def _process_separate_invoices(self, maintenance=None, utility=None):
        """Process Utility and Maintenance Separate Invoices"""
        qty = 1
        if self.tenancy_id.rent_unit == "Day":
            qty = self.service_days
        else:
            if self.tenancy_id.payment_term == "quarterly":
                qty = self.remain if self.remain > 0 else 3
        if maintenance:
            maintenance_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.tenancy_id.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_date,
                    "tenancy_id": self.tenancy_id.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.tenancy_id.maintenance_item_id.id,
                                "name": "Recurring Maintenance of "
                                        + self.tenancy_id.property_id.name,
                                "quantity": qty,
                                "price_unit": self.tenancy_id.total_maintenance,
                            },
                        )
                    ],
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.tenancy_id.id,
                    "type": "maintenance",
                    "invoice_date": self.invoice_date,
                    "amount": maintenance_invoice_id.amount_total,
                    "description": "Recurring Maintenance of "
                                   + self.tenancy_id.property_id.name,
                    "rent_invoice_id": maintenance_invoice_id.id,
                }
            )
        if utility:
            service_invoice_lines = []
            for line in self.tenancy_id.extra_services_ids.filtered(
                    lambda line: line.service_type == "monthly"
            ):
                service_invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": f"Service Type : Recurring - {line.service_id.name}",
                            "quantity": qty,
                            "price_unit": line.price,
                            "tax_ids": self.tenancy_id.tax_ids.ids
                            if self.tenancy_id.service_tax
                            else False,
                        },
                    )
                )
            service_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.tenancy_id.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_date,
                    "tenancy_id": self.tenancy_id.id,
                    "invoice_line_ids": service_invoice_lines,
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.tenancy_id.id,
                    "type": "other",
                    "invoice_date": self.invoice_date,
                    "amount": service_invoice_id.amount_total,
                    "description": "Recurring Utility Services",
                    "rent_invoice_id": service_invoice_id.id,
                }
            )


class TenancyInvoice(models.Model):
    """Tenancy account move"""

    _inherit = "account.move"

    tenancy_id = fields.Many2one(
        "tenancy.details", readonly=True, string="Rent Contract Ref.", store=True
    )
    sold_id = fields.Many2one(
        "property.vendor", string="Sold Information", readonly=True, store=True
    )
    tenancy_property_id = fields.Many2one(
        related="tenancy_id.property_id", string="Property"
    )
    sold_property_id = fields.Many2one(
        related="sold_id.property_id", string="Property "
    )
    maintenance_request_id = fields.Many2one(
        "maintenance.request", string="Maintenance Ref."
    )
    penalty_id = fields.Many2one("penalty.invoice", readonly=True)
    is_deposit_invoice = fields.Boolean(
        string="Security Deposit Invoice",
        readonly=True,
        help="Invoice holding only the security deposit of a rent contract.",
    )
