/** @odoo-module **/

import { session } from '@web/session';
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart} from "@odoo/owl";

export class RentalPropertyDashboard extends Component {
    setup() {
        this.action = useService('action');
        this.orm = useService("orm");
        this.state = useState({
            'property_data': {}
        })
        onWillStart(async ()=>{
            const data = await this.orm.call('property.details', 'retrieve_list_dashboard_data', []);
            this.state.property_data = data
        })


    }
    viewAllProperties(status){
        let domain, context;
        if (status === 'all') {
           domain = []
        } else {
            domain = [['stage', '=', status]]
        }
        context = { 'create': true }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Properties',
            res_model: 'property.details',
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
    viewForRentProperties(type){
        let domain, context;
        if (type === 'all') {
           domain = [['stage','=','available'],['sale_lease','=','for_tenancy']]
        } else {
            domain = [['stage','=','available'],['sale_lease','=','for_tenancy'],['type','=', type]]
        }
        context = { 'create': true }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Properties',
            res_model: 'property.details',
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
    viewProperties(status, type){
        let domain, context;
        if (status === 'all') {
           domain = [['stage', '!=', 'draft'],['type','=',type]]
        } else {
            domain = [['stage', '=', status],['type','=', type]]
        }
        context = { 'create': true }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Properties',
            res_model: 'property.details',
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

RentalPropertyDashboard.template = 'rental_management.RentalPropertyDashboard';
