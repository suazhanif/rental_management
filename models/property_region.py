# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PropertyRegion(models.Model):
    """Property Region"""

    _name = "property.region"
    _description = "Property Regions"

    name = fields.Char(string="Region")
    city_ids = fields.Many2many("property.res.city", string="Cities")
    project_count = fields.Integer(string="Project Count", compute="_compute_count")
    subproject_count = fields.Integer(
        string="Subproject Count", compute="_compute_count"
    )
    unit_count = fields.Integer(string="Units Count", compute="_compute_count")

    def _compute_count(self):
        """Compute Count"""
        for rec in self:
            rec.project_count = self.env["property.project"].search_count(
                [("region_id", "in", [rec.id])]
            )
            rec.subproject_count = self.env["property.sub.project"].search_count(
                [("region_id", "in", [rec.id])]
            )
            rec.unit_count = self.env["property.details"].search_count(
                [("region_id", "in", [rec.id])]
            )

    def action_view_project(self):
        """View project"""
        return {
            "name": "Projects",
            "type": "ir.actions.act_window",
            "domain": [("region_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.project",
            "target": "current",
        }

    def action_view_sub_project(self):
        """View Sub Project"""
        return {
            "name": "Sub Projects",
            "type": "ir.actions.act_window",
            "domain": [("region_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.sub.project",
            "target": "current",
        }

    def action_view_properties(self):
        """View properties"""
        return {
            "name": "Units",
            "type": "ir.actions.act_window",
            "domain": [("region_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.details",
            "target": "current",
        }
