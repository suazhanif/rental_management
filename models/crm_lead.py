# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PropertyInquiry(models.Model):
    _inherit = "crm.lead"

    property_id = fields.Many2one(
        "property.details",
        string="Property",
        domain="['|',('stage','=','available'),('stage','=','sale')]",
    )
    price = fields.Monetary(related="property_id.price")

    # For sale
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency "
    )
    ask_price = fields.Monetary(string="Ask Price")

    # Property Details
    property_type = fields.Selection(
        [
            ("land", "Land"),
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("industrial", "Industrial"),
        ],
        string="Property Type",
        required=True,
        default="residential",
    )
    sale_lease = fields.Selection(
        [
            ("for_sale", "Sale"),
            ("employee_family", "Employee Family Accommodation"),
            ("bachelor", "Bachelor Accommodation"),
            ("for_tenancy", "Rent"),
        ],
        string="Property For",
        default="for_tenancy",
        required=True,
    )
    furnishing_id = fields.Many2one("property.furnishing", string="Furnishing")
    unit_type = fields.Integer(string="Unit Type", default=1)
    available_property_count = fields.Integer(
        string="Available Properties", compute="_compute_available_property_count"
    )

    def _available_property_domain(self):
        return [
            ("type", "=", self.property_type),
            ("stage", "=", "available"),
            ("sale_lease", "=", self.sale_lease),
        ]

    @api.depends("property_type", "sale_lease")
    def _compute_available_property_count(self):
        for lead in self:
            if lead.property_type:
                lead.available_property_count = self.env[
                    "property.details"
                ].search_count(lead._available_property_domain())
            else:
                lead.available_property_count = 0

    def action_open_property_details(self):
        self.ensure_one()

        action = (
            self.env.ref("rental_management.property_details_action").sudo().read()[0]
        )

        action["domain"] = self._available_property_domain()

        action["context"] = {
            "default_type": self.property_type,
            "default_sale_lease": self.sale_lease,
        }

        return action
