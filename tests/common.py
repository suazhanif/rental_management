import datetime
import logging

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)
logging.getLogger("odoo.addons.mail").setLevel(logging.ERROR)


@tagged("enterprise_related", "rental_management")
class CreateRentalData(TransactionCase):
    """Test property rental management"""

    @classmethod
    def setUpClass(cls):
        """Helper test class to create rental management test data."""
        super().setUpClass()
        cls.Mail = cls.env["mail.mail"].with_context(test_mode=True)
        cls.env["ir.config_parameter"].sudo().set_param(
            "tk_rental_management.deposit_item_id",
            str(cls.env["product.product"].create({"name": "Booking Item"}).id),
        )
        cls.deposit_item_id = int(
            cls.env["ir.config_parameter"]
            .sudo()
            .get_param("tk_rental_management.deposit_item_id")
        )
        cls.broker_one = cls._create_user(
            "Broker One", "broker", email="email@gmail.com"
        )
        cls.customer_one = cls._create_user(
            "Customer One", "customer", email="email@gmail.com"
        )
        cls.company = cls.env.ref("base.main_company")
        cls.journal_bank = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        cls.company_currency = cls.env.company.currency_id
        cls.tax = cls.env["account.tax"].create(
            {
                "name": "10% incl",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 10.0,
            }
        )
        cls.duration = cls.env["contract.duration"].create(
            {"duration": "Ten Month", "month": 10, "rent_unit": "Month"}
        )
        cls.duration_year = cls.env["contract.duration"].create(
            {"duration": "Ten Year", "month": 10, "rent_unit": "Year"}
        )
        cls.test_landlord = cls.env["res.partner"].create(
            {"name": "Landlord", "user_type": "landlord"}
        )

    @classmethod
    def _create_project(
        cls,
        name,
        project_sequence,
        project_for,
        property_type,
        property_subtype_id,
        date_of_project=None,
        region_id=None,
    ):
        """Create and return a property project record."""
        cls.env = cls.env(context=dict(cls.env.context, test_mode=True))

        # Get Default Currency
        cls.currency = cls.env["res.currency"].search([("name", "=", "USD")], limit=1)
        if not cls.currency:
            cls.currency = cls.env["res.currency"].create(
                {"name": "USD", "symbol": "$", "rounding": 0.01, "decimal_places": 2}
            )

        return cls.env["property.project"].create(
            {
                "name": name,
                "project_sequence": project_sequence,
                "project_for": project_for,
                "property_type": property_type,
                "property_subtype_id": property_subtype_id,
                "landlord_id": cls.test_landlord.id,
                "company_id": cls.company.id,
                "currency_id": cls.currency.id,
                "date_of_project": (
                    date_of_project if date_of_project else datetime.datetime.today()
                ),
                "region_id": region_id,
            }
        )

    @classmethod
    def _create_units_wizard(
        cls, total_floors, units_per_floor, floor_start_from, active_id, unit_from
    ):
        """Create a unit creation wizard record."""
        return (
            cls.env["unit.creation"]
            .with_context(active_id=active_id, unit_from=unit_from)
            .create(
                {
                    "total_floors": total_floors,
                    "units_per_floor": units_per_floor,
                    "floor_start_from": floor_start_from,
                }
            )
        )

    @classmethod
    def _create_sub_project_wizard(
        cls, name, project_sequence, floors, units_per_floor, active_id
    ):
        """Create a subproject creation wizard record."""
        return (
            cls.env["subproject.creation"]
            .with_context(active_id=active_id)
            .create(
                {
                    "name": name,
                    "project_sequence": project_sequence,
                    "floors": floors,
                    "units_per_floor": units_per_floor,
                }
            )
        )

    @classmethod
    def _create_units(
        cls,
        name,
        sale_lease,
        stage,
        type,
        price,
        property_seq=None,
        is_maintenance_service=None,
        maintenance_type=None,
        total_maintenance=None,
        rent_unit=None,
        extra_service_ids=None,
        maintenance_rent_type=None,
        landlord_id=None,
    ):
        """Create and return a property unit record."""
        return cls.env["property.details"].create(
            {
                "name": name,
                "property_seq": property_seq,
                "sale_lease": sale_lease,
                "stage": stage,
                "type": type,
                "price": price,
                "is_maintenance_service": is_maintenance_service,
                "maintenance_type": maintenance_type,
                "total_maintenance": total_maintenance,
                "rent_unit": rent_unit,
                "extra_service_ids": extra_service_ids,
                "maintenance_rent_type": maintenance_rent_type,
                "landlord_id": landlord_id,
            }
        )

    @classmethod
    def _create_service(
        cls, name, is_extra_service_product: bool, lst_price: int, standard_price: int
    ):
        """Create and return a product service record."""
        return cls.env["product.product"].create(
            {
                "name": name,
                "is_extra_service_product": is_extra_service_product,
                "lst_price": lst_price,
                "standard_price": standard_price,
            }
        )

    @classmethod
    def _create_extra_service(cls, service_id, service_type, property_id):
        """Create and return an extra service line record."""
        return cls.env["extra.service.line"].create(
            {
                "service_id": service_id,
                "service_type": service_type,
                "property_id": property_id,
            }
        )

    @classmethod
    def _create_user(cls, name, user_type, email=None):
        """Create and return a partner user record."""
        return cls.env["res.partner"].create(
            {"name": name, "user_type": user_type, "email": email}
        )

    # For Sale
    @classmethod
    def _create_booking_wizard(
        cls,
        active_id=None,
        customer_id=None,
        property_id=None,
        book_price=None,
        ask_price=None,
        broker_id=None,
        is_any_broker=None,
        commission_type=None,
        broker_commission=None,
        broker_commission_percentage=None,
        commission_from=None,
        from_inquiry=None,
        note=None,
        lead_id=None,
        is_any_maintenance=None,
        total_maintenance=None,
        is_utility_service=None,
        total_service=None,
        booking_item_id=None,
        broker_item_id=None,
    ):
        """Create a booking wizard record for property sale."""
        return (
            cls.env["booking.wizard"]
            .with_context(active_id=active_id)
            .create(
                {
                    "customer_id": customer_id,
                    "property_id": property_id,
                    "book_price": book_price,
                    "ask_price": ask_price,
                    "broker_id": broker_id,
                    "commission_type": commission_type,
                    "broker_commission": broker_commission,
                    "broker_commission_percentage": broker_commission_percentage,
                    "commission_from": commission_from,
                    "from_inquiry": from_inquiry,
                    "note": note,
                    "lead_id": lead_id,
                    "is_any_maintenance": is_any_maintenance,
                    "total_maintenance": total_maintenance,
                    "is_utility_service": is_utility_service,
                    "total_service": total_service,
                    "is_any_broker": is_any_broker,
                    "booking_item_id": booking_item_id,
                    "broker_item_id": broker_item_id,
                }
            )
        )

    # For Rent

    @classmethod
    def _create_contract_wizard(cls, data, active_id, active_model):
        """Create a contract wizard record for property rent."""
        return (
            cls.env["contract.wizard"]
            .with_context(active_id=active_id, active_model=active_model)
            .create(data)
        )

    @classmethod
    def _create_duration(cls, duration: str, month: int, rent_unit: str):
        """Create and return a contract duration record."""
        return cls.env["contract.duration"].create(
            {"duration": duration, "month": month, "rent_unit": rent_unit}
        )

    @classmethod
    def _create_maintenance_wizard(
        cls,
        active_id,
        name=None,
        property_id=None,
        rent_contract_id=None,
        sell_contract_id=None,
        maintenance_type_id=None,
        maintenance_team_id=None,
        is_property_maintenance=None,
        is_renting_contract_maintenance=None,
        is_selling_contract_maintenance=None,
    ):
        """Create a property vendor installment wizard record."""
        return (
            cls.env["maintenance.wizard"]
            .with_context(active_id=active_id)
            .create(
                {
                    "name": name,
                    "property_id": property_id,
                    "rent_contract_id": rent_contract_id,
                    "sell_contract_id": sell_contract_id,
                    "maintenance_type_id": maintenance_type_id,
                    "maintenance_team_id": maintenance_team_id,
                    "is_property_maintenance": is_property_maintenance,
                    "is_renting_contract_maintenance": is_renting_contract_maintenance,
                    "is_selling_contract_maintenance": is_selling_contract_maintenance,
                }
            )
        )

    @classmethod
    def _create_installment_wizard(
        cls,
        active_id,
        company_id=None,
        currency_id=None,
        property_id=None,
        customer_id=None,
        final_price=None,
        sold_invoice_id=None,
        broker_id=None,
        is_any_broker=None,
        quarter=None,
        duration_id=None,
        payment_term=None,
        start_date=None,
        installment_item_id=None,
        is_taxes=None,
        taxes_ids=None,
    ):
        """Create an active contract record."""
        return (
            cls.env["property.vendor.wizard"]
            .with_context(active_id=active_id)
            .create(
                {
                    "company_id": company_id,
                    "currency_id": currency_id,
                    "property_id": property_id,
                    "customer_id": customer_id,
                    "final_price": final_price,
                    "sold_invoice_id": sold_invoice_id,
                    "broker_id": broker_id,
                    "is_any_broker": is_any_broker,
                    "quarter": quarter,
                    "duration_id": duration_id,
                    "payment_term": payment_term,
                    "start_date": start_date,
                    "installment_item_id": installment_item_id,
                    "is_taxes": is_taxes,
                    "taxes_ids": taxes_ids,
                }
            )
        )

    @classmethod
    def _create_active_contract(cls, active_id, type, contract_id, rent_unit):
        return (
            cls.env["active.contract"]
            .with_context(active_id=active_id)
            .create({"type": type, "contract_id": contract_id, "rent_unit": rent_unit})
        )

    @classmethod
    def _create_property_payment_wizard(
        cls,
        active_id,
        tenancy_id=None,
        customer_id=None,
        company_id=None,
        currency_id=None,
        type=None,
        description=None,
        invoice_date=None,
        rent_amount=None,
        amount=None,
        rent_invoice_id=None,
        service_id=None,
        tax_ids=None,
        is_invoice=None,
        is_bill=None,
        bill_type=None,
        vendor_id=None,
        vendor_phone=None,
        vendor_email=None,
    ):
        """Create a payment wizard record for property transactions."""
        return (
            cls.env["property.payment.wizard"]
            .with_context(active_id=active_id)
            .create(
                {
                    "tenancy_id": tenancy_id,
                    "customer_id": customer_id,
                    "company_id": company_id,
                    "currency_id": currency_id,
                    "type": type,
                    "description": description,
                    "invoice_date": invoice_date,
                    "rent_amount": rent_amount,
                    "amount": amount,
                    "rent_invoice_id": rent_invoice_id,
                    "service_id": service_id,
                    "tax_ids": tax_ids,
                    "is_invoice": is_invoice,
                    "is_bill": is_bill,
                    "bill_type": bill_type,
                    "vendor_id": vendor_id,
                    "vendor_phone": vendor_phone,
                    "vendor_email": vendor_email,
                }
            )
        )

    @classmethod
    def _create_payment_wizard(
        cls,
        active_id,
        tenancy_id=None,
        customer_id=None,
        company_id=None,
        currency_id=None,
        type=None,
        description=None,
        invoice_date=None,
        rent_amount=None,
        amount=None,
        rent_invoice_id=None,
        service_id=None,
        tax_ids=None,
        is_invoice=None,
        is_bill=None,
        bill_type=None,
        vendor_id=None,
        vendor_phone=None,
        vendor_email=None,
    ):
        """Create a contract service line record."""
        return (
            cls.env["property.payment.wizard"]
            .with_context(active_id=active_id)
            .create(
                {
                    "tenancy_id": tenancy_id,
                    "customer_id": customer_id,
                    "company_id": company_id,
                    "currency_id": currency_id,
                    "type": type,
                    "description": description,
                    "invoice_date": invoice_date,
                    "rent_amount": rent_amount,
                    "amount": amount,
                    "rent_invoice_id": rent_invoice_id,
                    "service_id": service_id,
                    "tax_ids": tax_ids,
                    "is_invoice": is_invoice,
                    "is_bill": is_bill,
                    "bill_type": bill_type,
                    "vendor_id": vendor_id,
                    "vendor_phone": vendor_phone,
                    "vendor_email": vendor_email,
                }
            )
        )

    @classmethod
    def _create_contract_service_line(
        cls,
        rent_contract_id=None,
        service_id=None,
        currency_id=None,
        company_id=None,
        price=None,
    ):
        return cls.env["contract.service.line"].create(
            {
                "rent_contract_id": rent_contract_id,
                "service_id": service_id,
                "currency_id": currency_id,
                "company_id": company_id,
                "price": price,
            }
        )

    @classmethod
    def _create_agreement_template(
        cls,
        name=None,
        company_id=None,
        agreement=None,
        template_variable_ids=None,
        model=None,
    ):
        """Create an agreement template record."""
        return cls.env["agreement.template"].create(
            {
                "name": name,
                "company_id": company_id,
                "agreement": agreement,
                "template_variable_ids": template_variable_ids,
                "model": model,
            }
        )

    @classmethod
    def _create_cities(cls, name):
        """Create a property city record."""
        return cls.env["property.res.city"].create({"name": name})

    @classmethod
    def _create_region(
        cls,
        name=None,
        city_ids=None,
        project_count=None,
        subproject_count=None,
        unit_count=None,
    ):
        """Create a property region record."""
        return cls.env["property.region"].create(
            {
                "name": name,
                "city_ids": city_ids,
                "project_count": project_count,
                "subproject_count": subproject_count,
                "unit_count": unit_count,
            }
        )

    # ------------------------------------------------------------------ #
    #  Approval workflow test helpers                                    #
    # ------------------------------------------------------------------ #
    @classmethod
    def _approve_for_activation(cls, contract):
        """Transition a draft contract to ``approved`` for tests.

        The approval workflow (added in 3.3.6) gates
        ``action_active_contract`` on ``contract_type == 'approved'``.
        Existing tests call ``action_active_contract`` directly on draft
        contracts; this helper performs the minimal write to bring the
        contract into the right state without exercising the full
        submit → manager-approve round trip.
        """
        if contract.contract_type == "new_contract":
            contract.write({"contract_type": "approved"})
