import datetime

import psycopg2
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_details")
class TestProperty(CreateRentalData):
    """Unit tests for Property Details model functionality."""

    @classmethod
    def setUpClass(cls):
        """Prepare initial property and service records for tests."""
        super().setUpClass()

        cls.property_one = cls._create_units(
            name="Property One",
            property_seq="001",
            sale_lease="for_sale",
            stage="draft",
            type="land",
            price=1000,
        )

        cls.property_two = cls._create_units(
            name="Property Two",
            property_seq="002",
            sale_lease="for_tenancy",
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

        cls.service_one = cls._create_service("Service One", True, 100, 50)
        cls.service_two = cls._create_service("Service Two", True, 200, 100)
        cls.service_three = cls._create_service("Service Three", True, 300, 150)
        cls.service_four = cls._create_service("Service Four", True, 400, 200)

    def test_create_property(self):
        """Verify property creation and required fields validation."""
        self.assertTrue(self.property_one)
        self.assertTrue(self.property_two)
        self.assertTrue(self.property_three)
        self.assertTrue(self.property_four)

        with self.assertLogs("odoo.sql_db", level="ERROR"):
            with self.assertRaises(psycopg2.errors.NotNullViolation):
                self.env["property.details"].create({})

    def test_create(self):
        """Check property sequence is auto-generated if not provided."""
        self.assertEqual(self.property_one.property_seq, "001")
        self.assertTrue(self.property_three.property_seq)

    def test_expand_groups(self):
        """Ensure property stage groups expand correctly."""
        self.assertEqual(
            ["draft", "available", "booked", "on_lease", "sale", "sold"],
            self.property_one._expand_groups(None, None),
        )

    def test_unlink(self):
        """Validate properties in certain stages cannot be deleted."""
        self.property_one.stage = "booked"
        self.property_two.stage = "on_lease"
        self.property_three.stage = "sale"
        self.property_four.stage = "sold"

        with self.assertRaises(ValidationError):
            self.property_one.unlink()
        with self.assertRaises(ValidationError):
            self.property_two.unlink()
        with self.assertRaises(ValidationError):
            self.property_three.unlink()
        with self.assertRaises(ValidationError):
            self.property_four.unlink()

    def test_compute_method(self):
        """Test all computed fields and their dependent logic."""
        # compute_room_measure ---------------------------------------------------------------------

        self.property_one.measure_unit = "sq_ft"
        self.property_two.measure_unit = "cu_ft"
        self.property_one.is_section_measurement = True
        self.property_two.is_section_measurement = True
        self.section_one = self.env["property.area.type"].create(
            {"name": "Section One", "type": "room"}
        )
        self.property_one.room_measurement_ids = [
            (
                0,
                0,
                {
                    "section_id": self.section_one.id,
                    "length": 10,
                    "width": 10,
                    "height": 10,
                    "no_of_unit": 5,
                },
            ),
            (
                0,
                0,
                {
                    "section_id": self.section_one.id,
                    "length": 20,
                    "width": 20,
                    "height": 20,
                    "no_of_unit": 5,
                },
            ),
        ]

        self.property_three.room_measurement_ids = [
            (
                0,
                0,
                {
                    "section_id": self.section_one.id,
                    "length": 10,
                    "width": 10,
                    "height": 10,
                    "no_of_unit": 5,
                },
            )
        ]

        self.property_measurement_one = self.env["property.room.measurement"].create(
            {
                "section_id": self.section_one.id,
                "length": 10,
                "width": 10,
                "height": 10,
                "no_of_unit": 5,
                "room_measurement_id": self.property_two.id,
            }
        )

        self.property_measurement_two = self.env["property.room.measurement"].create(
            {
                "section_id": self.section_one.id,
                "length": 20,
                "width": 20,
                "height": 20,
                "no_of_unit": 5,
                "room_measurement_id": self.property_two.id,
            }
        )

        self.property_measurement_one._compute_carpet_area()
        self.property_measurement_two._compute_carpet_area()
        self.assertEqual(self.property_measurement_one.carpet_area, 5000)
        self.assertEqual(self.property_measurement_two.carpet_area, 40000)

        self.property_one._compute_room_measure()
        self.property_two._compute_room_measure()
        self.property_three._compute_room_measure()
        self.assertEqual(self.property_one.total_area, 2500)
        self.assertEqual(self.property_two.total_area, 45000)
        self.assertEqual(self.property_three.total_area, 0.0)

        # _compute_lead ---------------------------------------------------------------------

        self.lead_one = self.env["crm.lead"].create(
            {"name": "Lead One", "type": "lead", "property_id": self.property_one.id}
        )
        self.lead_two = self.env["crm.lead"].create(
            {
                "name": "Lead Two",
                "type": "opportunity",
                "property_id": self.property_one.id,
            }
        )
        self.lead_three = self.env["crm.lead"].create(
            {"name": "Lead Three", "type": "lead", "property_id": self.property_one.id}
        )
        self.lead_four = self.env["crm.lead"].create(
            {
                "name": "Lead Four",
                "type": "opportunity",
                "property_id": self.property_one.id,
            }
        )

        self.lead_five = self.env["crm.lead"].create(
            {"name": "Lead Five", "type": "lead", "property_id": self.property_two.id}
        )
        self.lead_six = self.env["crm.lead"].create(
            {
                "name": "Lead Six",
                "type": "opportunity",
                "property_id": self.property_two.id,
            }
        )
        self.lead_seven = self.env["crm.lead"].create(
            {"name": "Lead Seven", "type": "lead", "property_id": self.property_two.id}
        )
        self.lead_eight = self.env["crm.lead"].create(
            {
                "name": "Lead Eight",
                "type": "opportunity",
                "property_id": self.property_two.id,
            }
        )

        self.property_one._compute_lead()
        self.property_two._compute_lead()
        self.property_three._compute_lead()

        self.assertEqual(self.property_one.lead_count, 2)
        self.assertEqual(self.property_one.lead_opp_count, 2)
        self.assertEqual(self.property_two.lead_count, 2)
        self.assertEqual(self.property_two.lead_opp_count, 2)
        self.assertEqual(self.property_three.lead_count, 0)
        self.assertEqual(self.property_three.lead_opp_count, 0)

        # _compute_extra_service_cost ---------------------------------------------------------------------

        self.extra_service_one = self._create_extra_service(
            self.service_one.id, "once", self.property_one.id
        )
        self.extra_service_two = self._create_extra_service(
            self.service_two.id, "monthly", self.property_one.id
        )
        self.extra_service_three = self._create_extra_service(
            self.service_three.id, "once", self.property_one.id
        )
        self.extra_service_four = self._create_extra_service(
            self.service_four.id, "monthly", self.property_one.id
        )
        self.extra_service_one._onchange_service_id_price()
        self.extra_service_two._onchange_service_id_price()
        self.extra_service_three._onchange_service_id_price()
        self.extra_service_four._onchange_service_id_price()

        self.assertEqual(self.extra_service_one.price, 100)
        self.assertEqual(self.extra_service_two.price, 200)
        self.assertEqual(self.extra_service_three.price, 300)
        self.assertEqual(self.extra_service_four.price, 400)

        view = self.env.ref("rental_management.property_details_form_view")
        arch = view.arch
        self.assertIn(""" invisible="not is_maintenance_service" """, arch)
        self.assertIn(
            """invisible="sale_lease != 'for_tenancy' or not is_maintenance_service""",
            arch,
        )

        self.property_one._compute_extra_service_cost()
        self.property_two._compute_extra_service_cost()
        self.assertEqual(self.property_one.extra_service_cost, 1000)
        self.assertEqual(self.property_two.extra_service_cost, 0)

        # _compute_booking_count ---------------------------------------------------------------------

        self.property_one.rent_unit = "Month"

        self.booking_create_wizard_one = self._create_booking_wizard(
            active_id=self.property_one.id,
            customer_id=self.customer_one.id,
            property_id=self.property_one.id,
            book_price=1000,
            ask_price=800,
            broker_id=self.broker_one.id,
        )

        self.booking_create_wizard_one.create_booking_action()
        self.one_month_duration = self._create_duration("One Month", 1, "Month")
        count = 0
        while True:
            date = datetime.datetime.today()
            self.contract_wizard_one = self._create_contract_wizard(
                active_id=self.property_two.id,
                active_model="property.details",
                data={
                    "customer_id": self.customer_one.id,
                    "duration_type": "by_duration",
                    "start_date": date,
                    "payment_term": "monthly",
                    "duration_id": self.one_month_duration.id,
                    "property_id": self.property_two.id,
                },
            )
            self.contract_wizard_one.contract_action()
            count += 1
            if count == 5:
                break
        self.property_two._compute_booking_count()

        self.assertEqual(self.property_two.tenancy_count, 5)

        # _compute_request_count ---------------------------------------------------------------------

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
            self.maintenance_wizard = self._create_maintenance_wizard(
                active_id=self.property_one.id,
                name="Maintenence Request",
                property_id=self.property_one.id,
                maintenance_type_id=self.product_template.id,
                maintenance_team_id=self.maintenance_team.id,
                is_property_maintenance=True,
            )

            self.maintenance_wizard.maintenance_request()
            count += 1
            if count == 5:
                break

        self.property_one._compute_request_count()
        self.assertEqual(self.property_one.request_count, 5)

    def test_onchange_methods(self):
        """Check onchange methods update fields as expected."""
        # onchange_fix_area_price ---------------------------------------------
        self.property_one.pricing_type = "area_wise"
        self.property_one.total_area = 100
        self.property_one.price_per_area = 100

        self.property_one._onchange_fix_area_price()
        self.assertEqual(self.property_one.price, 10000)

        # onchange_maintenance_type_charges ---------------------------------------------

        self.property_one.pricing_type = "fixed"
        self.property_one.price = 0
        self.property_one._onchange_fix_area_price()
        self.assertEqual(self.property_one.price, 0)

        self.property_one.per_area_maintenance = 100
        self.property_one.total_area = 100

        self.property_one.is_maintenance_service = True
        self.property_one.maintenance_type = "area_wise"
        self.property_one._onchange_maintenance_type_charges()
        self.assertEqual(self.property_one.total_maintenance, 10000)

        self.property_one.is_maintenance_service = False
        self.property_one.total_maintenance = 0
        self.property_one._onchange_maintenance_type_charges()

        self.assertEqual(self.property_one.total_maintenance, 0)

        # onchange_area_measure ---------------------------------------------

        self.section_one = self.env["property.area.type"].create(
            {"name": "Section One", "type": "room"}
        )
        self.property_one.is_section_measurement = True
        self.property_one.room_measurement_ids = [
            (
                0,
                0,
                {
                    "section_id": self.section_one.id,
                    "length": 10,
                    "width": 10,
                    "height": 10,
                    "no_of_unit": 5,
                    "room_measurement_id": self.property_two.id,
                },
            ),
            (
                0,
                0,
                {
                    "section_id": self.section_one.id,
                    "length": 20,
                    "width": 20,
                    "height": 20,
                    "no_of_unit": 5,
                    "room_measurement_id": self.property_two.id,
                },
            ),
        ]

        self.property_one._onchange_area_measure()
        self.assertEqual(self.property_one.total_area, 2500)

        self.property_one.measure_unit = "cu_ft"

        self.property_one._onchange_area_measure()
        self.assertEqual(self.property_one.total_area, 45000)

        # _onchange_property_sub_type ---------------------------------------------

        self.property_one.property_subtype_id = 7
        self.property_one._onchange_property_sub_type()
        self.assertFalse(self.property_one.property_subtype_id)

        # _onchange_country_id ---------------------------------------------

        self.property_one.country_id = 104
        self.property_one.state_id = 1

        self.property_one._onchange_country_id()

        self.assertFalse(self.property_one.state_id)

        # _onchange_state ---------------------------------------------

        self.property_one.country_id = False
        self.property_one.state_id = 588

        self.property_one._onchange_state()
        self.assertEqual(self.property_one.country_id.id, 104)

    def test_action_methods(self):
        """Verify all action methods return correct action dictionaries."""
        # _onchange_state ---------------------------------------------

        self.property_one.stage = "draft"
        self.property_one.action_in_available()
        self.assertEqual(self.property_one.stage, "available")

        # action_in_booked ---------------------------------------------

        self.property_one.action_in_booked()
        self.assertEqual(self.property_one.stage, "booked")

        # action_sold ---------------------------------------------

        self.property_one.action_sold()
        self.assertEqual(self.property_one.stage, "sold")

        # action_draft_property ---------------------------------------------

        self.property_one.action_draft_property()
        self.assertEqual(self.property_one.stage, "draft")

        # action_in_sale ---------------------------------------------

        self.property_one.action_in_sale()
        self.assertEqual(self.property_one.stage, "sale")

        warning = self.property_two.action_in_sale()
        self.assertIsInstance(warning, dict)
        self.assertEqual(warning["type"], "ir.actions.client")
        self.assertEqual(warning["tag"], "display_notification")
        self.assertIsInstance(warning["params"], dict)

        self.assertEqual(warning["params"]["type"], "info")
        self.assertIn(
            """You need to set "Price/Rent" to "For Sale" to proceed""",
            warning["params"]["title"],
        )
        self.assertFalse(warning["params"]["sticky"])

        # action_gmap_location ---------------------------------------------

        self.property_one.longitude = 40
        self.property_one.latitude = 35
        action = self.property_one.action_gmap_location()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["url"], "https://maps.google.com/maps?q=loc:35,40")

        self.property_one.longitude = False
        self.property_one.latitude = 12
        with self.assertRaises(ValidationError):
            self.property_one.action_gmap_location()

        self.property_one.longitude = 12
        self.property_one.latitude = False
        with self.assertRaises(ValidationError):
            self.property_one.action_gmap_location()

        self.property_one.longitude = False
        self.property_one.latitude = False
        with self.assertRaises(ValidationError):
            self.property_one.action_gmap_location()

        # action_maintenance_request ---------------------------------------------

        action = self.property_one.action_maintenance_request()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Request")
        self.assertEqual(action["res_model"], "maintenance.request")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertEqual(
            {"default_property_id": self.property_one.id}, action.get("context")
        )
        self.assertEqual(action["target"], "current")

        # action_property_document ---------------------------------------------

        action = self.property_one.action_property_document()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Document")
        self.assertEqual(action["res_model"], "property.documents")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertEqual(
            {"default_property_id": self.property_one.id}, action.get("context")
        )
        self.assertEqual(action["target"], "current")

        # action_sale_booking ---------------------------------------------

        action = self.property_one.action_sale_booking()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Booking Information")
        self.assertEqual(action["res_model"], "property.vendor")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertEqual(
            {"default_property_id": self.property_one.id}, action.get("context")
        )
        self.assertEqual(action["target"], "current")

        # action_crm_lead ---------------------------------------------

        action = self.property_one.action_crm_lead()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Leads")
        self.assertEqual(action["res_model"], "crm.lead")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertIn(("type", "=", "lead"), action.get("domain", []))
        self.assertEqual(
            {"default_property_id": self.property_one.id, "default_type": "lead"},
            action.get("context"),
        )
        self.assertEqual(action["target"], "current")

        # action_crm_lead_opp ---------------------------------------------

        action = self.property_one.action_crm_lead_opp()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Opportunity")
        self.assertEqual(action["res_model"], "crm.lead")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertIn(("type", "=", "opportunity"), action.get("domain", []))
        self.assertEqual(
            {
                "default_property_id": self.property_one.id,
                "default_type": "opportunity",
            },
            action.get("context"),
        )
        self.assertEqual(action["target"], "current")

        # action_view_contract ---------------------------------------------

        action = self.property_one.action_view_contract()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Rent Contracts")
        self.assertEqual(action["res_model"], "tenancy.details")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")

        # action_view_sell_contract ---------------------------------------------

        action = self.property_one.action_view_sell_contract()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Sell Contracts")
        self.assertEqual(action["res_model"], "property.vendor")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")

        # action_property_tenancy_broker ---------------------------------------------

        self.ids = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [
                    ("property_id", "=", self.property_one.id),
                    ("is_any_broker", "=", True),
                ]
            )
            .mapped("broker_id")
            .mapped("id")
        )
        action = self.property_one.action_property_tenancy_broker()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Brokers")
        self.assertEqual(action["res_model"], "res.partner")
        self.assertIn(("id", "in", self.ids), action.get("domain", []))
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")

        # action_property_sale_broker ---------------------------------------------

        self.ids = (
            self.env["property.vendor"]
            .sudo()
            .search(
                [
                    ("property_id", "=", self.property_one.id),
                    ("is_any_broker", "=", True),
                ]
            )
            .mapped("broker_id")
            .mapped("id")
        )

        action = self.property_one.action_property_sale_broker()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Brokers")
        self.assertEqual(action["res_model"], "res.partner")
        self.assertIn(("id", "in", self.ids), action.get("domain", []))
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")

        # action_view_increment_history ---------------------------------------------

        action = self.property_one.action_view_increment_history()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["name"], "Increment History")
        self.assertEqual(action["res_model"], "increment.history")
        self.assertIn(
            ("property_id", "=", self.property_one.id), action.get("domain", [])
        )
        self.assertEqual({"create": False}, action.get("context"))
        self.assertEqual(action["target"], "current")

        # Server Action
        # action_available_property ---------------------------------------------

        self.property_one.stage = "draft"
        self.property_two.stage = "draft"
        self.property_three.stage = "draft"
        self.property_four.stage = "draft"

        action = self.property_one.with_context(
            {
                "active_ids": [
                    self.property_one.id,
                    self.property_two.id,
                    self.property_three.id,
                    self.property_four.id,
                ],
                "active_model": "property.details",
            }
        ).action_available_property()

        self.assertEqual(self.property_one.stage, "available")
        self.assertEqual(self.property_two.stage, "available")
        self.assertEqual(self.property_three.stage, "available")
        self.assertEqual(self.property_four.stage, "available")

    def test_dashboard_methods(self):
        """Ensure dashboard statistics methods return accurate counts."""
        data = self.property_one.get_property_stats()
        self.assertIsInstance(data, dict)

        company_domain = [("company_id", "in", self.env.companies.ids)]
        property = self.env["property.details"]

        self.property_one.stage = "available"
        self.property_two.stage = "available"
        self.property_three.stage = "available"
        self.property_four.stage = "available"

        data = self.property_one.get_property_stats()
        self.assertEqual(
            data["avail_property"],
            property.sudo().search_count(
                [("stage", "=", "available")] + company_domain
            ),
        )

        self.property_one.stage = "booked"
        self.property_two.stage = "booked"
        self.property_three.stage = "booked"
        self.property_four.stage = "booked"

        data = self.property_one.get_property_stats()
        self.assertEqual(
            data["booked_property"],
            property.sudo().search_count([("stage", "=", "booked")] + company_domain),
        )

        self.property_one.stage = "on_lease"
        self.property_two.stage = "on_lease"
        self.property_three.stage = "on_lease"
        self.property_four.stage = "on_lease"

        data = self.property_one.get_property_stats()
        self.assertEqual(
            data["lease_property"],
            property.sudo().search_count([("stage", "=", "on_lease")] + company_domain),
        )

        self.property_one.stage = "sale"
        self.property_two.stage = "sale"
        self.property_three.stage = "sale"
        self.property_four.stage = "sale"

        data = self.property_one.get_property_stats()
        self.assertEqual(
            data["sale_property"],
            property.sudo().search_count([("stage", "=", "sale")] + company_domain),
        )

        self.region_one = self.env["property.region"].create(
            {
                "name": "Region One",
                "city_ids": [
                    (0, 0, {"name": "City One"}),
                    (0, 0, {"name": "City Two"}),
                ],
            }
        )
        self.region_two = self.env["property.region"].create(
            {
                "name": "Region Two",
                "city_ids": [
                    (0, 0, {"name": "City Three"}),
                    (0, 0, {"name": "City Four"}),
                ],
            }
        )

        data = self.property_one.get_property_stats()

        self.assertEqual(
            data["region_count"], self.env["property.region"].search_count([])
        )
        count = 0
        while True:
            self.test_property_one = self._create_project(
                name="Project One",
                project_sequence="10",
                project_for="rent",
                property_type="residential",
                property_subtype_id=1,
                date_of_project=datetime.datetime.today(),
            )
            count += 1
            if count == 5:
                break

        data = self.property_one.get_property_stats()

        self.assertEqual(
            data["project_count"],
            self.env["property.project"].search_count(company_domain),
        )

        count = 0
        while True:
            self.test_sub_project_one = self.env["property.sub.project"].create(
                {
                    "company_id": self.env.ref("base.main_company"),
                    "name": "Sub Project One",
                    "project_sequence": "10",
                    "property_type": "residential",
                    "property_project_id": self.test_property_one.id,
                }
            )
            count += 1
            if count == 5:
                break

        data = self.property_one.get_property_stats()

        self.assertEqual(
            data["subproject_count"],
            self.env["property.sub.project"].search_count(company_domain),
        )

        data = self.property_one.get_property_stats()

        self.assertEqual(data["total_property"], property.search_count(company_domain))
