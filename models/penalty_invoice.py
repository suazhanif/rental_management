# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PenaltyInvoice(models.Model):
    """Penalty Invoices"""

    _name = "penalty.invoice"
    _description = __doc__
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_penalty_name")
    rent_contract_id = fields.Many2one("tenancy.details", string="Rent No.")
    sale_contract_id = fields.Many2one("property.vendor", string="Sale No.")
    customer_id = fields.Many2one("res.partner", string="Customer")
    invoice_date = fields.Date(string="Invoice Date")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )

    rent_contract_invoice_id = fields.Many2one("rent.invoice", string="Rent Invoice")
    sale_contract_invoice_id = fields.Many2one("sale.invoice", string="Sale Invoice")

    amount = fields.Monetary(string="Amount")

    description = fields.Char(string="Description", translate=True)
    penalty_invoice_id = fields.Many2one("account.move", string="Invoice")
    payment_state = fields.Selection(
        related="penalty_invoice_id.payment_state", string="Payment Status"
    )
    landlord_id = fields.Many2one("res.partner", string="Landlord")

    @api.depends()
    def _compute_penalty_name(self):
        """Compute name according to rent contract or sale contract record"""
        for rec in self:
            name = "New"
            if rec.rent_contract_id:
                name = rec.rent_contract_id.tenancy_seq
            elif rec.sale_contract_id:
                name = rec.sale_contract_id.sold_seq
            rec.name = name

    @api.model
    def action_create_invoice(self):
        """Action Button For Create Invoice"""
        penalty_product = self.env["ir.config_parameter"].sudo().get_param(
            "rental_management.contract_penalty_item_id"
        ) or self.env.ref("rental_management.property_product_5")
        if not penalty_product:
            _logger.warning(
                "Penalty product not found. Please configure a penalty product before creating penalty invoices.",
                exc_info=True,
            )
            return False

        try:
            penalty_product_id = int(penalty_product)
        except Exception as e:
            _logger.warning(e, exc_info=True)
            return False

        invoice_id = False
        if self.rent_contract_id:
            invoice_data = {
                "partner_id": self.customer_id.id,
                "move_type": "out_invoice",
                "invoice_date": self.invoice_date,
                "tenancy_id": self.rent_contract_id.id,
                "penalty_id": self.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": penalty_product_id,
                            "name": self.description,
                            "quantity": 1,
                            "price_unit": self.amount,
                            "tax_ids": self.rent_contract_id.tax_ids.ids
                            if self.rent_contract_id.instalment_tax
                            else False,
                        },
                    )
                ],
            }
            invoice_id = self.env["account.move"].create(invoice_data)
            if invoice_id:
                mail_template = self.env.ref(
                    "rental_management.penalty_invoice_mail_template_for_rent_contract"
                )
                if mail_template:
                    mail_template.with_context({"penalty_rec": self}).send_mail(
                        self.rent_contract_id.id, force_send=True
                    )
        elif self.sale_contract_id:
            invoice_data = {
                "partner_id": self.customer_id.id,
                "move_type": "out_invoice",
                "invoice_date": self.invoice_date,
                "sold_id": self.sale_contract_id.id,
                "penalty_id": self.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": penalty_product_id,
                            "name": self.description,
                            "quantity": 1,
                            "price_unit": self.amount,
                            "tax_ids": self.sale_contract_id.taxes_ids.ids
                            if self.sale_contract_id.is_taxes
                            and self.sale_contract_id.taxes_ids
                            else False,
                        },
                    )
                ],
            }
            invoice_id = self.env["account.move"].create(invoice_data)
            if invoice_id:
                mail_template = self.env.ref(
                    "rental_management.penalty_invoice_mail_template_for_sale_contract"
                )
                if mail_template:
                    mail_template.with_context({"penalty_rec": self}).send_mail(
                        self.sale_contract_id.id, force_send=True
                    )

        if invoice_id:
            self.penalty_invoice_id = invoice_id.id
        return invoice_id
