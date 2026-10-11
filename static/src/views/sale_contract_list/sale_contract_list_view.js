/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { SaleContractDashboard } from '@rental_management/components/sale_contract_dashboard';

export class SaleContractDashboardRenderer extends ListRenderer {};

SaleContractDashboardRenderer.template = 'rental_management.SaleContractListView';
SaleContractDashboardRenderer.components= Object.assign({}, ListRenderer.components, {SaleContractDashboard})

export const SaleContractDashboardListView = {
    ...listView,
    Renderer: SaleContractDashboardRenderer,
};

registry.category("views").add("sale_contract_dashboard_list",SaleContractDashboardListView);