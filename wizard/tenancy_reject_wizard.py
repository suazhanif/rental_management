# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
"""Reject wizard for the rent-contract approval workflow.

A manager uses this wizard to reject a contract that is currently in
``pending_approval`` state.  The reason is mandatory — captured here and
copied to ``tenancy.details.rejection_reason`` along with the
``rejected_by`` / ``rejected_date`` audit fields.  On confirm the contract
is returned to ``new_contract`` (Draft) and an email is sent to the
submitter.
"""
import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TenancyRejectWizard(models.TransientModel):
    _name = "tenancy.reject.wizard"
    _description = "Reject Rent Contract Approval"

    tenancy_id = fields.Many2one(
        "tenancy.details",
        string="Contract",
        required=True,
        readonly=True,
    )
    tenancy_seq = fields.Char(
        related="tenancy_id.tenancy_seq",
        string="Contract Reference",
        readonly=True,
    )
    submitted_by = fields.Many2one(
        related="tenancy_id.submitted_by",
        string="Submitted By",
        readonly=True,
    )
    reason = fields.Text(
        string="Rejection Reason",
        required=True,
        help="Explain why this contract is being rejected.  The submitter "
        "will see this reason in the email and on the contract.",
    )

    def action_confirm_rejection(self):
        """Apply the rejection to the underlying tenancy record."""
        self.ensure_one()
        reason = (self.reason or "").strip()
        if not reason:
            raise ValidationError(
                _("A rejection reason is required. Please enter a reason.")
            )

        tenancy = self.tenancy_id.with_context(skip_activity_check=True)

        # State guard — protects against double-click and stale wizard state.
        if tenancy.contract_type != "pending_approval":
            raise ValidationError(
                _(
                    "This contract is no longer pending approval "
                    "(current state: %(state)s). The rejection cannot be applied.",
                    state=tenancy.contract_type,
                )
            )

        # Dismiss any open approval activities (best-effort, see also
        # ``TenancyDetails.action_approve``).
        try:
            tenancy.activity_feedback(["mail.mail_activity_data_todo"])
        except Exception:  # pylint: disable=broad-except
            _logger.warning(
                "Failed to clear approval activities for tenancy %s",
                tenancy.id,
                exc_info=True,
            )

        # Persist the rejection.
        tenancy.write(
            {
                "rejected_by": self.env.user.id,
                "rejected_date": fields.Datetime.now(),
                "rejection_reason": reason,
                "contract_type": "new_contract",
            }
        )

        # Audit note in the chatter.
        tenancy.message_post(
            body=_(
                "<b>Contract Rejected</b><br/>"
                "Rejected by <b>%(user)s</b> on %(date)s.<br/>"
                "<b>Reason:</b> %(reason)s",
                user=self.env.user.name,
                date=fields.Datetime.to_string(fields.Datetime.now()),
                reason=reason,
            ),
            subject=_("Rent Contract Rejected"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        # Email the submitter (if they have an email address).
        self._send_rejection_email(tenancy, reason)

        return {
            "type": "ir.actions.act_window",
            "name": _("Rent Contract"),
            "res_model": "tenancy.details",
            "res_id": tenancy.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _send_rejection_email(self, tenancy, reason):
        """Send the rejection email to the original submitter.

        The template's Jinja body references ``{{ object.rejection_reason }}``
        so we do not need to do any substitution here — the field has
        just been written.  We drive the recipient via ``recipient_ids``
        so the template's ``partner_to`` (set to ``False``) is honoured.
        The ``reason`` parameter is kept in the signature for symmetry
        with the approval helper and for the audit log.
        """
        template = self.env.ref(
            "rental_management.tenancy_approval_rejected_mail_template",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "tenancy_approval_rejected_mail_template missing — "
                "skipping rejection email for tenancy %s",
                tenancy.id,
            )
            return

        submitter_partner = tenancy.submitted_by.partner_id
        if not submitter_partner or not submitter_partner.email:
            _logger.warning(
                "Submitter %s has no email — skipping rejection email "
                "for tenancy %s",
                tenancy.submitted_by.id if tenancy.submitted_by else False,
                tenancy.id,
            )
            return

        template.send_mail(
            tenancy.id,
            force_send=True,
            email_values={"recipient_ids": [(4, submitter_partner.id)]},
        )
        # ``reason`` referenced for clarity in the audit log above and to
        # keep the helper signature symmetric with the approval flow.
        _ = reason
