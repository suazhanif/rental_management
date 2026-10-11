from odoo.tools import html2plaintext

def serialize_invoice(invoice, today=None):
    """Serialize a rent.invoice record into a flat dictionary."""
    from odoo import fields
    if today is None:
        today = fields.Date.today()

    rent_invoice = invoice.rent_invoice_id
    due_date = rent_invoice.invoice_date_due or invoice.invoice_date or today
    days_remaining = (due_date - today).days
    currency = invoice.tenancy_id.currency_id

    return {
        "id": invoice.id,
        "amount": float(rent_invoice.amount_residual if rent_invoice.amount_residual > 0 else invoice.amount),
        "currencySymbol": currency.symbol or currency.name or "",
        "dueDate": str(due_date),
        "daysRemaining": days_remaining,
        "invoiceId": rent_invoice.id,
        "invoiceUrl": f"/my/invoices/{rent_invoice.id}?access_token={rent_invoice._portal_ensure_token()}",
        "contractId": invoice.tenancy_id.id,
        "contractSequence": invoice.tenancy_id.tenancy_seq,
    }


def serialize_contract(contract):
    """
    Serialize a tenancy.details record into a flat dictionary.
    Returns only: id, sequence, start_date, end_date, property address,
    property_id, contract state, agreement download link, terms & conditions.
    """
    address_parts = []
    property = contract.property_id
    if property.street:
        address_parts.append(property.street)
    if property.street2:
        address_parts.append(property.street2)
    if property.building_no:
        address_parts.append(property.building_no)
    if property.city_id and property.city_id.name:
        address_parts.append(property.city_id.name)
    if property.state_id and property.state_id.name:
        address_parts.append(property.state_id.name)
    if property.zip:
        address_parts.append(property.zip)
    if property.country_id and property.country_id.name:
        address_parts.append(property.country_id.name)

    property_address = ", ".join(address_parts) if address_parts else None

    return {
        "id": contract.id,
        "name": contract.tenancy_seq,
        "startDate": str(contract.start_date) if contract.start_date else None,
        "endDate": str(contract.end_date) if contract.end_date else None,
        "propertyAddress": property_address,
        "propertyId": property.id if property else None,
        "contractState": contract.contract_type,
        "agreement": html2plaintext(contract.agreement).strip() if contract.agreement else None,
        "termsAndConditions": html2plaintext(contract.term_condition).strip() if contract.term_condition else None,
    }