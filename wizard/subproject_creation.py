# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class SubprojectCreation(models.TransientModel):
    """Subproject Creation"""

    _name = "subproject.creation"
    _description = "Create Building"

    name = fields.Char(string="Name", required=True)
    project_sequence = fields.Char(string="Code", required=True)
    floors = fields.Integer(string="No. of Floors")
    units_per_floor = fields.Integer(string="Units per Floor")

    def create_sub_project(self):
        """Process subproject creation"""
        images = []
        nearby = []
        active_id = self.env.context.get("active_id", False)
        if not active_id:
            return
        project_id = self.env["property.project"].browse(active_id)
        data = {
            "name": self.name,
            "project_sequence": self.project_sequence,
            "property_project_id": project_id.id,
            "country_id": project_id.country_id.id,
            "street": project_id.street,
            "street2": project_id.street2,
            "city_id": project_id.city_id.id,
            "state_id": project_id.state_id.id,
            "property_brochure": project_id.property_brochure,
            "brochure_name": project_id.brochure_name,
            "zip": project_id.zip,
            "total_floors": self.floors,
            "units_per_floor": self.units_per_floor,
            "sale_lease": project_id.sale_lease,
        }
        if project_id.avail_description:
            data["avail_description"] = project_id.avail_description
            data["description"] = project_id.description
        if project_id.avail_amenity:
            data["avail_amenity"] = project_id.avail_amenity
            data["subproject_amenity_ids"] = project_id.property_amenity_ids.ids
        if project_id.avail_specification:
            data["avail_specification"] = project_id.avail_specification
            data["subproject_specification_ids"] = (
                project_id.property_specification_ids.ids
            )
        if project_id.avail_image:
            data["avail_image"] = project_id.avail_image
            for image in project_id.project_image_ids:
                images.append(
                    (
                        0,
                        0,
                        {
                            "title": image.title,
                            "sequence": image.sequence,
                            "image": image.image,
                        },
                    )
                )
            data["subproject_image_ids"] = images
        if project_id.avail_nearby_connectivity:
            data["avail_nearby_connectivity"] = project_id.avail_nearby_connectivity
            for n in project_id.project_connectivity_ids:
                nearby.append(
                    (
                        0,
                        0,
                        {
                            "connectivity_id": n.connectivity_id.id,
                            "name": n.name,
                            "image": n.image,
                            "distance": n.distance,
                        },
                    )
                )
            data["subproject_connectivity_ids"] = nearby

        sub_project_id = self.env["property.sub.project"].create(data)
        return {
            "type": "ir.actions.act_window",
            "name": ("Sub Projects"),
            "res_model": "property.sub.project",
            "res_id": sub_project_id.id,
            "view_mode": "form",
            "target": "current",
        }
