import logging
from odoo import fields
from odoo.http import Controller, route, request
from .serializers import serialize_contract, serialize_invoice

_logger = logging.getLogger(__name__)


class ApiController(Controller):
    @route(
        "/api/v1/profile", type="jsonrpc", auth="user", methods=["POST"], cors="*"
    )
    def get_user_profile(self):
        """Returns user profile data"""
        user = request.env.user

        return {
            "id": user.id,
            "name": user.name,
        }

    @route(
        "/api/v1/tenant/contracts", type="jsonrpc", auth="user", methods=["POST"], cors="*"
    )
    def get_contracts(self, **kwargs):
        """Returns contracts for currently logged in user"""
        user = request.env.user
        Tenancy = request.env['tenancy.details'].sudo()
        limit = min(int(kwargs.get('limit', 50)), 100)
        offset = int(kwargs.get('offset', 0))
        domain = [('tenancy_id', '=', user.partner_id.id)]
        
        contracts = Tenancy.search(domain, limit=limit, offset=offset, order="create_date desc")

        contract_list = []
        for contract in contracts:
            contract_list.append(serialize_contract(contract))

        return contract_list

    @route(
        "/api/v1/tenant/invoices", type="jsonrpc", auth="user", methods=["POST"], cors="*"
    )
    def get_invoices(self, **kwargs):
        """Returns all unpaid rent invoices for the tenant"""
        user = request.env.user
        RentInvoice = request.env['rent.invoice'].sudo()
        limit = min(int(kwargs.get('limit', 50)), 100)
        offset = int(kwargs.get('offset', 0))

        domain = [
            ('tenancy_id.tenancy_id', '=', user.partner_id.id),
            ('rent_invoice_id', '!=', False),
            ('rent_invoice_id.payment_state', 'in', ['not_paid', 'partial']),
            ('type', 'in', ['rent', 'full_rent']),
        ]

        invoices = RentInvoice.search(domain, order='invoice_date asc, id asc', limit=limit, offset=offset)

        result = []
        today = fields.Date.today()

        for invoice in invoices:
            result.append(serialize_invoice(invoice, today))

        return result

    @route(
        "/api/v1/tenant/next-payment", type="jsonrpc", auth="user", methods=["POST"], cors="*"
    )
    def get_next_payment(self):
        """Returns the next upcoming unpaid rent invoice for the tenant"""
        user = request.env.user
        RentInvoice = request.env['rent.invoice'].sudo()
        
        # Find unpaid rent invoices for this tenant's contracts
        domain = [
            ('tenancy_id.tenancy_id', '=', user.partner_id.id),
            ('rent_invoice_id', '!=', False),
            ('rent_invoice_id.payment_state', 'in', ['not_paid', 'partial']),
            ('type', 'in', ['rent', 'full_rent']),
        ]
        
        # Get the earliest due invoice
        invoices = RentInvoice.search(domain, order='invoice_date asc, id asc', limit=1)

        if not invoices:
            return None

        return serialize_invoice(invoices[0])