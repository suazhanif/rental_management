import datetime

from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_rent_contract")
class TestRentContract(CreateRentalData):
    """Unit tests to validate tenancy contract creation, actions, and scheduler behaviours."""

    @classmethod
    def setUpClass(cls):
        """Prepare demo properties, products, and multiple tenancy contracts for test scenarios."""
        super().setUpClass()
        cls.property = cls._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "service one",
                "is_extra_service_product": True,
                "type": "consu",
                "lst_price": 10,
                "standard_price": 10,
            }
        )
        cls.contract_wizard = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.property.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": "2025-03-01",
                "payment_term": "monthly",
                "duration_id": cls.duration.id,
                "total_rent": 10000,
                "property_id": cls.property.id,
            },
        )
        cls.contract_wizard_action = cls.contract_wizard.contract_action()
        cls.contract_one = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action["res_id"]
        )
        cls.property_two = cls._create_units(
            name="Property One",
            property_seq="002",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
            rent_unit="Month",
        )
        cls.contract_wizard_two = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.property_two.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": "2025-03-01",
                "payment_term": "monthly",
                "duration_id": cls.duration.id,
                "duration_type": "by_date",
                "duration_end_date": "2026-03-01",
                "broker_commission": 1000,
                "commission_type": "f",
                "is_any_broker": True,
                "total_rent": 10000,
                "property_id": cls.property_two.id,
                "broker_id": cls.broker_one.id,
                "instalment_tax": True,
                "tax_ids": cls.tax,
                "rent_unit": "Month",
            },
        )
        cls.contract_wizard_action_two = cls.contract_wizard_two.contract_action()
        cls.contract_two = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action_two["res_id"]
        )

        cls.property_three = cls._create_units(
            name="Property One",
            property_seq="003",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
            rent_unit="Day",
        )
        cls.contract_wizard_three = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.property_three.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": "2025-03-31",
                "payment_term": "daily",
                "duration_type": "by_date",
                "duration_end_date": "2025-04-01",
                "broker_commission": 1000,
                "commission_type": "f",
                "is_any_broker": True,
                "total_rent": 10,
                "property_id": cls.property_three.id,
                "broker_id": cls.broker_one.id,
                "instalment_tax": True,
                "tax_ids": cls.tax,
                "rent_unit": "Day",
                "is_extra_service": True,
                "extra_service_invoice": "merge",
            },
        )
        cls.contract_wizard_action_three = cls.contract_wizard_three.contract_action()
        cls.contract_three = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action_three["res_id"]
        )

        cls.property_four = cls._create_units(
            name="Property One",
            property_seq="002",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
            rent_unit="Month",
            is_maintenance_service=True,
            maintenance_rent_type="recurring",
            maintenance_type="fixed",
            total_maintenance=10,
        )
        cls.property_four.is_extra_service = True
        cls.property_four.extra_service_ids = [
            (
                0,
                0,
                {"service_id": cls.product.id, "service_type": "monthly", "price": 10},
            )
        ]
        cls.contract_wizard_four = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.property_four.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": (
                    datetime.datetime.today().date() - relativedelta(months=1)
                ),
                "payment_term": "monthly",
                "duration_id": cls.duration.id,
                "duration_type": "by_duration",
                "broker_commission": 1000,
                "commission_type": "f",
                "is_any_broker": True,
                "total_rent": 10000,
                "property_id": cls.property_four.id,
                "broker_id": cls.broker_one.id,
                "instalment_tax": True,
                "tax_ids": cls.tax,
                "rent_unit": "Month",
                "is_any_maintenance": True,
                "maintenance_service_invoice": "merge",
                "extra_service_invoice": "merge",
            },
        )
        cls.contract_wizard_action_four = cls.contract_wizard_four.contract_action()
        cls.contract_four = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action_four["res_id"]
        )

        cls.property_five = cls._create_units(
            name="Property One",
            property_seq="002",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
            rent_unit="Month",
            is_maintenance_service=True,
            maintenance_rent_type="recurring",
            maintenance_type="fixed",
            total_maintenance=10,
        )
        cls.property_five.is_extra_service = True
        cls.property_five.extra_service_ids = [
            (
                0,
                0,
                {"service_id": cls.product.id, "service_type": "monthly", "price": 10},
            )
        ]
        cls.contract_wizard_five = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.property_five.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": (
                    datetime.datetime.today().date() - relativedelta(months=3)
                ),
                "payment_term": "quarterly",
                "duration_id": cls.duration.id,
                "duration_type": "by_duration",
                "broker_commission": 1000,
                "commission_type": "f",
                "is_any_broker": True,
                "total_rent": 10000,
                "property_id": cls.property_five.id,
                "broker_id": cls.broker_one.id,
                "instalment_tax": True,
                "tax_ids": cls.tax,
                "rent_unit": "Month",
                "is_any_maintenance": True,
                "maintenance_service_invoice": "merge",
                "extra_service_invoice": "merge",
            },
        )
        cls.contract_wizard_action_five = cls.contract_wizard_five.contract_action()
        cls.contract_five = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action_five["res_id"]
        )

        cls.property_six = cls._create_units(
            name="Property One",
            property_seq="002",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
            rent_unit="Month",
            is_maintenance_service=True,
            maintenance_rent_type="recurring",
            maintenance_type="fixed",
            total_maintenance=10,
        )
        cls.property_six.is_extra_service = True
        cls.property_six.extra_service_ids = [
            (
                0,
                0,
                {"service_id": cls.product.id, "service_type": "monthly", "price": 10},
            )
        ]
        cls.contract_wizard_six = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.property_six.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": (
                    datetime.datetime.today().date() - relativedelta(years=1)
                ),
                "payment_term": "year",
                "duration_id": cls.duration_year.id,
                "duration_type": "by_duration",
                "broker_commission": 1000,
                "commission_type": "f",
                "is_any_broker": True,
                "total_rent": 10000,
                "property_id": cls.property_six.id,
                "broker_id": cls.broker_one.id,
                "instalment_tax": True,
                "tax_ids": cls.tax,
                "rent_unit": "Year",
                "is_any_maintenance": True,
                "maintenance_service_invoice": "merge",
                "extra_service_invoice": "merge",
            },
        )
        cls.contract_wizard_action_six = cls.contract_wizard_six.contract_action()
        cls.contract_six = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action_six["res_id"]
        )

    def test_create(self):
        """Verify tenancy contract is created with correct start date, duration and total rent."""
        self.assertTrue(self.contract_one)
        self.assertEqual(
            self.contract_one.start_date,
            datetime.datetime.strptime("2025-03-01", "%Y-%m-%d").date(),
        )
        self.assertEqual(self.contract_one.duration_id.id, self.duration.id)
        self.assertEqual(self.contract_one.total_rent, 10000)

    def test_unlink(self):
        """Check that deleting a contract resets the related property stage to draft."""
        self.contract_one.unlink()
        self.assertEqual(self.property.stage, "draft")

    def test_check_end_date(self):
        """Ensure ValidationError is raised when end date is before start date."""
        with self.assertRaises(ValidationError):
            contract_wizard = self._create_contract_wizard(
                active_model="property.details",
                active_id=self.property.id,
                data={
                    "customer_id": self.customer_one.id,
                    "start_date": "2025-03-01",
                    "payment_term": "monthly",
                    "duration_id": self.duration.id,
                    "duration_type": "by_date",
                    "duration_end_date": "2025-01-01",
                },
            )
            contract_wizard_action = contract_wizard.contract_action()
            self.env["tenancy.details"].browse(contract_wizard_action["res_id"])

    def test_unlink_property_sub_project(self):
        """Validate that running contracts cannot be deleted."""
        self.contract_one.contract_type = "running_contract"
        with self.assertRaises(ValidationError):
            self.contract_one.unlink()

    def test_write(self):
        """Confirm payment term validation for a given rent unit when writing to contract."""
        valid_payment_terms = {
            "Day": ["Monthly", "Quarterly", "Year", "Daily"],
            "Month": ["Monthly", "Quarterly"],
            "Year": ["Year"],
        }
        self.contract_one.rent_unit = "Month"
        message = (
            "For Rent Unit '"
            + self.contract_one.rent_unit
            + "', Payment Term should be one of "
            + ", ".join(valid_payment_terms[self.contract_one.rent_unit])
        )
        with self.assertRaisesRegex(ValidationError, message):
            self.contract_one.write({"payment_term": "daily"})

    def test_compute_methods(self):
        """Test computed fields: end date, broker commission, days left, invoices, bills,
        maintenance requests, total amounts, margin, rent unit, contract period availability
        and duration IDs."""
        self.contract_two._compute_end_date()
        self.assertEqual(
            self.contract_two.end_date,
            datetime.datetime.strptime("2026-03-01", "%Y-%m-%d").date(),
        )

        #  _search_end_date ----------------------------------------------------

        domain = self.contract_one._search_end_date(
            "=", datetime.datetime.strptime("2026-03-01", "%Y-%m-%d").date()
        )
        value = self.env["tenancy.details"].search(domain)
        self.assertEqual(value.id, self.contract_two.id)

        # _compute_broker_commission -------------------------------------------

        self.contract_two.rent_type = "once"
        self.contract_two._compute_broker_commission()
        self.assertEqual(self.contract_two.commission, 1000)
        self.contract_two.is_any_broker = True
        self.contract_two.commission_type = "p"
        self.contract_two.rent_type = "e_rent"
        self.contract_two.broker_commission_percentage = 10
        self.contract_two._compute_broker_commission()
        self.assertEqual(self.contract_two.commission, 10000)

        # compute_days_left ----------------------------------------------------

        self.contract_two.contract_type = "running_contract"
        self.contract_two.compute_days_left()
        self.assertEqual(
            self.contract_two.days_left,
            366
            + (
                datetime.datetime.strptime("2025-03-01", "%Y-%m-%d")
                - datetime.datetime.today()
            ).days,
        )

        # _compute_total_days ---------------------------------------------------

        self.contract_two._compute_total_days()
        self.assertEqual(self.contract_two.total_days, 366)

        # _compute_tenancy_calculation ------------------------------------------

        self.contract_two.contract_type = "new_contract"
        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_two.id,
            type="manual",
            contract_id=self.contract_two.id,
            rent_unit=self.contract_two.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(len(self.contract_two.rent_invoice_ids), 10)
        for rec in self.contract_two.rent_invoice_ids:
            if rec.rent_invoice_id:
                rec.rent_invoice_id.action_post()
            else:
                rec.action_create_invoice()
                rec.rent_invoice_id.action_post()
            self.payment_wizard = (
                self.env["account.payment.register"]
                .with_context(
                    active_model="account.move",
                    active_ids=rec.rent_invoice_id.id,
                )
                .create(
                    {
                        "amount": 5500,
                        "journal_id": self.journal_bank.id,
                        "payment_date": "2025-03-21",
                        "currency_id": self.company_currency.id,
                        "payment_method_line_id": self.journal_bank.inbound_payment_method_line_ids[
                            0
                        ].id,
                    }
                )
            )
            self.payment_wizard.action_create_payments()
            self.assertEqual(rec.rent_invoice_id.amount_residual, 5500)

        self.contract_two._compute_tenancy_calculation()
        self.assertEqual(self.contract_two.total_amount, 110000)
        self.assertEqual(self.contract_two.total_tenancy, 100000)
        self.assertEqual(self.contract_two.tax_amount, 10000)
        self.assertEqual(self.contract_two.paid_tenancy, 55000.0)
        self.assertEqual(self.contract_two.remain_tenancy, 55000.0)

        # _compute_invoice_count -----------------------------------------------

        self.contract_two._compute_invoice_count()
        self.assertEqual(self.contract_two.invoice_count, 10)

        # _compute_total_bill_amount -------------------------------------------

        wizard = self._create_property_payment_wizard(
            active_id=self.contract_two.id,
            tenancy_id=self.contract_two.id,
            bill_type="Bill",
            description="Bill",
            amount=100,
            tax_ids=self.tax,
            vendor_id=self.customer_one.id,
            invoice_date="2025-03-31",
        )
        wizard.property_bill_action()
        for rec in self.contract_two.rent_bill_ids:
            rec.rent_bill_id.action_post()
            self.payment_wizard = (
                self.env["account.payment.register"]
                .with_context(
                    active_model="account.move", active_ids=rec.rent_bill_id.id
                )
                .create(
                    {
                        "amount": 55,
                        "journal_id": self.journal_bank.id,
                        "payment_date": "2025-03-21",
                        "currency_id": self.company_currency.id,
                        "payment_method_line_id": self.journal_bank.inbound_payment_method_line_ids[
                            0
                        ].id,
                    }
                )
            )
            self.payment_wizard.action_create_payments()
        self.contract_two._compute_total_bill_amount()
        self.assertEqual(self.contract_two.total_bill_amount, 100)
        self.assertEqual(self.contract_two.paid_bill_amount, 0)
        self.assertEqual(self.contract_two.remaining_bill_amount, 100)

        # _compute_maintenance_request_count -----------------------------------

        self.product_template = self.env["product.template"].create({"name": "Product"})
        self.maintenance_team = self.env["maintenance.team"].create(
            {
                "name": "Team One",
                "member_ids": [
                    (0, 0, {"name": "Team Member One", "login": "team_member_one"}),
                    (0, 0, {"name": "Team Member Two", "login": "team_member_two"}),
                ],
            }
        )
        count = 0
        while True:
            if count == 5:
                break
            maintenance_wizard = self._create_maintenance_wizard(
                active_id=self.contract_two.id,
                name="Maintenence Request",
                property_id=self.property.id,
                maintenance_type_id=self.product_template.id,
                maintenance_team_id=self.maintenance_team.id,
                rent_contract_id=self.contract_two.id,
                is_renting_contract_maintenance=True,
            )
            maintenance_wizard.maintenance_request()

            count += 1

        self.contract_two._compute_maintenance_request_count()
        self.assertEqual(self.contract_two.maintenance_request_count, 5)

        # _compute_total_amount ------------------------------------------------

        self.contract_two._compute_total_amount()
        invoice_amount = 0.0
        invoice_residual = 0.0
        bill_amount = 0.0
        bill_residual = 0.0
        invoices = (
            self.env["account.move"]
            .sudo()
            .search(
                [
                    ("tenancy_id", "=", self.contract_two.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                ]
            )
        )
        for invoice in invoices:
            invoice_amount += invoice.amount_total_signed
            invoice_residual += invoice.amount_residual_signed

        bills = (
            self.env["account.move"]
            .sudo()
            .search(
                [
                    ("tenancy_id", "=", self.contract_two.id),
                    ("move_type", "=", "in_invoice"),
                    ("state", "=", "posted"),
                ]
            )
        )
        for bill in bills:
            bill_amount += bill.amount_total_signed
            bill_residual += bill.amount_residual_signed
        self.assertEqual(self.contract_two.total_invoiced, invoice_amount)
        self.assertEqual(self.contract_two.invoice_residual, invoice_residual)
        self.assertEqual(
            self.contract_two.invoice_paid_amount, invoice_amount - invoice_residual
        )
        self.assertEqual(self.contract_two.total_bills, bill_amount)
        self.assertEqual(self.contract_two.bill_residual, bill_residual)
        self.assertEqual(
            self.contract_two.bill_paid_amount, bill_amount - bill_residual
        )
        self.assertEqual(
            self.contract_two.actual_margin,
            invoice_amount - invoice_residual - (-(bill_amount - bill_residual)),
        )
        self.assertEqual(self.contract_two.margin, invoice_amount - (-bill_amount))
        if self.contract_two.total_invoiced != 0:
            self.assertEqual(
                self.contract_two.margin_percentage,
                (self.contract_two.margin * 100) / self.contract_two.total_invoiced,
            )
        else:
            self.assertEqual(self.contract_two.margin_percentage, 0)

        # _compute_rent_unit ---------------------------------------------------

        self.contract_two._compute_rent_unit()
        self.assertEqual(self.contract_two.rent_unit, "Month")
        self.contract_two.final_rent_unit = "Day"
        self.contract_two._compute_rent_unit()
        self.assertEqual(self.contract_two.rent_unit, "Day")

        # _compute_is_contract_period_available --------------------------------

        self.contract_two._compute_is_contract_period_available()
        self.assertFalse(self.contract_two.is_contract_period_available)

        # _compute_durations_ids -----------------------------------------------

        self.contract_two.rent_unit = "Month"
        self.contract_two._compute_durations_ids()
        self.assertEqual(
            len(self.contract_two.duration_ids),
            self.env["contract.duration"].search_count(
                [("month", ">", 0), ("rent_unit", "=", "Month")]
            ),
        )

    def test_onchange_methods(self):
        """Validate onchange behaviours for rent unit and duration type fields."""
        # _onchange_rent_unit --------------------------------------------------

        self.contract_one._onchange_rent_unit()
        self.assertFalse(self.contract_one.payment_term)

        # _onchange_duration_type ----------------------------------------------

        self.contract_two._onchange_duration_type()
        self.assertEqual(self.contract_two.final_rent_unit, "Day")

    def test_action_button(self):
        """Verify contract action buttons: invoices, bills, maintenance requests,
        closing and activating contracts trigger correct actions and state changes."""
        # action_invoices ------------------------------------------------------
        action = self.contract_one.action_invoices()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Invoice")
        self.assertEqual(action["res_model"], "rent.invoice")
        self.assertIn(
            ("tenancy_id", "=", self.contract_one.id), action.get("domain", [])
        )
        self.assertEqual(action["target"], "current")

        # action_bills ---------------------------------------------------------

        action = self.contract_one.action_bills()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Bill")
        self.assertEqual(action["res_model"], "rent.bill")
        self.assertIn(
            ("tenancy_id", "=", self.contract_one.id), action.get("domain", [])
        )
        self.assertEqual(action["target"], "current")

        # action_bills ---------------------------------------------------------

        action = self.contract_one.action_maintenance_request()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Request")
        self.assertEqual(action["res_model"], "maintenance.request")
        self.assertIn(
            ("rent_contract_id", "=", self.contract_one.id), action.get("domain", [])
        )
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")

        # action_close_contract ------------------------------------------------

        action = self.contract_two.action_close_contract()
        self.assertTrue(action)
        self.assertTrue(self.contract_two.close_contract_state)
        self.assertEqual(self.contract_two.property_id.stage, "available")
        self.assertEqual(self.contract_two.contract_type, "close_contract")
        self.assertEqual(
            self.contract_two.terminate_date, datetime.datetime.today().date()
        )
        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_two.id,
            type="manual",
            contract_id=self.contract_two.id,
            rent_unit=self.contract_two.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        for rec in self.contract_one.rent_invoice_ids:
            if rec.rent_invoice_id:
                rec.rent_invoice_id.action_post()
        self.contract_two._compute_tenancy_calculation()
        # A pending balance no longer blocks closure: the close wizard opens
        # and warns about the outstanding amount instead.
        self.assertGreater(self.contract_two.remain_tenancy, 0)
        action = self.contract_two.action_close_contract()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "close.contract.wizard")
        self.assertEqual(action["context"]["active_id"], self.contract_two.id)

        close_wizard = (
            self.env["close.contract.wizard"]
            .with_context(
                active_id=self.contract_two.id, active_model="tenancy.details"
            )
            .create({"water_reading": 100.0, "electricity_reading": 200.0})
        )
        self.assertTrue(close_wizard.has_outstanding_amount)
        self.assertEqual(
            close_wizard.outstanding_amount, self.contract_two.remain_tenancy
        )
        close_wizard.action_close_contract()
        self.assertEqual(self.contract_two.contract_type, "close_contract")
        self.assertTrue(self.contract_two.close_contract_state)

        # action_active_contract -----------------------------------------------

        # Approval workflow (3.3.6) gates ``action_active_contract`` on
        # ``contract_type == 'approved'`` — flip the state directly here
        # instead of threading the full submit → manager-approve flow.
        self._approve_for_activation(self.contract_one)
        self.contract_one.action_active_contract()
        self.assertEqual(self.contract_one.contract_type, "running_contract")
        self.assertTrue(self.contract_one.active_contract_state)
        self.assertEqual(
            self.contract_one.last_invoice_payment_date,
            datetime.datetime.strptime("2025-03-01", "%Y-%m-%d").date(),
        )
        self.assertEqual(self.contract_one.type, "automatic")
        self.assertEqual(len(self.contract_one.rent_invoice_ids), 1)

        # action_active_rent_contract ------------------------------------------

        # Same approval guard — the wizard launched by
        # ``action_active_rent_contract`` ultimately calls
        # ``action_active_contract`` on the tenancy.
        self._approve_for_activation(self.contract_three)
        self.contract_three.action_active_rent_contract()
        self.assertEqual(self.contract_three.contract_type, "running_contract")
        self._approve_for_activation(self.contract_one)
        action = self.contract_one.action_active_rent_contract()
        self.assertIsInstance(action, dict)
        self.assertEqual({"active_id": self.contract_one.id}, action.get("context"))

    def test_scheduler_autometic(self):
        """Check automatic scheduler creates invoices and updates contract states
        for monthly, quarterly and yearly recurring tenancies."""
        # tenancy_recurring_invoice --------------------------------------------

        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_four.id,
            type="automatic",
            contract_id=self.contract_four.id,
            rent_unit=self.contract_four.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(self.contract_four.contract_type, "running_contract")
        self.assertEqual(len(self.contract_four.rent_invoice_ids), 1)
        self.env["ir.config_parameter"].set_param(
            "rental_management.reminder_days", "5"
        )
        self.contract_four.last_invoice_payment_date = (
            datetime.datetime.today().date()
            - relativedelta(months=1)
            + relativedelta(days=5)
        )
        self.contract_four.tenancy_recurring_invoice()
        self.assertEqual(len(self.contract_four.rent_invoice_ids), 2)

        self.contract_four.end_date = datetime.date(2025, 1, 1)
        self.contract_four.contract_type = "running_contract"
        self.contract_four.tenancy_expire()
        self.assertEqual(self.contract_four.contract_type, "expire_contract")

        # tenancy_recurring_quarterly_invoice ----------------------------------

        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_five.id,
            type="automatic",
            contract_id=self.contract_five.id,
            rent_unit=self.contract_five.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(self.contract_five.contract_type, "running_contract")
        self.assertEqual(len(self.contract_five.rent_invoice_ids), 1)
        self.env["ir.config_parameter"].set_param(
            "rental_management.reminder_days", "5"
        )
        self.contract_five.last_invoice_payment_date = (
            datetime.datetime.today().date() - relativedelta(months=3)
        ) + relativedelta(days=5)
        self.contract_five.tenancy_recurring_quarterly_invoice()
        self.assertEqual(len(self.contract_five.rent_invoice_ids), 2)

        self.contract_five.end_date = datetime.date(2025, 1, 1)
        self.contract_five.contract_type = "running_contract"
        self.contract_five.tenancy_expire()
        self.assertEqual(self.contract_five.contract_type, "expire_contract")

        # tenancy_yearly_invoice -----------------------------------------------

        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_six.id,
            type="automatic",
            contract_id=self.contract_six.id,
            rent_unit=self.contract_six.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(self.contract_six.contract_type, "running_contract")
        self.assertEqual(len(self.contract_six.rent_invoice_ids), 1)
        self.env["ir.config_parameter"].set_param(
            "rental_management.reminder_days", "5"
        )
        self.contract_six.last_invoice_payment_date = (
            datetime.datetime.today().date()
            - relativedelta(years=1)
            + relativedelta(days=5)
        )
        self.contract_six.tenancy_yearly_invoice()
        self.assertEqual(len(self.contract_six.rent_invoice_ids), 2)

        self.contract_six.end_date = datetime.date(2025, 1, 1)
        self.contract_six.contract_type = "running_contract"
        self.contract_six.tenancy_expire()
        self.assertEqual(self.contract_six.contract_type, "expire_contract")

    def test_scheduler_manual(self):
        """Confirm manual scheduler creates correct invoices for monthly, quarterly
        and yearly tenancies and updates invoice amounts."""
        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_four.id,
            type="manual",
            contract_id=self.contract_four.id,
            rent_unit=self.contract_four.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(self.contract_four.contract_type, "running_contract")
        self.assertEqual(len(self.contract_four.rent_invoice_ids), 10)
        self.env["ir.config_parameter"].set_param(
            "rental_management.reminder_days", "0"
        )
        self.contract_four.tenancy_manual_invoice()
        invoice = self.contract_four.rent_invoice_ids[1].rent_invoice_id
        self.assertTrue(invoice)
        self.assertEqual(invoice.amount_untaxed, 10020)
        self.assertEqual(invoice.amount_residual, 11021)

        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_five.id,
            type="manual",
            contract_id=self.contract_five.id,
            rent_unit=self.contract_five.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(self.contract_five.contract_type, "running_contract")
        self.assertEqual(len(self.contract_five.rent_invoice_ids), 4)
        self.env["ir.config_parameter"].set_param(
            "rental_management.reminder_days", "0"
        )
        self.contract_five.tenancy_manual_invoice()
        invoice = self.contract_five.rent_invoice_ids[1].rent_invoice_id
        self.assertTrue(invoice)
        self.assertEqual(invoice.amount_untaxed, 30060)
        self.assertEqual(invoice.amount_residual, 33063)

        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_six.id,
            type="manual",
            contract_id=self.contract_six.id,
            rent_unit=self.contract_six.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        self.assertEqual(self.contract_six.contract_type, "running_contract")
        self.assertEqual(len(self.contract_six.rent_invoice_ids), 10)
        self.env["ir.config_parameter"].set_param(
            "rental_management.reminder_days", "0"
        )
        self.contract_six.tenancy_manual_invoice()
        invoice = self.contract_six.rent_invoice_ids[1].rent_invoice_id
        self.assertTrue(invoice)
        self.assertEqual(invoice.amount_untaxed, 10020)
        self.assertEqual(invoice.amount_residual, 11021)

    def test_onchange_agreement_template_id(self):
        """Ensure agreement template variables are correctly replaced in generated agreement."""
        fields = (
            "id",
            "tenancy_seq",
            "total_rent",
            "start_date",
            "duration_type",
            "property_id.name",
        )
        agreement = ""
        for i in range(len(fields)):
            agreement += "{{" + str(i + 1) + "}}\n"
        agreement_template = self._create_agreement_template(
            name="AG1", agreement=agreement
        )
        agreement_template._compute_agreement_variable_ids()
        for rec, field in zip(agreement_template.template_variable_ids, fields):
            rec.field_type = "field"
            rec.field_name = field
        property = self._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
        )
        contract_wizard = self._create_contract_wizard(
            active_model="property.details",
            active_id=property.id,
            data={
                "customer_id": self.customer_one.id,
                "start_date": "2025-03-01",
                "payment_term": "monthly",
                "duration_id": self.duration.id,
                "total_rent": 10000,
                "property_id": property.id,
                "agreement_template_id": agreement_template.id,
            },
        )
        contract_wizard_action = contract_wizard.contract_action()
        contract_one = self.env["tenancy.details"].browse(
            contract_wizard_action["res_id"]
        )
        agreement_str = contract_one.agreement
        self.assertIn(str(contract_one.id), agreement_str)
        self.assertIn(str(contract_one.tenancy_seq), agreement_str)
        self.assertIn(str(contract_one.total_rent), agreement_str)
        self.assertIn(str(contract_one.start_date), agreement_str)
        self.assertIn(str(contract_one.duration_type), agreement_str)
        self.assertIn(str(contract_one.property_id.name), agreement_str)
