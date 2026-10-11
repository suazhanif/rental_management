# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PropertyHandoverMaterial(models.Model):
    """Configurable master list of materials handed over on occupation
    (blankets, bedsheets, mattresses, etc.) along with their replacement cycle."""

    _name = "property.handover.material"
    _description = "Property Handover Material"
    _order = "sequence, id"

    name = fields.Char(string="Material", required=True, translate=True)
    sequence = fields.Integer(default=10)
    replacement_years = fields.Integer(
        string="Replacement Duration (Years)",
        required=True,
        default=1,
        help="Number of years after handover this material is due for replacement.",
    )
    active = fields.Boolean(default=True)
    note = fields.Char(string="Note")
