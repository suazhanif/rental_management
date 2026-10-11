from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_rent_contract")
class TestCloseContractSettlement(CreateRentalData):
    """Closing a contract settles the security deposit against maintenance."""

    @classmethod
    def setUpClass(cls):
        """Create a contract carrying a security deposit."""
        super().setUpClass()
        cls.settlement_property = cls._create_units(
            name="Settlement Property",
            property_seq="900",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10000,
            rent_unit="Month",
        )
        contract_wizard = cls._create_contract_wizard(
            active_model="property.details",
            active_id=cls.settlement_property.id,
            data={
                "customer_id": cls.customer_one.id,
                "start_date": "2025-03-01",
                "payment_term": "monthly",
                "duration_id": cls.duration.id,
                "total_rent": 10000,
                "property_id": cls.settlement_property.id,
                "is_any_deposit": True,
                "deposit_amount": 5000,
                "water_reading": 5.0,
                "electricity_reading": 15.0,
            },
        )
        cls.contract = cls.env["tenancy.details"].browse(
            contract_wizard.contract_action()["res_id"]
        )

    def _post_deposit_invoice(self):
        """Create and post the deposit invoice of the contract."""
        deposit_invoice_id = self.contract._create_deposit_invoice()
        if deposit_invoice_id.state == "draft":
            deposit_invoice_id.action_post()
        return deposit_invoice_id

    def _close_wizard(self, **values):
        """Build the close wizard for the contract."""
        return (
            self.env["close.contract.wizard"]
            .with_context(active_id=self.contract.id, active_model="tenancy.details")
            .create(
                dict({"water_reading": 10.0, "electricity_reading": 20.0}, **values)
            )
        )

    def test_close_contract_creates_settlement(self):
        """Maintenance is invoiced and the rest of the deposit credited back."""
        deposit_invoice_id = self._post_deposit_invoice()
        self.assertTrue(deposit_invoice_id.is_deposit_invoice)
        self.assertEqual(self.contract._get_deposit_invoice(), deposit_invoice_id)

        wizard = self._close_wizard(maintenance_amount=1200.0)
        self.assertEqual(wizard.deposit_amount, deposit_invoice_id.amount_total)
        self.assertEqual(
            wizard.refundable_amount, deposit_invoice_id.amount_total - 1200.0
        )
        self.assertTrue(wizard.has_deposit_invoice)
        self.assertTrue(wizard.maintenance_product_id)

        wizard.action_close_contract()
        self.assertEqual(self.contract.contract_type, "close_contract")

        # Maintenance is invoiced to the tenant for the amount entered.
        maintenance_line = self.contract.rent_invoice_ids.filtered(
            lambda line: line.type == "maintenance"
        )
        self.assertEqual(len(maintenance_line), 1)
        self.assertEqual(maintenance_line.amount, 1200.0)
        self.assertEqual(maintenance_line.rent_invoice_id.move_type, "out_invoice")
        self.assertEqual(maintenance_line.rent_invoice_id.amount_total, 1200.0)

        # The remaining deposit is credited back.
        settlement_line = self.contract._get_settlement_record()
        self.assertEqual(len(settlement_line), 1)
        self.assertEqual(
            settlement_line.amount, deposit_invoice_id.amount_total - 1200.0
        )
        credit_note_id = settlement_line.rent_invoice_id
        self.assertEqual(credit_note_id.move_type, "out_refund")
        self.assertEqual(credit_note_id.reversed_entry_id, deposit_invoice_id)
        self.assertEqual(credit_note_id.partner_id, self.contract.tenancy_id)
        self.assertEqual(
            credit_note_id.amount_total, deposit_invoice_id.amount_total - 1200.0
        )

    def test_close_contract_is_settled_only_once(self):
        """Re-closing a closed contract does not duplicate the settlement."""
        self._post_deposit_invoice()
        self._close_wizard(maintenance_amount=500.0).action_close_contract()

        settlement_line = self.contract._get_settlement_record()
        self.contract.action_close_contract()
        self.assertEqual(self.contract._get_settlement_record(), settlement_line)
        self.assertEqual(
            len(
                self.contract.rent_invoice_ids.filtered(
                    lambda line: line.type == "maintenance"
                )
            ),
            1,
        )

    def test_maintenance_above_deposit_leaves_nothing_to_refund(self):
        """No credit note when maintenance eats up the whole deposit."""
        deposit_invoice_id = self._post_deposit_invoice()
        self._close_wizard(
            maintenance_amount=deposit_invoice_id.amount_total + 500.0
        ).action_close_contract()

        settlement_line = self.contract._get_settlement_record()
        self.assertEqual(settlement_line.amount, 0.0)
        self.assertFalse(settlement_line.rent_invoice_id)

    def test_close_contract_without_deposit_invoice(self):
        """Maintenance is still invoiced when no deposit was ever billed."""
        self._close_wizard(maintenance_amount=300.0).action_close_contract()

        self.assertEqual(self.contract.contract_type, "close_contract")
        self.assertFalse(self.contract._get_settlement_record())
        maintenance_line = self.contract.rent_invoice_ids.filtered(
            lambda line: line.type == "maintenance"
        )
        self.assertEqual(maintenance_line.amount, 300.0)

    def test_negative_maintenance_amount_is_rejected(self):
        """A negative maintenance amount blocks the closure."""
        wizard = self._close_wizard(maintenance_amount=-10.0)
        with self.assertRaises(ValidationError):
            wizard.action_close_contract()

    def test_maintenance_amount_requires_an_item(self):
        """A maintenance charge cannot be invoiced without a product."""
        wizard = self._close_wizard(
            maintenance_amount=100.0, maintenance_product_id=False
        )
        with self.assertRaises(ValidationError):
            wizard.action_close_contract()
