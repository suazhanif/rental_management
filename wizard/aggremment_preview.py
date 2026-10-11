# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models


class AgreementPreview(models.TransientModel):
    """Agreement Preview"""

    _name = "agreement.preview"
    _description = "Agreement Preview"

    agreement_id = fields.Many2one("agreement.template", string="Agreement")
    body = fields.Html(string="Preview", compute="_compute_preview")

    @api.model
    def default_get(self, fields_list):
        """Default get"""
        res = super(AgreementPreview, self).default_get(fields_list)
        active_id = self.env.context.get("active_id")
        res["agreement_id"] = active_id
        return res

    @api.depends("agreement_id")
    def _compute_preview(self):
        """Compute agreement preview"""
        for rec in self:
            if rec.agreement_id.template_variable_ids:
                body = rec.agreement_id.agreement
                variable_dict = {}
                body_var = set(re.findall(r"{{[1-9][0-9]*}}", body or ""))
                for var in rec.agreement_id.template_variable_ids:
                    variable_dict[var.name] = var.demo if var.demo else ""
                for data in body_var:
                    body = body.replace(data, variable_dict.get(data))
                rec.body = body
            else:
                rec.body = ""
