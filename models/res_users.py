# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
"""Adds assigned-property counts to ``res.users``.

First ``_inherit = "res.users"`` in this codebase.  Three computed
Integer fields drive the smart buttons on the user form (see
``views/res_users_view.xml``).

Counts respect the record rules of the property models so an officer
sees only their own assignments.  Managers see the full count for any
user because the officer-scoped rules do not apply to them.
"""
from odoo import _, api, fields, models


class ResUsersPropertyAssignment(models.Model):
    _inherit = "res.users"

    assigned_compound_count = fields.Integer(
        compute="_compute_assigned_counts",
        string="Assigned Compounds",
    )
    assigned_building_count = fields.Integer(
        compute="_compute_assigned_counts",
        string="Assigned Buildings",
    )
    assigned_property_count = fields.Integer(
        compute="_compute_assigned_counts",
        string="Assigned Properties",
    )

    def _compute_assigned_counts(self):
        """Compute the 3 counts in a single pass per user.

        We deliberately do NOT use ``sudo()`` — the count must respect
        the record rules.  An officer sees their own assignments; a
        manager sees the full count for any user.
        """
        Compound = self.env["property.project"]
        Building = self.env["property.sub.project"]
        Property_ = self.env["property.details"]
        for user in self:
            user.assigned_compound_count = Compound.search_count(
                [("user_ids", "in", user.id)]
            )
            user.assigned_building_count = Building.search_count(
                [("user_ids", "in", user.id)]
            )
            user.assigned_property_count = Property_.search_count(
                [("user_ids", "in", user.id)]
            )

    def action_view_assigned_compounds(self):
        """Open the list of compounds assigned to this user."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assigned Compounds"),
            "res_model": "property.project",
            "view_mode": "tree,form",
            "domain": [("user_ids", "in", self.id)],
            "context": {"default_user_ids": [(4, self.id)]},
        }

    def action_view_assigned_buildings(self):
        """Open the list of buildings assigned to this user."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assigned Buildings"),
            "res_model": "property.sub.project",
            "view_mode": "tree,form",
            "domain": [("user_ids", "in", self.id)],
            "context": {"default_user_ids": [(4, self.id)]},
        }

    def action_view_assigned_properties(self):
        """Open the list of properties assigned to this user."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assigned Properties"),
            "res_model": "property.details",
            "view_mode": "tree,form",
            "domain": [("user_ids", "in", self.id)],
            "context": {"default_user_ids": [(4, self.id)]},
        }
