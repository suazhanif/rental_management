# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
"""Property Assignment — record-level access for Compounds, Buildings, Properties.

Adds the ``user_ids`` M2M field to ``property.project``,
``property.sub.project`` and ``property.details``.  Visibility is enforced
by ``security/property_assignment_rules.xml`` and the
``property_rental_officer`` group.  Managers (whose group no longer
implies ``property_rental_officer`` as of 3.4.0) are not subject to
those rules and see every record.

When an *officer* creates a new record, the creator is automatically
added to ``user_ids`` so they can see their own work.  When a *manager*
creates a record the field is left empty, so the record is
manager-only until someone assigns it.

The manager reassigns records by opening the form and editing
``user_ids`` directly — there is no bulk wizard in v1.
"""
from odoo import api, fields, models


def _augment_user_ids_for_officer(vals, env):
    """Add the current officer to ``user_ids`` in ``vals`` if not present.

    Used by the three ``create()`` overrides below.  When the caller is a
    manager, returns ``vals`` unchanged (the record stays unassigned and
    is therefore manager-only).
    """
    manager_group = env.ref(
        "rental_management.property_rental_manager", raise_if_not_found=False
    )
    user = env.user
    # Use ``has_group`` (which gracefully handles edge cases like a
    # freshly-created user record whose ``groups_id`` M2M isn't
    # populated yet) instead of poking ``user.groups_id`` directly.
    is_manager = bool(
        manager_group and user.has_group("rental_management.property_rental_manager")
    )
    if is_manager:
        return vals
    existing = set()
    for cmd in vals.get("user_ids", ()):
        if not isinstance(cmd, (list, tuple)):
            continue
        op = cmd[0]
        if op == 4 and len(cmd) >= 2:
            existing.add(cmd[1])
        elif op == 6 and len(cmd) >= 3:
            existing.update(cmd[2])
    if user.id not in existing:
        if "user_ids" in vals:
            vals["user_ids"] = list(vals["user_ids"]) + [(4, user.id)]
        else:
            vals["user_ids"] = [(4, user.id)]
    return vals


class PropertyProjectAssignment(models.Model):
    _inherit = "property.project"

    user_ids = fields.Many2many(
        "res.users",
        "property_project_user_rel",
        "project_id",
        "user_id",
        string="Assigned Officers",
        tracking=True,
        copy=False,
        domain=[("share", "=", False)],
        help="Officers responsible for this compound.  "
             "Leave empty to restrict visibility to managers only.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _augment_user_ids_for_officer(vals, self.env)
        return super().create(vals_list)


class PropertySubProjectAssignment(models.Model):
    _inherit = "property.sub.project"

    user_ids = fields.Many2many(
        "res.users",
        "property_sub_project_user_rel",
        "sub_project_id",
        "user_id",
        string="Assigned Officers",
        tracking=True,
        copy=False,
        domain=[("share", "=", False)],
        help="Officers responsible for this building.  "
             "Leave empty to restrict visibility to managers only.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _augment_user_ids_for_officer(vals, self.env)
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "user_ids" in vals:
            for rec in self:
                if rec.property_unit_ids:
                    rec.property_unit_ids.write(
                        {"user_ids": [(6, 0, rec.user_ids.ids)]}
                    )
        return res


class PropertyDetailsAssignment(models.Model):
    _inherit = "property.details"

    user_ids = fields.Many2many(
        "res.users",
        "property_details_user_rel",
        "property_id",
        "user_id",
        string="Assigned Officers",
        tracking=True,
        copy=False,
        domain=[("share", "=", False)],
        help="Officers responsible for this property.  "
             "Leave empty to restrict visibility to managers only.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _augment_user_ids_for_officer(vals, self.env)
        return super().create(vals_list)
