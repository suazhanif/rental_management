import datetime

from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_rent_extend_contract")
class TestRentExtendContract(CreateRentalData):
    """Unit tests to verify property rent contract extension process,
    including rent increment calculations and start date validations."""

    @classmethod
    def setUpClass(cls):
        """Create initial tenancy contract and prepare extension wizard for test scenarios."""
        super().setUpClass()
        cls.property = cls._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=10,
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
            active_id=cls.property.id,
            active_model="property.details",
            data={
                "customer_id": cls.customer_one.id,
                "duration_type": "by_date",
                "duration_end_date": datetime.datetime.today().date()
                - relativedelta(days=1),
            },
        )
        cls.contract_wizard.default_get(
            {
                "property_id": None,
                "customer_id": None,
                "start_date": None,
                "is_contract_extend": None,
                "installment_item_id": None,
                "deposit_item_id": None,
                "broker_item_id": None,
                "maintenance_item_id": None,
                "is_any_deposit": None,
                "deposit_amount": None,
                "rent_unit": None,
                "total_rent": None,
                "is_any_broker": None,
                "broker_id": None,
                "commission_from": None,
                "rent_type": None,
                "commission_type": None,
                "broker_commission_percentage": None,
                "broker_commission": None,
                "term_condition": None,
                "previous_rent": None,
            }
        )
        cls.contract_wizard._compute_end_date()
        cls.contract_wizard_action = cls.contract_wizard.contract_action()
        cls.contract_one = cls.env["tenancy.details"].browse(
            cls.contract_wizard_action["res_id"]
        )
        cls.contract_one.tenancy_expire()
        cls.extend_contract_wizard = cls._create_contract_wizard(
            active_id=cls.contract_one.id,
            active_model="tenancy.details",
            data={
                "customer_id": cls.customer_one.id,
                "duration_type": "by_date",
                "total_rent": 10,
                "property_id": cls.property.id,
                "start_date": datetime.datetime.today().date(),
            },
        )

    def test_create_extend_contract(self):
        """Ensure a new extended contract is created correctly and
        previous contract is marked as closed with appropriate references."""
        res = self.extend_contract_wizard.default_get(
            {
                "property_id": None,
                "customer_id": None,
                "start_date": None,
                "is_contract_extend": None,
                "installment_item_id": None,
                "deposit_item_id": None,
                "broker_item_id": None,
                "maintenance_item_id": None,
                "is_any_deposit": None,
                "deposit_amount": None,
                "rent_unit": None,
                "total_rent": None,
                "is_any_broker": None,
                "broker_id": None,
                "commission_from": None,
                "rent_type": None,
                "commission_type": None,
                "broker_commission_percentage": None,
                "broker_commission": None,
                "term_condition": None,
                "previous_rent": None,
            }
        )
        self.assertIsInstance(res, dict)
        action = self.extend_contract_wizard.contract_action()
        self.assertIsInstance(action, dict)
        extand_contract = self.env["tenancy.details"].browse(action["res_id"])
        self.assertTrue(extand_contract)
        self.assertTrue(self.contract_one.extended)
        self.assertEqual(self.contract_one.extend_ref, extand_contract.tenancy_seq)
        self.assertEqual(self.contract_one.new_contract_id.id, extand_contract.id)
        self.assertTrue(extand_contract.is_extended)
        self.assertEqual(extand_contract.extend_from, self.contract_one.tenancy_seq)
        self.assertEqual(self.contract_one.contract_type, "close_contract")
        self.assertTrue(self.contract_one.close_contract_state)

    def test_extend_rent_increment(self):
        """Validate rent increment computation for both fixed and percentage
        increment types during contract extension."""
        self.extend_contract_wizard.default_get(
            {
                "property_id": None,
                "customer_id": None,
                "start_date": None,
                "is_contract_extend": None,
                "installment_item_id": None,
                "deposit_item_id": None,
                "broker_item_id": None,
                "maintenance_item_id": None,
                "is_any_deposit": None,
                "deposit_amount": None,
                "rent_unit": None,
                "total_rent": None,
                "is_any_broker": None,
                "broker_id": None,
                "commission_from": None,
                "rent_type": None,
                "commission_type": None,
                "broker_commission_percentage": None,
                "broker_commission": None,
                "term_condition": None,
                "previous_rent": None,
            }
        )
        self.extend_contract_wizard.is_contract_extend = True
        self.extend_contract_wizard.is_rent_increment = True
        self.extend_contract_wizard.current_rent_type = "fixed"
        self.extend_contract_wizard.rent_increment_type = "fix"
        self.assertEqual(self.extend_contract_wizard.incremented_rent, 10)
        self.extend_contract_wizard.increment_amount = 10
        self.extend_contract_wizard.compute_increment_rent()
        action = self.extend_contract_wizard.contract_action()
        self.assertIsInstance(action, dict)
        extand_contract = self.env["tenancy.details"].browse(action["res_id"])
        self.assertEqual(extand_contract.total_rent, 20)

        self.extend_contract_wizard.default_get(
            {
                "property_id": None,
                "customer_id": None,
                "start_date": None,
                "is_contract_extend": None,
                "installment_item_id": None,
                "deposit_item_id": None,
                "broker_item_id": None,
                "maintenance_item_id": None,
                "is_any_deposit": None,
                "deposit_amount": None,
                "rent_unit": None,
                "total_rent": None,
                "is_any_broker": None,
                "broker_id": None,
                "commission_from": None,
                "rent_type": None,
                "commission_type": None,
                "broker_commission_percentage": None,
                "broker_commission": None,
                "term_condition": None,
                "previous_rent": None,
            }
        )
        self.extend_contract_wizard.is_contract_extend = True
        self.extend_contract_wizard.is_rent_increment = True
        self.extend_contract_wizard.current_rent_type = "fixed"
        self.extend_contract_wizard.rent_increment_type = "percentage"
        self.extend_contract_wizard.increment_percentage = 10
        action = self.extend_contract_wizard.contract_action()
        self.assertIsInstance(action, dict)
        extand_contract = self.env["tenancy.details"].browse(action["res_id"])
        self.assertEqual(extand_contract.total_rent, 11)

    def test_check_contract_start(self):
        """Confirm ValidationError is raised if new contract start date is not
        after the previous contract's end date."""
        self.contract_one.end_date = datetime.datetime.today().date() + relativedelta(
            days=1
        )
        self.extend_contract_wizard.default_get(
            {
                "property_id": None,
                "customer_id": None,
                "start_date": None,
                "is_contract_extend": None,
                "installment_item_id": None,
                "deposit_item_id": None,
                "broker_item_id": None,
                "maintenance_item_id": None,
                "is_any_deposit": None,
                "deposit_amount": None,
                "rent_unit": None,
                "total_rent": None,
                "is_any_broker": None,
                "broker_id": None,
                "commission_from": None,
                "rent_type": None,
                "commission_type": None,
                "broker_commission_percentage": None,
                "broker_commission": None,
                "term_condition": None,
                "previous_rent": None,
            }
        )
        with self.assertRaisesRegex(
            ValidationError,
            "Contract start date must be greater than previous contract end date",
        ):
            self.extend_contract_wizard.is_contract_extend = True
            self.extend_contract_wizard.contract_action()
