import base64
import re

from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_reports")
class TestPropertyReport(CreateRentalData):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.property_one = cls._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_tenancy",
            stage="draft",
            type="land",
            price=1000,
            landlord_id=cls.test_landlord.id,
        )

        cls.property_two = cls._create_units(
            name="Property Two",
            property_seq="002",
            sale_lease="for_sale",
            stage="draft",
            type="residential",
            price=2000,
        )

        cls.property_three = cls._create_units(
            name="Property Three",
            sale_lease="for_sale",
            stage="draft",
            type="commercial",
            price=3000,
        )

        cls.property_four = cls._create_units(
            name="Property Four",
            sale_lease="for_tenancy",
            stage="draft",
            type="industrial",
            price=4000,
        )

    def test_property_sale_tenancy_xls_report_rent(self):
        document_id = 0
        contracts = []
        for _ in range(5):
            self.contract_wizard = self._create_contract_wizard(
                active_model="property.details",
                active_id=self.property_one.id,
                data={
                    "customer_id": self.customer_one.id,
                    "start_date": "2025-03-01",
                    "payment_term": "monthly",
                    "duration_id": self.duration.id,
                    "total_rent": 10000,
                    "property_id": self.property_one.id,
                },
            )
            self.contract_wizard_action = self.contract_wizard.contract_action()
            self.contract_one = self.env["tenancy.details"].browse(
                self.contract_wizard_action["res_id"]
            )
            contracts.append(self.contract_one)

        sale_wizard = self.env["property.report.wizard"].create(
            {"type": "tenancy", "start_date": "2025-03-01", "end_date": "2025-12-31"}
        )

        report = sale_wizard.action_property_xls_report()
        self.assertIsInstance(report, dict)
        self.assertEqual(report["type"], "ir.actions.act_url")
        self.assertEqual(report["target"], "self")
        match = re.search(r"/web/content/(\d+)\?download=true", report["url"])
        if match:
            number = match.group(1)
            document_id = int(number)
        document = self.env["ir.attachment"].browse(document_id)
        self.assertTrue(document)
        for rec in contracts:
            self.assertIn(rec.tenancy_seq, str(base64.decodebytes(document.datas)))

    def test_landlord_tenancy_sold_xls_rent(self):
        document_id = 0
        contracts = []
        contract_wizard = self._create_contract_wizard(
            active_model="property.details",
            active_id=self.property_one.id,
            data={
                "customer_id": self.customer_one.id,
                "start_date": "2025-03-01",
                "payment_term": "monthly",
                "duration_id": self.duration.id,
                "total_rent": 10000,
                "property_id": self.property_one.id,
                "rent_unit": "Month",
            },
        )
        contract_wizard_action = contract_wizard.contract_action()
        self.contract_one = self.env["tenancy.details"].browse(
            contract_wizard_action["res_id"]
        )
        active_contract_wizard = self._create_active_contract(
            active_id=self.contract_one.id,
            type="manual",
            contract_id=self.contract_one.id,
            rent_unit=self.contract_one.rent_unit,
        )
        active_contract_wizard.action_create_contract()
        contracts.append(self.contract_one)

        tenancy_wizard = self.env["landlord.sale.tenancy"].create(
            {"landlord_id": self.test_landlord.id, "report_for": "tenancy"}
        )
        report = tenancy_wizard.action_tenancy_sold_xls_report()
        self.assertIsInstance(report, dict)
        self.assertEqual(report["type"], "ir.actions.act_url")
        self.assertEqual(report["target"], "self")

        match = re.search(r"/web/content/(\d+)\?download=true", report["url"])
        if match:
            number = match.group(1)
            document_id = int(number)
        document = self.env["ir.attachment"].browse(document_id)
        self.assertTrue(document)
        for rec in contracts:
            self.assertIn(rec.tenancy_seq, str(base64.decodebytes(document.datas)))

    def test_property_sale_tenancy_xls_report_sale(self):
        document_id = 0
        contracts = []
        for _ in range(5):
            contract_wizard = self._create_booking_wizard(
                self.property_two.id,
                self.customer_one.id,
                self.property_two.id,
                1000,
                800,
                broker_id=self.broker_one.id,
                is_any_broker=True,
                commission_from="customer",
                commission_type="p",
                broker_commission_percentage=10,
                booking_item_id=self.deposit_item_id,
            )
            contract_wizard_action = contract_wizard.create_booking_action()
            contract_one = self.env["property.vendor"].browse(
                contract_wizard_action["res_id"]
            )
            contracts.append(contract_one)

        sale_wizard = self.env["property.report.wizard"].create(
            {"type": "sold", "start_date": "2025-03-01", "end_date": "2025-12-31"}
        )

        report = sale_wizard.action_property_xls_report()
        self.assertIsInstance(report, dict)
        self.assertEqual(report["type"], "ir.actions.act_url")
        self.assertEqual(report["target"], "self")
        match = re.search(r"/web/content/(\d+)\?download=true", report["url"])
        if match:
            number = match.group(1)
            document_id = int(number)
        document = self.env["ir.attachment"].browse(document_id)
        self.assertTrue(document)
        for rec in contracts:
            self.assertIn(rec.sold_seq, str(base64.decodebytes(document.datas)))

    def test_landlord_tenancy_sold_xls_sale(self):
        document_id = 0
        contracts = []
        for _ in range(5):
            contract_wizard = self._create_booking_wizard(
                active_id=self.property_two.id,
                customer_id=self.customer_one.id,
                property_id=self.property_two.id,
                book_price=1000,
                ask_price=800,
                broker_id=self.broker_one.id,
                is_any_broker=True,
                commission_from="customer",
                commission_type="p",
                broker_commission_percentage=10,
                booking_item_id=self.deposit_item_id,
            )

            contract_wizard_action = contract_wizard.create_booking_action()
            contract_one = self.env["property.vendor"].browse(
                contract_wizard_action["res_id"]
            )
            installment_wizard = self._create_installment_wizard(
                contract_one.id,
                customer_id=contract_one.id,
                company_id=self.company.id,
                property_id=self.property_two.id,
                payment_term="full_payment",
                final_price=10000,
                is_taxes=True,
                taxes_ids=[(6, 0, [self.tax.id])],
            )
            installment_wizard.property_sale_action()

        tenancy_wizard = self.env["landlord.sale.tenancy"].create(
            {"landlord_id": self.test_landlord.id, "report_for": "tenancy"}
        )
        report = tenancy_wizard.action_tenancy_sold_xls_report()
        self.assertIsInstance(report, dict)
        self.assertEqual(report["type"], "ir.actions.act_url")
        self.assertEqual(report["target"], "self")

        match = re.search(r"/web/content/(\d+)\?download=true", report["url"])
        if match:
            number = match.group(1)
            document_id = int(number)
        document = self.env["ir.attachment"].browse(document_id)
        self.assertTrue(document)
        for rec in contracts:
            self.assertIn(rec.tenancy_seq, str(base64.decodebytes(document.datas)))
