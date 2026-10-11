# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models


class PropertySold(models.TransientModel):
    """Property Sale Installment Process"""

    _name = "property.vendor.wizard"
    _description = "Wizard For Selecting Customer to sale"

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    property_id = fields.Many2one("property.details", string="Property")
    customer_id = fields.Many2one("property.vendor", string="Customer")
    final_price = fields.Monetary(string="Final Price")
    sold_invoice_id = fields.Many2one("account.move")
    broker_id = fields.Many2one(related="customer_id.broker_id")
    is_any_broker = fields.Boolean(related="customer_id.is_any_broker")
    quarter = fields.Integer(string="Quarter", default=4)

    # Payment Term
    duration_id = fields.Many2one(
        "contract.duration", string="Duration", domain="[('rent_unit','=','Month')]"
    )
    payment_term = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("full_payment", "Full Payment"),
            ("quarterly", "Quarterly"),
        ],
        string="Payment Term",
    )
    start_date = fields.Date(string="Start From")

    # Installment Item
    installment_item_id = fields.Many2one(
        "product.product",
        string="Installment Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_1", raise_if_not_found=False
        ),
    )
    is_taxes = fields.Boolean(string="Taxes ?")
    taxes_ids = fields.Many2many("account.tax", string="Taxes")

    @api.model
    def default_get(self, fields_list):
        """Default get"""
        res = super(PropertySold, self).default_get(fields_list)
        active_id = self.env.context.get("active_id")
        sell_id = self.env["property.vendor"].browse(active_id)
        res["customer_id"] = sell_id.id
        res["final_price"] = sell_id.ask_price
        res["is_taxes"] = sell_id.is_taxes
        res["taxes_ids"] = [(6, 0, sell_id.taxes_ids.ids)]
        res["property_id"] = sell_id.property_id.id
        res["installment_item_id"] = sell_id.installment_item_id.id
        return res

    def property_sale_action(self):
        """Process property sale"""
        if self.final_price <= 0:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": _("Please enter a valid (non-negative) price."),
                    "sticky": False,
                },
            }
        if self.payment_term == "quarterly" and self.quarter <= 1:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": _("Quarter"),
                    "message": _("Quarter should be greater than 1."),
                    "sticky": False,
                },
            }

        self.customer_id.write(
            {
                "installment_item_id": self.installment_item_id.id,
                "is_taxes": self.is_taxes,
                "taxes_ids": self.taxes_ids.ids,
                "sale_price": self.final_price,
                "payment_term": self.payment_term,
            }
        )
        count = 0
        for rec in self:
            if rec.payment_term == "monthly":
                amount = rec.customer_id.payable_amount / rec.duration_id.month
                invoice_date = rec.start_date
                for r in range(rec.duration_id.month):
                    count = count + 1
                    sold_invoice_data = {
                        "name": f"Installment : {str(count)}",
                        "property_sold_id": rec.customer_id.id,
                        "invoice_date": invoice_date,
                        "amount": amount,
                        "tax_ids": self.taxes_ids.ids if self.is_taxes else False,
                    }
                    self.env["sale.invoice"].create(sold_invoice_data)
                    invoice_date = invoice_date + relativedelta(months=1)
            elif rec.payment_term == "quarterly":
                if rec.quarter > 1:
                    amount = rec.customer_id.payable_amount / rec.quarter
                    invoice_date = rec.start_date
                    for r in range(rec.quarter):
                        count = count + 1
                        sold_invoice_data = {
                            "name": f"Quarter Payment : {str(count)}",
                            "property_sold_id": rec.customer_id.id,
                            "invoice_date": invoice_date,
                            "amount": amount,
                            "tax_ids": self.taxes_ids.ids if self.is_taxes else False,
                        }
                        self.env["sale.invoice"].create(sold_invoice_data)
                        invoice_date = invoice_date + relativedelta(months=3)
            elif rec.payment_term == "full_payment":
                self.env["sale.invoice"].create(
                    {
                        "name": "Full Payment",
                        "property_sold_id": self.customer_id.id,
                        "invoice_date": fields.Date.today(),
                        "amount": rec.customer_id.payable_amount,
                        "tax_ids": self.taxes_ids.ids if self.is_taxes else False,
                        "is_remain_invoice": True,
                    }
                )
