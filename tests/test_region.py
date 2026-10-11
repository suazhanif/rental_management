import datetime

from odoo.tests.common import tagged

from .common import CreateRentalData


@tagged("property_region")
class TestPropertyRegion(CreateRentalData):
    """Test property region creation, counts and related actions."""

    def test_property_region(self):
        """Verify region counts and actions for projects, subprojects and units."""
        city = self._create_cities(name="C1")
        region_one = self._create_region(name="R1", city_ids=[(6, 0, [city.id])])
        self.env["product.template"].create({"name": "Product"})
        self.env["maintenance.team"].create(
            {
                "name": "Team One",
                "member_ids": [
                    (0, 0, {"name": "Team Member One", "login": "team_member_one"}),
                    (0, 0, {"name": "Team Member Two", "login": "team_member_two"}),
                ],
            }
        )
        project = self._create_project(
            name="Project One",
            project_sequence="10",
            project_for="rent",
            property_type="residential",
            property_subtype_id=1,
            date_of_project=datetime.datetime.today(),
            region_id=region_one.id,
        )

        subproject_wizard = self._create_sub_project_wizard(
            "SP1", "01", 5, 5, project.id
        )
        subproject_action = subproject_wizard.create_sub_project()
        subproject = self.env["property.sub.project"].browse(
            subproject_action["res_id"]
        )
        unit_wizard = self._create_units_wizard(1, 8, 1, subproject.id, "sub_project")
        unit_wizard.action_create_property_unit()
        self.env["property.details"].search([("subproject_id", "=", subproject.id)])

        region_one._compute_count()
        self.assertEqual(region_one.project_count, 1)
        self.assertEqual(region_one.subproject_count, 1)
        self.assertEqual(region_one.unit_count, 8)

        # action_view_project --------------------------------------------------

        action = region_one.action_view_project()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Projects")
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertIn(("region_id", "=", region_one.id), action.get("domain", []))
        self.assertEqual({"create": False}, action.get("context", []))
        self.assertEqual(action["res_model"], "property.project")
        self.assertEqual(action["target"], "current")

        # action_view_sub_project ----------------------------------------------

        action = region_one.action_view_sub_project()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Sub Projects")
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertIn(("region_id", "=", region_one.id), action.get("domain", []))
        self.assertEqual({"create": False}, action.get("context", []))
        self.assertEqual(action["res_model"], "property.sub.project")
        self.assertEqual(action["target"], "current")

        # action_view_sub_project ----------------------------------------------

        action = region_one.action_view_properties()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Units")
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertIn(("region_id", "=", region_one.id), action.get("domain", []))
        self.assertEqual({"create": False}, action.get("context", []))
        self.assertEqual(action["res_model"], "property.details")
        self.assertEqual(action["target"], "current")
