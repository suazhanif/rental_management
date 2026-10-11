# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
"""Post-migration for ``rental_management`` 3.3.6.

The approval workflow introduces two new states
(``pending_approval`` and ``approved``) and gates
``action_active_contract`` on ``contract_type == 'approved'``.

Existing ``new_contract`` (Draft) records must therefore be transitioned
to ``approved`` so the existing activation flow keeps working for any
operator with a draft pipeline.

We deliberately do **not** stamp ``approved_by`` / ``approved_date`` —
the absence of a stamp on the form clearly signals "migrated, not
actually approved" for audit purposes.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

NEW_CONTRACT = "new_contract"
APPROVED = "approved"


def migrate(cr, version):
    """Upgrade hook — runs once per version bump."""
    if not version:
        # Fresh install — nothing to migrate.
        return

    _logger.info(
        "rent_contract 3.3.6 migration: transitioning existing "
        "new_contract records to 'approved' (no approver stamp)."
    )
    env = api.Environment(cr, SUPERUSER_ID, {})
    migrated = (
        env["tenancy.details"]
        .sudo()
        .search([("contract_type", "=", NEW_CONTRACT)])
        .write({"contract_type": APPROVED})
    )
    _logger.info(
        "rent_contract 3.3.6 migration: %d contract(s) moved from "
        "Draft to Approved.",
        migrated,
    )
