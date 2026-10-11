# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
"""Rent Contract Approval Workflow — fields and helpers.

Adds the approval audit fields to ``tenancy.details`` and a single
``_get_rental_manager_partners`` helper used by the submit/approve/reject
actions defined in :mod:`rental_management.models.rent_contract`.
"""
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TenancyDetailsApproval(models.Model):
    """Adds approval workflow fields to tenancy.details.

    The new state values (``pending_approval``, ``approved``) and the
    action methods live on the base :class:`tenancy.details` model in
    ``rent_contract.py`` because they depend on the Selection field and
    the existing ``action_active_contract`` flow.  This file is
    intentionally field-only to keep the new workflow isolated from the
    2,400-line base model — same pattern as
    :class:`occupy_details_dual_approval.OccupyDetailsDualApproval`.
    """

    _inherit = "tenancy.details"

    # --------------------------------------------------------------- #
    #  Audit fields — all readonly, all ``tracking=True`` for chatter  #
    # --------------------------------------------------------------- #
    submitted_by = fields.Many2one(
        "res.users",
        string="Submitted By",
        readonly=True,
        copy=False,
        tracking=True,
        help="Staff user who submitted this contract for manager approval.",
    )
    submitted_date = fields.Datetime(
        string="Submitted On",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        copy=False,
        tracking=True,
        help="Manager who approved the contract.  Empty for contracts that "
        "were migrated from Draft to Approved by the post-migration script.",
    )
    approved_date = fields.Datetime(
        string="Approved On",
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejected_by = fields.Many2one(
        "res.users",
        string="Rejected By",
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejected_date = fields.Datetime(
        string="Rejected On",
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        copy=False,
        tracking=True,
        help="Mandatory reason captured when a manager rejects the contract. "
        "The contract is returned to Draft and the user may edit and resubmit.",
    )

    # --------------------------------------------------------------- #
    #  Helpers                                                        #
    # --------------------------------------------------------------- #
    def _get_rental_manager_users(self):
        """Return ``res.users`` records in the ``property_rental_manager`` group.

        :raises UserError: if the group cannot be located (mis-installed).
        :returns: ``res.users`` recordset (possibly empty).
        """
        self.ensure_one()
        group = self.env.ref(
            "rental_management.property_rental_manager", raise_if_not_found=False
        )
        if not group:
            raise UserError(
                _(
                    "The Rental Manager security group is missing. "
                    "Please contact your administrator."
                )
            )
        # Odoo 19: ``res.groups`` exposes ``user_ids`` (a Many2many to
        # ``res.users``).  The legacy ``users`` attribute no longer exists.
        return group.user_ids

    def _get_rental_manager_partners(self):
        """Return partners of users in the ``property_rental_manager`` group.

        Users without a partner (shouldn't happen) are filtered out.  An
        empty recordset means no manager is configured — the caller is
        expected to raise a user-visible error.
        """
        users = self._get_rental_manager_users()
        return users.mapped("partner_id").filtered("email")
