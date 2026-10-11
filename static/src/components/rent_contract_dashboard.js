/** @odoo-module **/

import { session } from '@web/session';
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart} from "@odoo/owl";

export class RentalContractDashboard extends Component {
    setup() {
        this.action = useService('action');
        this.orm = useService("orm");
        this.state = useState({
            'tenancy_data': {}
        })
        onWillStart(async ()=>{
            const data = await this.orm.call('tenancy.details', 'retrieve_contract_list_dashboard_data', []);
            this.state.tenancy_data = data
        })


    }
    async viewContract(field, type) {
        let domain, context;
        domain = [[field, '=', type]]
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contracts',
            res_model: 'tenancy.details',
            view_mode: 'list',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            target: 'current',
            context: context,
            domain: domain,
        }, {
            pushState: false,
            stackPosition: "replaceCurrentAction",
        });
    }
}

RentalContractDashboard.template = 'rental_management.RentalContractDashboard';
