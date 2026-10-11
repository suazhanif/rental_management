/** @odoo-module **/

import { session } from '@web/session';
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart} from "@odoo/owl";

export class SaleContractDashboard extends Component {
    setup() {
        this.action = useService('action');
        this.orm = useService("orm");
        this.state = useState({
            'sale_contract_data': {}
        })
        onWillStart(async ()=>{
            const data = await this.orm.call('property.vendor', 'retrieve_sale_contract_list_dashboard_data', []);
            this.state.sale_contract_data = data
        })


    }
    async viewContract(field, type) {
        let domain, context;
        domain = [[field, '=', type]]
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contracts',
            res_model: 'property.vendor',
            view_mode: 'list',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
            domain: domain,
        }, {
            pushState: false,
            stackPosition: "replaceCurrentAction",
        });
    }
}

SaleContractDashboard.template = 'rental_management.SaleContractDashboard';
