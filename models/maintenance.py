# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PropertyMaintenance(models.Model):
    """Property Maintenance Request"""

    _inherit = "maintenance.request"

    property_id = fields.Many2one("property.details", string="Property")
    tenancy_id = fields.Many2one("tenancy.details")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    landlord_id = fields.Many2one("res.partner", string="LandLord")
    maintenance_type_id = fields.Many2one(
        "product.template", string="Type", domain=[("is_maintenance", "=", True)]
    )
    price = fields.Float(related="maintenance_type_id.list_price", string="Price")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    invoice_state = fields.Boolean(string="State")

    bill_id = fields.Many2one("account.move", string="Bill")
    bill_state = fields.Boolean(string="State ")

    invoice_count = fields.Integer(
        string="Invoice Count", compute="_compute_invoice_count"
    )
    bill_count = fields.Integer(string="Bill Count", compute="_compute_bill_count")

    payment_from = fields.Selection(
        [("customer", "Customer"), ("vendor", "Vendor")],
        string="Payment From",
        default="customer",
    )
    payment_type = fields.Selection(
        [("invoice", "Invoice"), ("bill", "Bill")],
        string="Payment Type",
        default="invoice",
    )
    customer_id = fields.Many2one("res.partner", string="Customer")
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    maintenance_product_ids = fields.One2many(
        "maintenance.product.line", "maintenance_id"
    )
    total_untaxed_amount = fields.Monetary(
        string="Total Untaxed Amount", compute="_compute_total_untaxed_amount"
    )
    total = fields.Monetary(string="Total")

    rent_contract_id = fields.Many2one("tenancy.details", string="Rent Contract")
    sell_contract_id = fields.Many2one("property.vendor", string="Sell Contract")

    def action_crete_invoice(self):
        """Create Maintenance Invoice for Customer"""
        if not self.maintenance_product_ids:
            raise ValidationError(_("Add Product for create invoice"))
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": product.product_id.id,
                    "name": product.description,
                    "quantity": product.quantity,
                    "price_unit": product.price_unit,
                    "tax_ids": product.tax_ids.ids,
                },
            )
            for product in self.maintenance_product_ids
        ]
        data = {
            "move_type": "out_invoice",
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": invoice_lines,
            "maintenance_request_id": self.id,
        }
        if self.payment_from == "customer":
            if not self.customer_id:
                raise ValidationError(_("Add customer to create invoice"))
            data["partner_id"] = self.customer_id.id
        else:
            if not self.vendor_id:
                raise ValidationError(_("Add vendor to create invoice"))
            data["partner_id"] = (self.vendor_id.id,)
        invoice_id = self.env["account.move"].sudo().create(data)
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        self.invoice_id = invoice_id.id
        self.total = invoice_id.amount_total
        self.invoice_state = True

        return {
            "type": "ir.actions.act_window",
            "name": "Invoice",
            "res_model": "account.move",
            "res_id": invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_crete_bill(self):
        """View Bills"""
        if not self.maintenance_product_ids:
            raise ValidationError(_("Add Product for create bill"))
        bill_lines = [
            (
                0,
                0,
                {
                    "product_id": product.product_id.id,
                    "name": product.description,
                    "quantity": product.quantity,
                    "price_unit": product.price_unit,
                    "tax_ids": product.tax_ids.ids,
                },
            )
            for product in self.maintenance_product_ids
        ]
        data = {
            "move_type": "in_invoice",
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": bill_lines,
            "maintenance_request_id": self.id,
        }
        if self.payment_from == "customer":
            if not self.customer_id:
                raise ValidationError(_("Add customer to create bill"))
            data["partner_id"] = self.customer_id.id
        else:
            if not self.vendor_id:
                raise ValidationError(_("Add vendor to create bill"))
            data["partner_id"] = (self.vendor_id.id,)

        bill_id = self.env["account.move"].sudo().create(data)
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        if invoice_post_type == "automatically":
            bill_id.action_post()
        self.bill_id = bill_id.id
        self.total = bill_id.amount_total
        self.bill_state = True

        return {
            "type": "ir.actions.act_window",
            "name": "Bill",
            "res_model": "account.move",
            "res_id": bill_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.depends("maintenance_product_ids")
    def _compute_total_untaxed_amount(self):
        """Compute total Untaxed"""
        for rec in self:
            total_amount = 0.0
            if rec.maintenance_product_ids:
                for product in rec.maintenance_product_ids:
                    total_amount += product.price_subtotal
            rec.total_untaxed_amount = total_amount

    def _compute_invoice_count(self):
        """Compute invoice count"""
        for rec in self:
            rec.invoice_count = len(
                self.env["account.move"]
                .sudo()
                .search(
                    [
                        ("maintenance_request_id", "in", [rec.id]),
                        ("move_type", "=", "out_invoice"),
                    ]
                )
                .mapped("maintenance_request_id")
                .mapped("id")
            )

    def _compute_bill_count(self):
        """Compute bill count"""
        for rec in self:
            rec.bill_count = len(
                self.env["account.move"]
                .sudo()
                .search(
                    [
                        ("maintenance_request_id", "in", [rec.id]),
                        ("move_type", "=", "in_invoice"),
                    ]
                )
                .mapped("maintenance_request_id")
                .mapped("id")
            )

    def action_view_invoice(self):
        """View Invoices"""
        return {
            "name": "Invoices",
            "type": "ir.actions.act_window",
            "domain": [("maintenance_request_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "account.move",
            "target": "current",
        }

    def action_view_bills(self):
        """View Bills"""
        return {
            "name": "Bills",
            "type": "ir.actions.act_window",
            "domain": [("maintenance_request_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "account.move",
            "target": "current",
        }


class MaintenanceProduct(models.Model):
    """Maintenance Product"""

    _inherit = "product.template"

    is_maintenance = fields.Boolean(string="Maintenance")


class MaintenanceProductLine(models.Model):
    """Maintenance Product Line"""

    _name = "maintenance.product.line"
    _description = __doc__
    _rec_name = "product_id"

    maintenance_id = fields.Many2one("maintenance.request", string="Maintenance")
    product_id = fields.Many2one("product.product", string="Product")

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )

    quantity = fields.Integer(string="Quantity", default=1)
    description = fields.Char(string="Description")
    price_unit = fields.Monetary(string="Price")
    tax_ids = fields.Many2many(
        "account.tax", string="Taxes", domain=[("type_tax_use", "=", "sale")]
    )
    price_subtotal = fields.Monetary(string="Amount", compute="_compute_price_subtotal")

    @api.onchange("product_id")
    def _onchange_product_get_details(self):
        """Get product details"""
        for rec in self:
            rec.price_unit = rec.product_id.lst_price
            if rec.product_id.taxes_id:
                rec.tax_ids = rec.product_id.taxes_id.ids
            rec.description = rec.product_id.name

    @api.depends("product_id", "quantity", "price_unit")
    def _compute_price_subtotal(self):
        """Compute price subtotal"""
        for rec in self:
            total_amount = 0.0
            if rec.product_id:
                total_amount = rec.quantity * rec.price_unit
            rec.price_subtotal = total_amount
