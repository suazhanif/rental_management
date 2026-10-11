# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
{
    "name": """Advanced Property Sale & Rental Management | Real Estate
     | Property Sales | Property Rental | Property Management""",
    "description": """
        - Property Salecd ~/odoo19/custom/rental_management

        - Property Rental
        - Lease Contract
        - Landlord Management
        - Customer Management
        - Property Maintenance
        - Customer Recurring Invoice
        - Property List
    """,
    "summary": """
        Property Sale & Rental Management
    """,
    "version": "3.4.0",
    "author": "Baramej® Business and Digital Technology Center LLC",
    "company": "Baramej®",
    "maintainer": "Baramej®",
    "website": "https://baramej.io/en",
    "category": "Realestate",
    "depends": ["mail", "contacts", "account", "hr", "maintenance", "crm", "website"],
    "data": [
        # security
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/security.xml",
        # 3.4.0 — Property Assignment: officer-vs-manager record rules
        "security/property_assignment_rules.xml",
        # 3.4.0 — Property Assignment: clear manager's implied officer group
        # (overrides the group record defined in groups.xml; must load
        # AFTER groups.xml so the update takes effect)
        "security/property_assignment_group_fix.xml",
        # Data
        "data/ir_cron.xml",
        "data/sequence.xml",
        "data/property_product_data.xml",
        "data/update_ir_cron.xml",
        # Printable Reports
        "report/loi_report_palm.xml",
        "report/loi_report_assalah.xml",
        "report/loi_report_assalah_family.xml",
        "report/loi_report_palm_apt.xml",
        "report/final_statement_report.xml",
        # wizard views
        "wizard/close_contract_wizard_views.xml",
        "wizard/vacate_wizard_views.xml",
        "wizard/occupy_wizard_views.xml",
        "wizard/employee_accommodation_search_views.xml",
        "wizard/contract_wizard_view.xml",
        "wizard/tenancy_payment_wizard_view.xml",
        "wizard/property_sale_wizard_view.xml",
        "wizard/property_maintenance_wizard_view.xml",
        "wizard/booking_wizard_view.xml",
        # "wizard/property_sale_tenancy_xls_report_view.xml",
        "wizard/landlord_tenancy_sold_xls_view.xml",
        "wizard/active_contract_view.xml",
        "wizard/subproject_creation_view.xml",
        "wizard/unit_creation_view.xml",
        "wizard/agreement_preview_view.xml",
        "wizard/dual_accommodation_approval_wizard_view.xml",
        "wizard/tenancy_reject_wizard_view.xml",
        "wizard/occupancy_report_wizard_view.xml",
        "wizard/outstanding_report_wizard_views.xml",
        "wizard/vacant_report_wizard_views.xml",
        "wizard/property_report_wizard_views.xml",
        "wizard/tenancy_list_report_wizard_views.xml",
        # Views
        "views/assets.xml",
        "views/shift_occupy_views.xml",
        "views/occupy_details_views.xml",
        "views/property_details_view.xml",
        "views/property_document_view.xml",
        "views/user_type_view.xml",
        "views/tenancy_details_view.xml",
        "views/contract_duration_view.xml",
        "views/rent_invoice_view.xml",
        "views/property_amenities_view.xml",
        "views/property_specification_view.xml",
        "views/property_vendor_view.xml",
        "views/property_tag_view.xml",
        "views/property_handover_material_views.xml",
        "views/product_product_inherit_view.xml",
        "views/property_invoice_inherit.xml",
        "views/res_config_setting_view.xml",
        "views/property_res_city.xml",
        "views/nearby_connectivity_view.xml",
        "views/agreement_template_view.xml",
        "views/configuration_views.xml",
        "views/property_region_views.xml",
        "views/property_project_view.xml",
        "views/property_sub_project_views.xml",
        "views/rent_bill_view.xml",
        "views/penalty_invoice_view.xml",
        "views/sale_invoice_view.xml",
        "views/templates/property_web_template.xml",
        # Inherit Views
        "views/hr_employee_inherit.xml",
        "views/maintenance_product_inherit.xml",
        "views/property_maintenance_view.xml",
        "views/property_crm_lead_inherit_view.xml",
        "views/occupy_details_dual_approval_inherit_view.xml",
        # 3.4.0 — Property Assignment: user_ids M2M widget via view inheritance
        "views/property_assignment_inherit_views.xml",
        # Report views
        "report/tenancy_details_report_template.xml",
        "report/property_details_report.xml",
        "report/property_sold_report.xml",
        "report/invoice_report_inherit.xml",
        "report/loi_report_palm.xml",
        # Mail Template
        "data/tenancy_expiry_reminder_mail_template.xml",
        "data/active_contract_mail_template.xml",
        "data/tenancy_reminder_mail_template.xml",
        "data/property_book_mail_template.xml",
        "data/property_sold_mail_template.xml",
        "data/sale_invoice_mail_template.xml",
        "data/penalty_invoice_mail_template.xml",
        "data/tenancy_approval_request_mail_template.xml",
        "data/tenancy_approval_decision_mail_template.xml",
        "data/dual_accommodation_expiry_reminder_template.xml",
        "data/non_company_expiry_reminder_template.xml",
        "views/owner_dashboard_views.xml",
        # menus
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "rental_management/static/src/js/lib/jquery.js",
            "rental_management/static/src/xml/template.xml",
            "rental_management/static/src/scss/style.scss",
            "rental_management/static/src/js/lib/index.js",
            "rental_management/static/src/js/lib/map.js",
            "rental_management/static/src/js/lib/xy.js",
            "rental_management/static/src/js/lib/worldLow.js",
            "rental_management/static/src/js/lib/Animated.js",
            "rental_management/static/src/js/lib/apexcharts.js",
            "rental_management/static/src/js/rental.js",
            "rental_management/static/src/components/**/*",
            "rental_management/static/src/views/**/*",
            "rental_management/static/src/js/owner_dashboard.js",
            "rental_management/static/src/css/owner_dashboard.css",
            "rental_management/static/src/xml/owner_dashboard.xml",
        ],
        "web.assets_frontend": [
            "rental_management/static/src/css/extra.css",
        ],
    },
    "images": [
        "static/description/property-rental.gif",
    ],
    "license": "OPL-1",
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 250,
    "currency": "USD",
}
