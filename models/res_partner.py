# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class UserTypes(models.Model):
    """Partner User Type : Customer, Landlord, Broker"""

    _inherit = "res.partner"

    user_type = fields.Selection(
        [("landlord", "LandLord"), ("customer", "Customer"), ("broker", "Broker"), ("other", "Other")],
        string="User Type",
    )
    properties_count = fields.Integer(
        string="Properties Count", compute="_compute_properties_count"
    )
    properties_ids = fields.One2many(
        "property.details", "landlord_id", string="Properties "
    )
    brokerage_company_id = fields.Many2one(
        "res.company",
        string=" Brokerage Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_brokerage_currency",
    )

    # Customer Fields
    is_tenancy = fields.Boolean(string="Property Renting")
    is_sold_customer = fields.Boolean(string="Property Buyer")

    # Broker Fields
    tenancy_ids = fields.One2many("tenancy.details", "broker_id", string="Tenancy ")
    property_sold_ids = fields.One2many(
        "property.vendor", "broker_id", string="Sold Commission"
    )

    # Landline Number
    phone_landline = fields.Char("Landline")

    # Additional Address
    po_box = fields.Char("PO Box.")

    # Visa Information Fields
    passport_no = fields.Char("Passport No.")
    passport_issue_date = fields.Date("Passport Issue Date")
    passport_expiry_date = fields.Date("Passport Expiry Date")
    id_no = fields.Char("ID Card No.")
    id_issue_date = fields.Date("ID Issue Date")
    id_expiry_date = fields.Date("ID Expiry Date")

    @api.depends("brokerage_company_id")
    def _compute_brokerage_currency(self):
        for partner in self:
            partner.currency_id = (
                partner.sudo().brokerage_company_id.currency_id
                or self.env.company.currency_id
            )

    @api.depends("properties_ids")
    def _compute_properties_count(self):
        """Compute property count"""
        for rec in self:
            count = self.env["property.details"].search_count(
                [("landlord_id", "in", [rec.id])]
            )
            rec.properties_count = count

    def action_properties(self):
        """View house owner properties"""
        return {
            "type": "ir.actions.act_window",
            "name": "Properties",
            "res_model": "property.details",
            "domain": [("landlord_id", "=", self.id)],
            "context": {"default_landlord_id": self.id},
            "view_mode": "list,form",
            "target": "current",
        }
