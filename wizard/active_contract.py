from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ActiveContract(models.Model):
    """Active Rent Contract"""

    _name = "active.contract"
    _description = "Active Contract"
    _rec_name = "type"

    type = fields.Selection(
        [
            ("automatic", "Auto Installment"),
            ("manual", "Manual Installment (List out all rent installment)"),
        ],
        default="automatic",
    )
    contract_id = fields.Many2one(comodel_name="tenancy.details")
    rent_unit = fields.Selection(related="contract_id.rent_unit")

    @api.model
    def default_get(self, fields_list):
        """Default get"""
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        contract_id = self.env["tenancy.details"].browse(active_id)
        res["contract_id"] = contract_id.id
        if contract_id.rent_unit == "Day":
            res["type"] = "manual"
        return res

    def action_create_contract(self):
        """Process activation of rent contract"""
        active_contract_check = self.check_current_active_contract_status()
        if active_contract_check:
            raise ValidationError(_(active_contract_check))
        active_id = self.env.context.get("active_id")
        tenancy_id = self.env["tenancy.details"].browse(active_id)
        if self.type == "automatic":
            tenancy_id.action_active_contract()
        if self.type == "manual":
            self._prepare_installment()
            self._process_post_installment()

    def _prepare_installment(self):
        """Prepare installment for rent manual installment type"""
        if self.contract_id.rent_unit == "Month":
            if self.contract_id.payment_term == "monthly":
                self.action_monthly_month_active()
            if self.contract_id.payment_term == "quarterly":
                self.action_quarterly_month_active()
            if self.contract_id.payment_term == "half_year":
                self.action_half_year_month_active()
        if self.contract_id.rent_unit == "Day":
            self._process_rent_installment_day()
        if self.contract_id.rent_unit == "Year":
            if self.contract_id.payment_term == "year":
                self.action_yearly_year()
        if self.contract_id.is_any_broker:
            self.contract_id.action_broker_invoice()

    def _process_post_installment(self):
        """Handle post installment process"""
        self.contract_id.write(
            {
                "type": "manual",
                "contract_type": "running_contract",
                "active_contract_state": True,
            }
        )
        self.contract_id.action_send_active_contract()

    def action_monthly_month_active(self):
        """Monthly payment term active contract"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        service = 0.0
        invoice_lines = []
        invoice_date = self.contract_id.invoice_start_date + relativedelta(months=1)
        if (
            self.contract_id.is_maintenance_service
            and self.contract_id.maintenance_service_invoice == "separate"
        ):
            self._process_separate_invoices(days=1, maintenance=True)
        if (
            self.contract_id.is_extra_service
            and self.contract_id.extra_service_invoice == "separate"
        ):
            self._process_separate_invoices(days=1, utility=True)
        for i in range(self.contract_id.month):
            if i == 0:
                invoice_lines.append(
                    (0, 0, self._prepare_invoice_line(type="installment"))
                )
                if (
                    self.contract_id.is_maintenance_service
                    and self.contract_id.maintenance_service_invoice == "merge"
                ):
                    invoice_lines.append(
                        (0, 0, self._prepare_invoice_line(type="maintenance"))
                    )
                if (
                    self.contract_id.is_extra_service
                    and self.contract_id.extra_service_invoice == "merge"
                ):
                    invoice_lines += self._prepare_service_invoice_line(qty=1)
                    service = sum(self.contract_id.extra_services_ids.mapped("price"))
                if (
                    self.contract_id.is_added_services
                    and self.contract_id.added_service_ids
                    and self.contract_id.added_service_invoice == "merge"
                ):
                    for line in self.contract_id.added_service_ids:
                        invoice_lines.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": line.service_id.id,
                                    "name": line.service_id.name,
                                    "quantity": 1,
                                    "price_unit": line.price,
                                },
                            )
                        )
                if (
                    self.contract_id.is_added_services
                    and self.contract_id.added_service_ids
                    and self.contract_id.added_service_invoice == "separate"
                ):
                    self._process_separate_added_services()

                invoice_id = (
                    self.env["account.move"]
                    .sudo()
                    .create(
                        {
                            "partner_id": self.contract_id.tenancy_id.id,
                            "move_type": "out_invoice",
                            "invoice_date": self.contract_id.invoice_start_date,
                            "invoice_line_ids": invoice_lines,
                            "tenancy_id": self.contract_id.id,
                        }
                    )
                )
                if invoice_post_type == "automatically":
                    invoice_id.action_post()
                self.env["rent.invoice"].create(
                    {
                        "tenancy_id": self.contract_id.id,
                        "type": "rent",
                        "invoice_date": self.contract_id.invoice_start_date,
                        "description": "First Rent",
                        "rent_invoice_id": invoice_id.id,
                        "amount": invoice_id.amount_total,
                        "rent_amount": self.contract_id.total_rent,
                        "service_amount": service,
                    }
                )
                self.contract_id._create_deposit_invoice()
            if not i == 0:
                self.env["rent.invoice"].create(
                    {
                        "tenancy_id": self.contract_id.id,
                        "type": "rent",
                        "invoice_date": invoice_date,
                        "description": "Installment of "
                        + self.contract_id.property_id.name,
                        "amount": self.contract_id.total_rent,
                        "rent_amount": self.contract_id.total_rent,
                    }
                )
                invoice_date = invoice_date + relativedelta(months=1)

    def action_quarterly_month_active(self):
        """Quarterly payment term active contract"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        service_amount = 0.0
        active_id = self.env.context.get("active_id")
        tenancy_id = self.env["tenancy.details"].browse(active_id)
        invoice_lines = []
        full_quarter = self.contract_id.month // 3
        reminder_quarter = self.contract_id.month % 3
        invoice_date = self.contract_id.invoice_start_date + relativedelta(months=3)
        # Separate Invoice
        if (
            self.contract_id.is_maintenance_service
            and self.contract_id.maintenance_service_invoice == "separate"
        ):
            self._process_separate_invoices(days=3, maintenance=True)
        if (
            self.contract_id.is_extra_service
            and self.contract_id.extra_service_invoice == "separate"
        ):
            self._process_separate_invoices(days=3, utility=True)
        if full_quarter >= 1:
            for i in range(full_quarter):
                if i == 0:
                    record = {
                        "product_id": tenancy_id.installment_item_id.id,
                        "name": "First Quarter Invoice of "
                        + tenancy_id.property_id.name,
                        "quantity": 1,
                        "price_unit": tenancy_id.total_rent * 3,
                        "tax_ids": (
                            tenancy_id.tax_ids.ids
                            if tenancy_id.instalment_tax
                            else False
                        ),
                    }
                    invoice_lines.append((0, 0, record))
                    if (
                        tenancy_id.is_maintenance_service
                        and self.contract_id.maintenance_service_invoice == "merge"
                    ):
                        invoice_lines.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": tenancy_id.maintenance_item_id.id,
                                    "name": "Maintenance of "
                                    + tenancy_id.property_id.name,
                                    "quantity": 3,
                                    "price_unit": tenancy_id.total_maintenance,
                                    "tax_ids": (
                                        tenancy_id.tax_ids.ids
                                        if tenancy_id.instalment_tax
                                        else False
                                    ),
                                },
                            )
                        )
                    if (
                        tenancy_id.is_extra_service
                        and self.contract_id.extra_service_invoice == "merge"
                    ):
                        for line in tenancy_id.extra_services_ids:
                            if line.service_type == "once":
                                service_amount = service_amount + line.price
                                service_invoice_record = {
                                    "product_id": line.service_id.id,
                                    "name": "Service Type : Once"
                                    + "\n"
                                    + "Service : "
                                    + str(line.service_id.name),
                                    "quantity": 1,
                                    "price_unit": line.price,
                                    "tax_ids": (
                                        tenancy_id.tax_ids.ids
                                        if tenancy_id.service_tax
                                        else False
                                    ),
                                }
                                invoice_lines.append((0, 0, service_invoice_record))
                            if line.service_type == "monthly":
                                service_amount = service_amount + line.price * 3
                                service_invoice_record = {
                                    "product_id": line.service_id.id,
                                    "name": "Service Type : Recurring"
                                    + "\n"
                                    + "Service : "
                                    + str(line.service_id.name),
                                    "quantity": 3,
                                    "price_unit": line.price,
                                    "tax_ids": (
                                        tenancy_id.tax_ids.ids
                                        if tenancy_id.service_tax
                                        else False
                                    ),
                                }
                                invoice_lines.append((0, 0, service_invoice_record))
                    if (
                        self.contract_id.is_added_services
                        and self.contract_id.added_service_ids
                        and self.contract_id.added_service_invoice == "merge"
                    ):
                        for line in self.contract_id.added_service_ids:
                            invoice_lines.append(
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": line.service_id.id,
                                        "name": line.service_id.name,
                                        "quantity": 1,
                                        "price_unit": line.price,
                                    },
                                )
                            )
                    if (
                        self.contract_id.is_added_services
                        and self.contract_id.added_service_ids
                        and self.contract_id.added_service_invoice == "separate"
                    ):
                        self._process_separate_added_services()

                    data = {
                        "partner_id": tenancy_id.tenancy_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": tenancy_id.invoice_start_date,
                        "invoice_line_ids": invoice_lines,
                    }
                    invoice_id = self.env["account.move"].sudo().create(data)
                    invoice_id.tenancy_id = tenancy_id.id
                    if invoice_post_type == "automatically":
                        invoice_id.action_post()
                    rent_invoice = {
                        "tenancy_id": tenancy_id.id,
                        "type": "rent",
                        "invoice_date": tenancy_id.invoice_start_date,
                        "description": "First Quarter Rent",
                        "rent_invoice_id": invoice_id.id,
                        "amount": invoice_id.amount_total,
                        "rent_amount": tenancy_id.total_rent * 3,
                        "service_amount": service_amount,
                    }
                    self.env["rent.invoice"].create(rent_invoice)
                    tenancy_id._create_deposit_invoice()
                if not i == 0:
                    rent_invoice = {
                        "tenancy_id": tenancy_id.id,
                        "type": "rent",
                        "invoice_date": invoice_date,
                        "description": "Installment of " + tenancy_id.property_id.name,
                        "amount": tenancy_id.total_rent * 3,
                        "rent_amount": tenancy_id.total_rent * 3,
                    }
                    self.env["rent.invoice"].create(rent_invoice)
                    invoice_date = invoice_date + relativedelta(months=3)

            if reminder_quarter > 0:
                rent_invoice_reminder = {
                    "tenancy_id": tenancy_id.id,
                    "type": "rent",
                    "invoice_date": invoice_date,
                    "description": "Installment of " + tenancy_id.property_id.name,
                    "amount": tenancy_id.total_rent * reminder_quarter,
                    "rent_amount": tenancy_id.total_rent * reminder_quarter,
                    "remain": reminder_quarter,
                }
                self.env["rent.invoice"].create(rent_invoice_reminder)

    def action_half_year_month_active(self):
        """
        Activates a half-year payment term for a rental contract.

        This method:
        - Processes separate invoices for maintenance and extra services if required.
        - Creates a combined invoice for the first 6-month period:
            - Includes rent, deposit (if any), maintenance, extra and added services.
        - Creates rent invoice records for each 6-month installment and any remaining months.
        - Posts invoices automatically if configured.

        Models used:
        - tenancy.details
        - account.move
        - rent.invoice
        """
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        service_amount = 0.0
        invoice_lines = []
        full_half_years = self.contract_id.month // 6
        remaining_months = self.contract_id.month % 6
        next_invoice_date = self.contract_id.invoice_start_date + relativedelta(
            months=6
        )
        if full_half_years >= 1:
            for installment_index in range(full_half_years):
                if installment_index == 0:
                    rent_invoice_line = {
                        "product_id": self.contract_id.installment_item_id.id,
                        "name": "First Half year invoice of "
                        + self.contract_id.property_id.name,
                        "quantity": 1,
                        "price_unit": self.contract_id.total_rent * 6,
                        "tax_ids": self.contract_id.tax_ids.ids
                        if self.contract_id.instalment_tax
                        else False,
                    }
                    invoice_lines.append((0, 0, rent_invoice_line))
                    # Append merged service lines (maintenance, extra, added)
                    service_amount += self._append_merged_service_lines(
                        self.contract_id, invoice_lines
                    )
                    # Handle separate added services
                    if (
                        self.contract_id.is_added_services
                        and self.contract_id.added_service_ids
                        and self.contract_id.added_service_invoice == "separate"
                    ):
                        self._process_separate_added_services()
                    invoice_vals = {
                        "partner_id": self.contract_id.tenancy_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": self.contract_id.invoice_start_date,
                        "invoice_line_ids": invoice_lines,
                    }
                    invoice = self.env["account.move"].sudo().create(invoice_vals)
                    invoice.tenancy_id = self.contract_id.id
                    if invoice_post_type == "automatically":
                        invoice.action_post()
                    rent_invoice_vals = {
                        "tenancy_id": self.contract_id.id,
                        "type": "rent",
                        "invoice_date": self.contract_id.invoice_start_date,
                        "description": "First Half Year Rent",
                        "rent_invoice_id": invoice.id,
                        "amount": invoice.amount_total,
                        "rent_amount": self.contract_id.total_rent * 6,
                        "service_amount": service_amount,
                    }
                    self.env["rent.invoice"].create(rent_invoice_vals)
                    self.contract_id._create_deposit_invoice()
                else:
                    rent_invoice_vals = {
                        "tenancy_id": self.contract_id.id,
                        "type": "rent",
                        "invoice_date": next_invoice_date,
                        "description": "Installment of "
                        + self.contract_id.property_id.name,
                        "amount": self.contract_id.total_rent * 6,
                        "rent_amount": self.contract_id.total_rent * 6,
                    }
                    self.env["rent.invoice"].create(rent_invoice_vals)
                    next_invoice_date += relativedelta(months=6)

            # Process separate invoices
            if (
                self.contract_id.is_maintenance_service
                and self.contract_id.maintenance_service_invoice == "separate"
            ):
                self._process_separate_invoices(days=1, maintenance=True)

            if (
                self.contract_id.is_extra_service
                and self.contract_id.extra_service_invoice == "separate"
            ):
                self._process_separate_invoices(days=1, utility=True)
            # Handle any remaining months
            if remaining_months > 0:
                rent_invoice_vals = {
                    "tenancy_id": self.contract_id.id,
                    "type": "rent",
                    "invoice_date": next_invoice_date,
                    "description": "Installment of "
                    + self.contract_id.property_id.name,
                    "amount": self.contract_id.total_rent * remaining_months,
                    "rent_amount": self.contract_id.total_rent * remaining_months,
                    "remain": remaining_months,
                }
                self.env["rent.invoice"].create(rent_invoice_vals)

    def _append_merged_service_lines(self, tenancy, invoice_lines):
        """Append merged service lines (maintenance, extra services, added services) to invoice."""
        total_service_amount = 0.0

        # Merged Maintenance
        if (
            tenancy.is_maintenance_service
            and self.contract_id.maintenance_service_invoice == "merge"
        ):
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": tenancy.maintenance_item_id.id,
                        "name": "Maintenance of " + tenancy.property_id.name,
                        "quantity": 1,
                        "price_unit": tenancy.total_maintenance,
                        "tax_ids": tenancy.tax_ids.ids
                        if tenancy.instalment_tax
                        else False,
                    },
                )
            )
        # Merged Extra Services
        if (
            tenancy.is_extra_service
            and self.contract_id.extra_service_invoice == "merge"
        ):
            for service in tenancy.extra_services_ids:
                line_vals = {
                    "product_id": service.service_id.id,
                    "name": f"Service Type : {'Once' if service.service_type == 'once' else 'Recurring'}\nService : {service.service_id.name}",
                    "quantity": 1,
                    "price_unit": service.price,
                    "tax_ids": tenancy.tax_ids.ids if tenancy.service_tax else False,
                }
                invoice_lines.append((0, 0, line_vals))
                total_service_amount += service.price
        # Merged Added Services
        if (
            self.contract_id.is_added_services
            and self.contract_id.added_service_ids
            and self.contract_id.added_service_invoice == "merge"
        ):
            for added_service in self.contract_id.added_service_ids:
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": added_service.service_id.id,
                            "name": added_service.service_id.name,
                            "quantity": 1,
                            "price_unit": added_service.price,
                        },
                    )
                )
                total_service_amount += added_service.price
        return total_service_amount

    def action_yearly_year(self):
        """Yearly Payment Term active contract"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        service_amount = 0
        active_id = self.env.context.get("active_id")
        tenancy_id = self.env["tenancy.details"].browse(active_id)
        invoice_lines = []
        year = tenancy_id.month
        if (
            self.contract_id.is_maintenance_service
            and self.contract_id.maintenance_service_invoice == "separate"
        ):
            self._process_separate_invoices(days=1, maintenance=True)
        if (
            self.contract_id.is_extra_service
            and self.contract_id.extra_service_invoice == "separate"
        ):
            self._process_separate_invoices(days=1, utility=True)
        invoice_date = tenancy_id.invoice_start_date + relativedelta(years=1)
        for i in range(year):
            if i == 0:
                invoice_lines.append(
                    (0, 0, self._prepare_invoice_line(type="installment"))
                )
                if (
                    tenancy_id.is_maintenance_service
                    and self.contract_id.maintenance_service_invoice == "merge"
                ):
                    invoice_lines.append(
                        (0, 0, self._prepare_invoice_line(type="maintenance"))
                    )
                if (
                    tenancy_id.is_extra_service
                    and self.contract_id.extra_service_invoice == "merge"
                ):
                    for line in tenancy_id.extra_services_ids:
                        if line.service_type == "once":
                            service_amount = service_amount + line.price
                            service_invoice_record = {
                                "product_id": line.service_id.id,
                                "name": "Service Type : Once"
                                + "\n"
                                + "Service : "
                                + str(line.service_id.name),
                                "quantity": 1,
                                "price_unit": line.price,
                                "tax_ids": (
                                    tenancy_id.tax_ids.ids
                                    if tenancy_id.service_tax
                                    else False
                                ),
                            }
                            invoice_lines.append((0, 0, service_invoice_record))
                        if line.service_type == "monthly":
                            service_amount = service_amount + (line.price * 12)
                            service_invoice_record = {
                                "product_id": line.service_id.id,
                                "name": "Service Type : Recurring"
                                + "\n"
                                + "Service : "
                                + str(line.service_id.name),
                                "quantity": 12,
                                "price_unit": line.price,
                                "tax_ids": (
                                    tenancy_id.tax_ids.ids
                                    if tenancy_id.service_tax
                                    else False
                                ),
                            }
                            invoice_lines.append((0, 0, service_invoice_record))
                if (
                    self.contract_id.is_added_services
                    and self.contract_id.added_service_ids
                    and self.contract_id.added_service_invoice == "merge"
                ):
                    for line in self.contract_id.added_service_ids:
                        invoice_lines.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": line.service_id.id,
                                    "name": line.service_id.name,
                                    "quantity": 1,
                                    "price_unit": line.price,
                                },
                            )
                        )
                if (
                    self.contract_id.is_added_services
                    and self.contract_id.added_service_ids
                    and self.contract_id.added_service_invoice == "separate"
                ):
                    self._process_separate_added_services()
                invoice_id = (
                    self.env["account.move"]
                    .sudo()
                    .create(
                        {
                            "partner_id": tenancy_id.tenancy_id.id,
                            "move_type": "out_invoice",
                            "invoice_date": tenancy_id.invoice_start_date,
                            "invoice_line_ids": invoice_lines,
                            "tenancy_id": self.contract_id.id,
                        }
                    )
                )
                if invoice_post_type == "automatically":
                    invoice_id.action_post()
                rent_invoice = {
                    "tenancy_id": tenancy_id.id,
                    "type": "rent",
                    "invoice_date": tenancy_id.invoice_start_date,
                    "description": "First Rent",
                    "rent_invoice_id": invoice_id.id,
                    "amount": invoice_id.amount_total,
                    "rent_amount": tenancy_id.total_rent,
                    "service_amount": service_amount,
                }
                self.env["rent.invoice"].create(rent_invoice)
                tenancy_id._create_deposit_invoice()
            if not i == 0:
                rent_invoice = {
                    "tenancy_id": tenancy_id.id,
                    "type": "rent",
                    "invoice_date": invoice_date,
                    "description": "Installment of " + tenancy_id.property_id.name,
                    "amount": tenancy_id.total_rent,
                    "rent_amount": tenancy_id.total_rent,
                }
                self.env["rent.invoice"].create(rent_invoice)
                invoice_date = invoice_date + relativedelta(years=1)

    def _process_rent_installment_day(self):
        """Process Rent Installment: Rent Unit Day"""
        self.contract_id.rent_invoice_ids.unlink()
        config_obj = self.env["ir.config_parameter"].sudo()
        invoice_post_type = config_obj.get_param("rental_management.invoice_post_type")
        total_days = (
            self.contract_id.total_days
            if self.contract_id.duration_type == "by_date"
            else self.contract_id.month
        )
        installment_count, full_installment_days, reminder_installment_days = (
            self.get_contract_installment_count(total_days=total_days)
        )
        invoice_date = self.contract_id.invoice_start_date
        last_invoice_date = None
        if installment_count > 0:
            for i in range(installment_count):
                description = (
                    f"Installment : {invoice_date} to"
                    f" {invoice_date + relativedelta(days=(full_installment_days - 1))}"
                )
                self.env["rent.invoice"].create(
                    {
                        "tenancy_id": self.contract_id.id,
                        "type": "rent",
                        "invoice_date": invoice_date,
                        "description": (
                            description
                            if self.contract_id.payment_term != "daily"
                            else f"Installment {invoice_date}"
                        ),
                        "amount": self.contract_id.total_rent * full_installment_days,
                        "rent_amount": self.contract_id.total_rent
                        * full_installment_days,
                        "service_days": full_installment_days,
                    }
                )
                last_invoice_date = invoice_date + relativedelta(
                    days=(full_installment_days - 1)
                )
                invoice_date += relativedelta(days=(full_installment_days))
        if reminder_installment_days > 0:
            reminder_invoice_date = (
                self.contract_id.invoice_start_date
                if installment_count == 0
                else last_invoice_date
            )
            description = (
                f"Installment : {reminder_invoice_date} to {self.contract_id.end_date}"
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.contract_id.id,
                    "type": "rent",
                    "invoice_date": reminder_invoice_date,
                    "description": (
                        description
                        if self.contract_id.payment_term != "daily"
                        else f"Installment {reminder_invoice_date}"
                    ),
                    "amount": self.contract_id.total_rent * reminder_installment_days,
                    "rent_amount": self.contract_id.total_rent
                    * reminder_installment_days,
                    "service_days": reminder_installment_days,
                }
            )
        first_rent_invoice_line_id = self.contract_id.rent_invoice_ids[0]
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": self.contract_id.installment_item_id.id,
                    "name": first_rent_invoice_line_id.description,
                    "quantity": 1,
                    "price_unit": first_rent_invoice_line_id.amount,
                    "tax_ids": self.contract_id.tax_ids.ids
                    if self.contract_id.instalment_tax
                    else False,
                },
            )
        ]
        if (
            self.contract_id.is_maintenance_service
            and self.contract_id.maintenance_service_invoice == "merge"
        ):
            maintenance_amount = 0.0
            if self.contract_id.maintenance_rent_type == "once":
                maintenance_amount = self.contract_id.total_maintenance
            else:
                if installment_count > 0:
                    maintenance_amount = (
                        self.contract_id.total_maintenance * full_installment_days
                    )
                else:
                    maintenance_amount = (
                        self.contract_id.total_maintenance * reminder_installment_days
                    )
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": self.contract_id.maintenance_item_id.id,
                        "name": f"Maintenance of {self.contract_id.property_id.name}",
                        "price_unit": maintenance_amount,
                        "quantity": 1,
                        "tax_ids": False,
                    },
                )
            )
        if (
            self.contract_id.is_extra_service
            and self.contract_id.extra_service_invoice == "merge"
        ):
            for line in self.contract_id.extra_services_ids:
                service_type = "Once" if line.service_type == "once" else "Recurring"
                service_amount = 0.0
                if line.service_type == "once":
                    service_amount = line.price
                else:
                    if installment_count > 0:
                        service_amount = line.price * full_installment_days
                    else:
                        service_amount = line.price * reminder_installment_days
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": f"Service Type : {service_type} - {line.service_id.name}",
                            "quantity": 1,
                            "price_unit": service_amount,
                            "tax_ids": self.contract_id.tax_ids.ids
                            if self.contract_id.service_tax
                            else False,
                        },
                    )
                )
        if (
            self.contract_id.is_added_services
            and self.contract_id.added_service_ids
            and self.contract_id.added_service_invoice == "merge"
        ):
            for line in self.contract_id.added_service_ids:
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": line.service_id.name,
                            "quantity": 1,
                            "price_unit": line.price,
                        },
                    )
                )
        if (
            self.contract_id.is_added_services
            and self.contract_id.added_service_ids
            and self.contract_id.added_service_invoice == "separate"
        ):
            self._process_separate_added_services()
        # Create First Invoice
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.contract_id.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.contract_id.invoice_start_date,
                    "invoice_line_ids": invoice_lines,
                    "tenancy_id": self.contract_id.id,
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        first_rent_invoice_line_id.amount = invoice_id.amount_total
        first_rent_invoice_line_id.rent_invoice_id = invoice_id.id
        # Separate Deposit Invoice
        self.contract_id._create_deposit_invoice()
        # Separate Invoice : Maintenance and Service
        if (
            self.contract_id.is_maintenance_service
            and self.contract_id.maintenance_service_invoice == "separate"
        ):
            self._process_separate_invoices(
                days=(
                    full_installment_days
                    if full_installment_days != 0
                    else reminder_installment_days
                ),
                maintenance=True,
            )
        if (
            self.contract_id.is_extra_service
            and self.contract_id.extra_service_invoice == "separate"
        ):
            self._process_separate_invoices(
                days=(
                    full_installment_days
                    if full_installment_days != 0
                    else reminder_installment_days
                ),
                utility=True,
            )

    def _create_invoice_line(self, product_id, name, price_unit, tax_ids):
        """Create Invoice Lines"""
        return {
            "product_id": product_id,
            "name": name,
            "quantity": 1,
            "price_unit": price_unit,
            "tax_ids": tax_ids,
        }

    def _prepare_service_invoice_line(self, qty):
        """Prepare Service Line"""
        invoice_lines = []
        for line in self.contract_id.extra_services_ids:
            service_type = "Once" if line.service_type == "once" else "Recurring"
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.service_id.id,
                        "name": f"Service Type : {service_type} - {line.service_id.name}",
                        "quantity": qty,
                        "price_unit": line.price,
                        "tax_ids": self.contract_id.tax_ids.ids
                        if self.contract_id.service_tax
                        else False,
                    },
                )
            )
        return invoice_lines

    def _prepare_invoice_line(self, type):
        """Prepare Invoice Line"""
        type_mapping = {
            "installment": {
                "product_id": self.contract_id.installment_item_id.id,
                "name": f"First Invoice of {self.contract_id.property_id.name}",
                "price_unit": self.contract_id.total_rent,
                "tax_ids": self.contract_id.tax_ids.ids
                if self.contract_id.instalment_tax
                else False,
            },
            "maintenance": {
                "product_id": self.contract_id.maintenance_item_id.id,
                "name": f"Maintenance of {self.contract_id.property_id.name}",
                "price_unit": self.contract_id.total_maintenance,
            },
        }

        if type in type_mapping:
            invoice_line = type_mapping[type]
            invoice_line.update({"quantity": 1})
            return invoice_line

    def check_current_active_contract_status(self):
        active_id = self.env.context.get("active_id")
        tenancy_id = self.env["tenancy.details"].browse(active_id)
        contracts = self.env["tenancy.details"].search(
            [
                ("start_date", "<=", tenancy_id.end_date),
                ("end_date", ">", tenancy_id.start_date),
                ("property_id", "=", tenancy_id.property_id.id),
                ("contract_type", "=", "running_contract"),
            ]
        )
        if contracts:
            return "Some contracts are active for this time period. Please choose a different contract period"
        return ""

    def _get_config_days(self):
        """Get config days"""
        config_obj = self.env["ir.config_parameter"].sudo()
        config_month_days = config_obj.get_param("rental_management.month_days")
        config_quarter_days = config_obj.get_param("rental_management.quarter_days")
        config_year_days = config_obj.get_param("rental_management.year_days")
        config_half_year_days = config_obj.get_param("rental_management.half_year_days")
        month_days = int(config_month_days) if config_month_days else 30
        quarter_days = int(config_quarter_days) if config_quarter_days else 90
        year_days = int(config_year_days) if config_year_days else 365
        half_year_days = int(config_half_year_days) if config_half_year_days else 183
        return month_days, quarter_days, year_days, half_year_days

    def get_contract_installment_count(self, total_days):
        """Retrieve Installment Count"""
        payment_term_days = {
            "monthly": self._get_config_days()[0],
            "quarterly": self._get_config_days()[1],
            "year": self._get_config_days()[2],
            "half_year": self._get_config_days()[3],
            "daily": 1,
        }

        term = self.contract_id.payment_term
        installment_count, full_installment_days, remainder_installment_days = 0, 0, 0

        if term in payment_term_days:
            term_days = payment_term_days[term]

            if term == "daily":
                # Special case for daily payments
                installment_count = total_days
                full_installment_days = 1
            else:
                # General case for monthly, quarterly, yearly
                if total_days < term_days:
                    remainder_installment_days = total_days
                elif total_days == term_days:
                    installment_count = 1
                    full_installment_days = term_days
                else:
                    installment_count = total_days // term_days
                    full_installment_days = term_days
                    remainder_installment_days = total_days % term_days

        return installment_count, full_installment_days, remainder_installment_days

    def _process_separate_added_services(self):
        """Process sperate added services"""
        invoice_lines = []
        for data in self.contract_id.added_service_ids:
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": data.service_id.id,
                        "name": data.service_id.name,
                        "quantity": 1,
                        "price_unit": data.price,
                    },
                )
            )
        if invoice_lines:
            invoice_id = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "partner_id": self.contract_id.tenancy_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": self.contract_id.invoice_start_date,
                        "invoice_line_ids": invoice_lines,
                        "tenancy_id": self.contract_id.id,
                    }
                )
            )
            self.contract_id.added_service_ids.write({"invoice_id": invoice_id.id})

    def _process_separate_invoices(self, days, maintenance=None, utility=None):
        """Process Utility and Maintenance Separate Invoices"""
        if maintenance:
            maintenance_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.contract_id.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.contract_id.invoice_start_date,
                    "tenancy_id": self.contract_id.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.contract_id.maintenance_item_id.id,
                                "name": "Maintenance of "
                                + self.contract_id.property_id.name,
                                "quantity": 1
                                if self.contract_id.maintenance_rent_type == "once"
                                else days,
                                "price_unit": self.contract_id.total_maintenance,
                            },
                        )
                    ],
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.contract_id.id,
                    "type": "maintenance",
                    "invoice_date": self.contract_id.invoice_start_date,
                    "amount": maintenance_invoice_id.amount_total,
                    "description": "Maintenance of "
                    + self.contract_id.property_id.name,
                    "rent_invoice_id": maintenance_invoice_id.id,
                }
            )
        if utility:
            service_invoice_lines = []
            for line in self.contract_id.extra_services_ids:
                service_type = "Once" if line.service_type == "once" else "Recurring"
                service_invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": f"Service Type : {service_type} - {line.service_id.name}",
                            "quantity": 1 if line.service_type == "once" else days,
                            "price_unit": line.price,
                            "tax_ids": self.contract_id.tax_ids.ids
                            if self.contract_id.service_tax
                            else False,
                        },
                    )
                )
            service_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.contract_id.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.contract_id.invoice_start_date,
                    "tenancy_id": self.contract_id.id,
                    "invoice_line_ids": service_invoice_lines,
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.contract_id.id,
                    "type": "other",
                    "invoice_date": self.contract_id.invoice_start_date,
                    "amount": service_invoice_id.amount_total,
                    "description": "Utility Services",
                    "rent_invoice_id": service_invoice_id.id,
                }
            )
