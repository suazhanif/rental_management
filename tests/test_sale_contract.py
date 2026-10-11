import datetime

from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_sale_contract")
class TestSaleContract(CreateRentalData):
    """Unit tests to verify property sale contract creation, installments, broker commission,
    remaining amount calculations, maintenance requests and all related actions."""

    @classmethod
    def setUpClass(cls):
        """Create demo property, customers and multiple sale contracts through booking wizards."""
        super().setUpClass()
        cls.property = cls._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_sale",
            stage="draft",
            type="land",
            price=1000,
        )
        cls.contract_wizard = cls._create_booking_wizard(
            cls.property.id,
            cls.customer_one.id,
            cls.property.id,
            1000,
            800,
            broker_id=cls.broker_one.id,
            is_any_broker=True,
            commission_from="customer",
            commission_type="p",
            broker_commission_percentage=10,
            booking_item_id=cls.deposit_item_id,
        )
        cls.contract_wizard_two = cls._create_booking_wizard(
            cls.property.id,
            cls.customer_one.id,
            cls.property.id,
            1000,
            800,
            broker_id=cls.broker_one.id,
            is_any_broker=True,
            commission_from="landlord",
            broker_commission=500,
            booking_item_id=cls.deposit_item_id,
        )
        cls.contract_wizard_three = cls._create_booking_wizard(
            cls.property.id,
            cls.customer_one.id,
            cls.property.id,
            1000,
            800,
            broker_id=cls.broker_one.id,
            is_any_broker=True,
            booking_item_id=cls.deposit_item_id,
        )
        cls.contract_action = cls.contract_wizard.create_booking_action()
        cls.contract_action_two = cls.contract_wizard_two.create_booking_action()
        cls.contract_action_three = cls.contract_wizard_three.create_booking_action()
        cls.contract_one = cls.env["property.vendor"].browse(
            cls.contract_action["res_id"]
        )
        cls.contract_two = cls.env["property.vendor"].browse(
            cls.contract_action_two["res_id"]
        )
        cls.contract_three = cls.env["property.vendor"].browse(
            cls.contract_action_three["res_id"]
        )

    def test_create_normal_contract(self):
        """Ensure a normal sale contract is created with correct property, prices and broker details."""
        self.assertTrue(self.contract_one)
        self.assertEqual(self.contract_one.date, datetime.datetime.today().date())
        self.assertEqual(self.contract_one.property_id.id, self.property.id)
        self.assertEqual(self.contract_one.price, 1000)
        self.assertEqual(self.contract_one.book_price, -1000)
        self.assertTrue(self.contract_one.is_any_broker)
        self.assertEqual(self.contract_one.broker_id.id, self.broker_one.id)
        self.assertEqual(self.contract_one.customer_email, self.customer_one.email)
        self.assertEqual(self.contract_one.booking_item_id.id, self.deposit_item_id)
        self.assertEqual(self.contract_one.ask_price, 800)

    def test_compute_remain_amount(self):
        """Validate remaining amount, tax and total calculations for full payment,
        monthly and quarterly installment plans after partial payments."""
        # _compute_remain_amount -----------------------------------------------
        # Full payment
        self.installment_wizard = self._create_installment_wizard(
            self.contract_one.id,
            customer_id=self.contract_one.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="full_payment",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
        self.assertEqual(self.installment_wizard.taxes_ids.amount, 10)
        self.installment_wizard.property_sale_action()
        self.contract_one._compute_remain_amount()
        self.assertTrue(self.installment_wizard)
        self.assertEqual(self.contract_one.tax_amount, 900)
        self.assertEqual(self.contract_one.total_untaxed_amount, 9000)
        self.assertEqual(self.contract_one.total_amount, 9900)
        self.contract_one.action_confirm_sale()
        self.contract_one.sale_invoice_ids.action_create_invoice()
        self.contract_one.sale_invoice_ids.invoice_id.action_post()
        self.payment_wizard = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=self.contract_one.sale_invoice_ids.invoice_id.id,
            )
            .create(
                {
                    "amount": 4950.0,
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
        self.assertEqual(
            self.contract_one.sale_invoice_ids.invoice_id.amount_residual, 4950.0
        )
        self.contract_one._compute_remain_amount()
        self.assertEqual(self.contract_one.tax_amount, 900)
        self.assertEqual(self.contract_one.total_untaxed_amount, 9000)
        self.assertEqual(self.contract_one.total_amount, 9900)
        self.assertEqual(self.contract_one.paid_amount, 4950.0)
        self.assertEqual(self.contract_one.remaining_amount, 4950.0)

        # Monthly

        self.installment_wizard_two = self._create_installment_wizard(
            self.contract_two.id,
            customer_id=self.contract_two.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="monthly",
            duration_id=self.duration.id,
            start_date="2025-04-01",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )

        self.installment_wizard_two.property_sale_action()
        self.assertEqual(len(self.contract_two.sale_invoice_ids), 10)
        self.contract_two.action_confirm_sale()
        for rec in self.contract_two.sale_invoice_ids:
            self.assertFalse(rec.invoice_id)
            rec.action_create_invoice()
            self.assertTrue(rec.invoice_id)
            self.assertEqual(rec.invoice_id.amount_residual, 990)
            rec.invoice_id.action_post()
            self.payment_wizard = (
                self.env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=rec.invoice_id.id)
                .create(
                    {
                        "amount": 495.0,
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
            self.assertEqual(rec.invoice_id.amount_residual, 495.0)
        self.contract_two._compute_remain_amount()
        self.assertEqual(self.contract_two.tax_amount, 900)
        self.assertEqual(self.contract_two.total_untaxed_amount, 9000)
        self.assertEqual(self.contract_two.total_amount, 9900)
        self.assertEqual(self.contract_two.paid_amount, 4950.0)
        self.assertEqual(self.contract_two.remaining_amount, 4950.0)

        # Quarterly

        self.installment_wizard_three = self._create_installment_wizard(
            self.contract_three.id,
            customer_id=self.contract_three.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="quarterly",
            quarter=4,
            start_date="2025-04-01",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
        self.installment_wizard_three.property_sale_action()
        self.assertEqual(len(self.contract_three.sale_invoice_ids), 4)
        month, year = 4, 2025
        for rec in self.contract_three.sale_invoice_ids:
            self.assertFalse(rec.invoice_id)
            rec.action_create_invoice()
            self.assertTrue(rec.invoice_id)
            self.assertEqual(
                rec.invoice_date,
                datetime.datetime.strptime(
                    str(year) + "-" + str(month) + "-01", "%Y-%m-%d"
                ).date(),
            )
            month, year = (month + 3) % 12 or 12, year + (month + 3) // 12
            rec.invoice_id.action_post()
            self.payment_wizard = (
                self.env["account.payment.register"]
                .with_context(
                    active_model="account.move",
                    active_ids=rec.invoice_id.id,
                )
                .create(
                    {
                        "amount": 1237.5,
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
            self.assertEqual(rec.invoice_id.amount_residual, 1237.5)
        self.contract_three._compute_remain_amount()
        self.assertEqual(self.contract_three.tax_amount, 900)
        self.assertEqual(self.contract_three.total_untaxed_amount, 9000)
        self.assertEqual(self.contract_three.total_amount, 9900)
        self.assertEqual(self.contract_three.paid_amount, 4950.0)
        self.assertEqual(self.contract_three.remaining_amount, 4950.0)

    def test_compute_remain_check(self):
        """Check remain_check flag updates correctly after creating and posting all installment invoices."""

        self.installment_wizard_two = self._create_installment_wizard(
            self.contract_two.id,
            customer_id=self.contract_two.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="monthly",
            duration_id=self.duration.id,
            start_date="2025-04-01",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )

        self.installment_wizard_two.property_sale_action()
        self.assertEqual(len(self.contract_two.sale_invoice_ids), 10)
        self.contract_two.sale_invoice_ids[0].action_create_invoice()
        self.contract_two._compute_remain_check()
        self.assertFalse(self.contract_two.remain_check)
        for rec in self.contract_two.sale_invoice_ids:
            rec.action_create_invoice()
        self.contract_two._compute_remain_check()
        self.assertFalse(self.contract_two.remain_check)
        self.installment_wizard_three = self._create_installment_wizard(
            self.contract_three.id,
            customer_id=self.contract_three.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="quarterly",
            quarter=4,
            start_date="2025-04-01",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
        self.installment_wizard_three.property_sale_action()
        self.assertEqual(len(self.contract_three.sale_invoice_ids), 4)
        self.contract_three.action_receive_remaining()
        self.assertEqual(len(self.contract_three.sale_invoice_ids), 1)
        self.contract_three.sale_invoice_ids.action_create_invoice()
        self.assertEqual(
            self.contract_three.sale_invoice_ids.invoice_id.invoice_line_ids.price_total,
            9900.0,
        )
        self.contract_three._compute_remain_check()
        self.assertTrue(self.contract_three.remain_check)

    def test_compute_broker_final_commission(self):
        """Verify broker final commission is correctly computed for both percentage
        and fixed commission types."""
        self.installment_wizard = self._create_installment_wizard(
            self.contract_one.id,
            customer_id=self.contract_one.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="full_payment",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
        self.installment_wizard.property_sale_action()
        self.contract_one._compute_broker_final_commission()
        self.assertEqual(self.contract_one.broker_final_commission, 1000)
        self.installment_wizard = self._create_installment_wizard(
            self.contract_two.id,
            customer_id=self.contract_two.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="full_payment",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
        self.contract_two._compute_broker_final_commission()
        self.assertEqual(self.contract_two.broker_final_commission, 500)

    def test_compute_maintenance_request_count(self):
        """Ensure maintenance request count is updated when a selling contract
        related maintenance request is created."""

        self.installment_wizard = self._create_installment_wizard(
            self.contract_one.id,
            customer_id=self.contract_one.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="full_payment",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
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

        self.installment_wizard.property_sale_action()
        self.maintenance_wizard = self._create_maintenance_wizard(
            active_id=self.contract_one.id,
            name="Maintenence Request",
            property_id=self.property.id,
            maintenance_type_id=self.product_template.id,
            maintenance_team_id=self.maintenance_team.id,
            sell_contract_id=self.contract_one.id,
            is_selling_contract_maintenance=True,
        )
        self.maintenance_wizard.maintenance_request()
        self.maintenance = self.env["maintenance.request"].search_count(
            [("sell_contract_id", "in", [self.contract_one.id])]
        )
        self.contract_one._compute_maintenance_request_count()
        self.assertEqual(self.contract_one.maintenance_request_count, 1)

    def test_compute_sell_price(self):
        """Confirm payable and total sell amounts are computed correctly when maintenance
        services are included in property sale."""
        property_one = self._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_sale",
            stage="draft",
            type="land",
            price=10000,
            is_maintenance_service=True,
            maintenance_type="fixed",
            total_maintenance=500,
        )
        self.contract_wizard_four = self._create_booking_wizard(
            property_one.id,
            self.customer_one.id,
            property_one.id,
            book_price=1000,
            ask_price=900,
            is_any_broker=True,
            broker_id=self.broker_one.id,
            booking_item_id=self.deposit_item_id,
        )
        self.contract_action_four = self.contract_wizard_four.create_booking_action()
        self.contract_four = self.env["property.vendor"].browse(
            self.contract_action_four["res_id"]
        )
        self.contract_four.compute_sell_price()
        self.assertEqual(self.contract_four.payable_amount, -500)
        self.assertEqual(self.contract_four.total_sell_amount, 500)

    def test_all_action_buttons(self):
        """Test all action buttons: refund, cancel, lock and reset installments
        update contract stage and property availability correctly."""
        # action_refund_amount -------------------------------------------------
        self.contract_one.action_refund_amount()
        self.assertEqual(self.contract_one.stage, "refund")
        self.assertEqual(self.contract_one.property_id.stage, "available")
        self.assertFalse(self.contract_one.property_id.sold_booking_id)

        # action_cancel_contract -----------------------------------------------

        self.contract_one.action_cancel_contract()

        self.assertEqual(self.contract_one.stage, "cancel")
        self.assertEqual(self.contract_one.property_id.stage, "available")
        self.assertFalse(self.contract_one.property_id.sold_booking_id)

        # action_locked_contract -----------------------------------------------

        self.contract_one.action_locked_contract()
        self.assertEqual(self.contract_one.stage, "locked")

        # action_reset_installments --------------------------------------------

        self.contract_one.action_reset_installments()
        self.assertFalse(self.contract_one.sale_invoice_ids)

    def test_all_action_methods(self):
        """Validate contract methods: confirm sale action notification,
        creation of installments, customer status update and maintenance request action."""
        # action_confirm_sale --------------------------------------------------

        action = self.contract_one.action_confirm_sale()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "info")
        self.assertEqual(
            action["params"]["message"], "Please create installments to confirm sale."
        )
        self.assertFalse(action["params"]["sticky"])
        self.installment_wizard_five = self._create_installment_wizard(
            self.contract_one.id,
            customer_id=self.contract_one.id,
            company_id=self.company.id,
            property_id=self.property.id,
            payment_term="full_payment",
            final_price=10000,
            is_taxes=True,
            taxes_ids=[(6, 0, [self.tax.id])],
        )
        self.installment_wizard_five.property_sale_action()
        self.contract_one.action_confirm_sale()
        self.assertEqual(self.contract_one.stage, "sold")
        self.assertTrue(self.contract_one.customer_id.is_sold_customer)
        self.assertEqual(self.contract_one.property_id.stage, "sold")

        # action_maintenance_request -------------------------------------------

        action = self.contract_one.action_maintenance_request()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Request")
        self.assertEqual(action["res_model"], "maintenance.request")
        self.assertIn(
            ("sell_contract_id", "=", self.contract_one.id), action.get("domain", [])
        )
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")
