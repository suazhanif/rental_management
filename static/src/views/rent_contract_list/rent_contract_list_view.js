/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { RentalContractDashboard } from '@rental_management/components/rent_contract_dashboard';

export class RentalContractDashboardRenderer extends ListRenderer {};

RentalContractDashboardRenderer.template = 'rental_management.RentalContractListView';
RentalContractDashboardRenderer.components= Object.assign({}, ListRenderer.components, {RentalContractDashboard})

export const RentalContractDashboardListView = {
    ...listView,
    Renderer: RentalContractDashboardRenderer,
};

registry.category("views").add("rental_contract_dashboard_list", RentalContractDashboardListView);