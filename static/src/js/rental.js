/** @odoo-module **/
import {registry} from "@web/core/registry";
import {Layout} from "@web/search/layout";
import {getDefaultConfig} from "@web/views/view";
import {useService} from "@web/core/utils/hooks";
import {useDebounced} from "@web/core/utils/timing";
import {session} from "@web/session";
import {Domain} from "@web/core/domain";
import {sprintf} from "@web/core/utils/strings";
import {cookie as cookieManager} from "@web/core/browser/cookie";
//cookieManager.get("color_scheme")


const {Component, useSubEnv, useState, onMounted, onWillStart, useRef} = owl;
import {loadJS, loadCSS} from "@web/core/assets"

export class RentalDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            propertyStats: {
                'total_property': 0,
                'avail_property': 0,
                'sold_property': 0,
                'booked_property': 0,
                'sale_property': 0,
                'lease_property': 0,
                'sold_total': "0",
                'sale_sold': 0,
                'booked': 0,
                'draft_contract': 0,
                'running_contract': 0,
                'expire_contract': 0,
                'pending_invoice': 0,
                'rent_total': "0",
                'region_count': 0,
                'project_count': 0,
                'subproject_count': 0,
                'landlord_count': 0,
                'customer_count': 0,
                'pending_invoice_sale': 0,
                'close_contract': 0,
                'extend_contract': 0,
                'refund': 0,
            },
            propertyType: {'x-axis': [], 'y-axis': []},
        });
        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });
        this.propertyType = useRef('propertyType');
        this.propertyStages = useRef('propertyStages');
        this.tenancyTopBroker = useRef('tenancyTopBroker');
        this.soldTopBroker = useRef('soldTopBroker');
        this.tenancyDuePaid = useRef('tenancyDuePaid');
        this.soldDuePaid = useRef('soldDuePaid');
        this.worldMap = useRef('worldMap');
        onWillStart(async () => {
            let propertyData = await this.orm.call('property.details', 'get_property_stats', []);
            if (propertyData) {
                this.state.propertyStats = propertyData;
                this.state.propertyType = {
                    'x-axis': propertyData['property_type'][0],
                    'y-axis': propertyData['property_type'][1]
                }
                this.state.propertyStages = {
                    'x-axis': propertyData['property_stage'][0],
                    'y-axis': propertyData['property_stage'][1]
                }
                this.state.tenancyTopBroker = {
                    'x-axis': propertyData['tenancy_top_broker'][0],
                    'y-axis': propertyData['tenancy_top_broker'][1]
                }
                this.state.soldTopBroker = {
                    'x-axis': propertyData['tenancy_top_broker'][2],
                    'y-axis': propertyData['tenancy_top_broker'][3]
                }
                this.state.tenancyDuePaid = {
                    'x-axis': propertyData['due_paid_amount'][2],
                    'y-axis': propertyData['due_paid_amount'][3]
                }
                this.state.soldDuePaid = {
                    'x-axis': propertyData['due_paid_amount'][0],
                    'y-axis': propertyData['due_paid_amount'][1]
                }
                this.state.propertyMapData = propertyData['property_map_data']
            }
        });
        onMounted(() => {
            this.renderPropertyType(this.propertyType.el, this.state.propertyType);
            this.renderTenancyTopBroker();
            this.renderSoldTopBroker();
            this.renderTenancyDuePaid();
            this.renderSoldDuePaid();
            this.renderMapProperties(this.worldMap.el, this.state.propertyMapData);
        })
    }

    renderPropertyType(div, sessionData) {
        var root = am5.Root.new(div);
        root.setThemes([
            am5themes_Animated.new(root)
        ]);
        var data = [{
            name: "Land",
            steps: sessionData['y-axis'][0],
            pictureSettings: {
                src: "/rental_management/static/src/img/land-dash.svg"
            }
        }, {
            name: "Residential",
            steps: sessionData['y-axis'][1],
            pictureSettings: {
                src: "/rental_management/static/src/img/re-dash.svg"
            }
        }, {
            name: "Commercial",
            steps: sessionData['y-axis'][2],
            pictureSettings: {
                src: "/rental_management/static/src/img/come-dash.svg"
            }
        }, {
            name: "Industrial",
            steps: sessionData['y-axis'][3],
            pictureSettings: {
                src: "/rental_management/static/src/img/ind-dash.svg"
            }
        }];
        var chart = root.container.children.push(
            am5xy.XYChart.new(root, {
                panX: false,
                panY: false,
                wheelX: "none",
                wheelY: "none",
                paddingBottom: 50,
                paddingTop: 40,
                paddingLeft: 0,
                paddingRight: 0
            })
        );
        var xRenderer = am5xy.AxisRendererX.new(root, {
            minorGridEnabled: true,
            minGridDistance: 60
        });
        xRenderer.grid.template.set("visible", false);
        var xAxis = chart.xAxes.push(
            am5xy.CategoryAxis.new(root, {
                paddingTop: 40,
                categoryField: "name",
                renderer: xRenderer
            })
        );
        var yRenderer = am5xy.AxisRendererY.new(root, {});
        yRenderer.grid.template.set("strokeDasharray", [3]);

        var yAxis = chart.yAxes.push(
            am5xy.ValueAxis.new(root, {
                min: 0,
                renderer: yRenderer
            })
        );
        var series = chart.series.push(
            am5xy.ColumnSeries.new(root, {
                name: "Income",
                xAxis: xAxis,
                yAxis: yAxis,
                valueYField: "steps",
                categoryXField: "name",
                sequencedInterpolation: true,
                calculateAggregates: true,
                maskBullets: false,
                tooltip: am5.Tooltip.new(root, {
                    dy: -30,
                    pointerOrientation: "vertical",
                    labelText: "{valueY}"
                })
            })
        );
        series.columns.template.setAll({
            strokeOpacity: 0,
            cornerRadiusBR: 10,
            cornerRadiusTR: 10,
            cornerRadiusBL: 10,
            cornerRadiusTL: 10,
            maxWidth: 50,
            fillOpacity: 0.8
        });
        var currentlyHovered;
        series.columns.template.events.on("pointerover", function (e) {
            handleHover(e.target.dataItem);
        });
        series.columns.template.events.on("pointerout", function (e) {
            handleOut();
        });

        function handleHover(dataItem) {
            if (dataItem && currentlyHovered != dataItem) {
                handleOut();
                currentlyHovered = dataItem;
                var bullet = dataItem.bullets[0];
                bullet.animate({
                    key: "locationY",
                    to: 1,
                    duration: 600,
                    easing: am5.ease.out(am5.ease.cubic)
                });
            }
        }

        function handleOut() {
            if (currentlyHovered) {
                var bullet = currentlyHovered.bullets[0];
                bullet.animate({
                    key: "locationY",
                    to: 0,
                    duration: 600,
                    easing: am5.ease.out(am5.ease.cubic)
                });
            }
        }

        var circleTemplate = am5.Template.new({});
        series.bullets.push(function (root, series, dataItem) {
            var bulletContainer = am5.Container.new(root, {});
            var circle = bulletContainer.children.push(
                am5.Circle.new(
                    root,
                    {
                        radius: 34
                    },
                    circleTemplate
                )
            );
            var maskCircle = bulletContainer.children.push(
                am5.Circle.new(root, {radius: 27})
            );
            var imageContainer = bulletContainer.children.push(
                am5.Container.new(root, {
                    mask: maskCircle
                })
            );
            var image = imageContainer.children.push(
                am5.Picture.new(root, {
                    templateField: "pictureSettings",
                    centerX: am5.p50,
                    centerY: am5.p50,
                    width: 60,
                    height: 60
                })
            );
            return am5.Bullet.new(root, {
                locationY: 0,
                sprite: bulletContainer
            });
        });
        series.set("heatRules", [
            {
                dataField: "valueY",
                min: am5.color(0xe5dc36),
                max: am5.color(0x5faa46),
                target: series.columns.template,
                key: "fill"
            },
            {
                dataField: "valueY",
                min: am5.color(0xe5dc36),
                max: am5.color(0x5faa46),
                target: circleTemplate,
                key: "fill"
            }
        ]);
        series.data.setAll(data);
        xAxis.data.setAll(data);
        var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {}));
        cursor.lineX.set("visible", false);
        cursor.lineY.set("visible", false);

        cursor.events.on("cursormoved", function () {
            var dataItem = series.get("tooltip").dataItem;
            if (dataItem) {
                handleHover(dataItem);
            } else {
                handleOut();
            }
        });
        series.appear();
        chart.appear(1000, 100);
    }

    renderTenancyTopBroker() {
        var options = {
            series: [{
                name: "Rent Contracts",
                data: this.state.tenancyTopBroker['y-axis']
            }],
            chart: {
                height: 200,
                type: 'bar',
            },
            colors: ['#EF745C', '#D06257', '#B15052', '#923E4D', '#722B47'],
            plotOptions: {
                bar: {
                    columnWidth: '40%',
                    distributed: true,
                }
            },
            dataLabels: {
                enabled: true
            },
            legend: {
                show: true
            },
            xaxis: {
                categories: this.state.tenancyTopBroker['x-axis'],
                labels: {
                    style: {
                        colors: ['#EF745C', '#D06257', '#B15052', '#923E4D', '#722B47'],
                        fontSize: '12px'
                    }
                }
            }
        };
        this.renderGraph(this.tenancyTopBroker.el, options);
    }

    renderSoldTopBroker() {
        var options = {
            series: [{
                name: "Sale Contracts",
                data: this.state.soldTopBroker['y-axis']
            }],
            chart: {
                height: 200,
                type: 'bar',
            },
            colors: ['#11D3F3', '#38DEDF', '#5FE8CB', '#86F3B6', '#ADFDA2'],
            plotOptions: {
                bar: {
                    columnWidth: '40%',
                    distributed: true,
                }
            },
            dataLabels: {
                enabled: true
            },
            legend: {
                show: true
            },
            xaxis: {
                categories: this.state.soldTopBroker['x-axis'],
                labels: {
                    style: {
                        colors: ['#11D3F3', '#38DEDF', '#5FE8CB', '#86F3B6', '#ADFDA2'],
                        fontSize: '12px'
                    }
                }
            }
        };
        this.renderGraph(this.soldTopBroker.el, options);
    }

    renderTenancyDuePaid() {
        const options = {
            series: this.state.tenancyDuePaid['y-axis'],
            chart: {
                type: 'pie',
                height: 300
            },
            colors: ['#FF884B', '#64E291'],
            dataLabels: {
                enabled: false
            },
            labels: this.state.tenancyDuePaid['x-axis'],
            legend: {
                position: 'bottom',
            },

        };
        this.renderGraph(this.tenancyDuePaid.el, options);
    }

    renderSoldDuePaid() {
        const options = {
            series: this.state.soldDuePaid['y-axis'],
            chart: {
                type: 'pie',
                height: 225
            },
            colors: ['#FF884B', '#64E291'],
            dataLabels: {
                enabled: false
            },
            labels: this.state.soldDuePaid['x-axis'],
            legend: {
                position: 'bottom',
            },
        };
        this.renderGraph(this.soldDuePaid.el, options);
    }

    renderMapProperties(div, sessionData) {
        const root = am5.Root.new(div);
        root.setThemes([am5themes_Animated.new(root)]);
        const chart = root.container.children.push(
            am5map.MapChart.new(root, {
                panX: "rotateX",
                panY: "translateY",
                projection: am5map.geoMercator(),
            })
        );
        chart.set("zoomControl", am5map.ZoomControl.new(root, {}));
        const polygonSeries = chart.series.push(
            am5map.MapPolygonSeries.new(root, {
                geoJSON: am5geodata_worldLow,
                exclude: ["AQ"]
            })
        );
        polygonSeries.mapPolygons.template.setAll({
            fill: am5.color(0xdadada)
        });
        const pointSeries = chart.series.push(am5map.ClusteredPointSeries.new(root, {}));

        pointSeries.set("clusteredBullet", function (root) {
            const container = am5.Container.new(root, {
                cursorOverStyle: "pointer"
            });
            const circle1 = container.children.push(am5.Circle.new(root, {
                radius: 8,
                tooltipY: 0,
                fill: am5.color(0xff8c00)
            }));
            const circle2 = container.children.push(am5.Circle.new(root, {
                radius: 12,
                fillOpacity: 0.3,
                tooltipY: 0,
                fill: am5.color(0xff8c00)
            }));
            const circle3 = container.children.push(am5.Circle.new(root, {
                radius: 16,
                fillOpacity: 0.3,
                tooltipY: 0,
                fill: am5.color(0xff8c00)
            }));
            const label = container.children.push(am5.Label.new(root, {
                centerX: am5.p50,
                centerY: am5.p50,
                fill: am5.color(0xffffff),
                populateText: true,
                fontSize: "8",
                text: "{value}"
            }));
            container.events.on("click", function (e) {
                pointSeries.zoomToCluster(e.target.dataItem);
            });
            return am5.Bullet.new(root, {
                sprite: container
            });
        });

        // Modified to use dynamic colors based on status
        pointSeries.bullets.push(function (root, series, dataItem) {
            // Get the data for this point
            const data = dataItem.dataContext;

            // Determine color based on status
            let fillColor;

            switch (data.status) {
                case "available":
                    fillColor = am5.color(0x4CAF50); // Green for available
                    break;
                case "booked":
                    fillColor = am5.color(0xFFC107); // Amber for booked
                    break;
                case "on_lease":
                    fillColor = am5.color(0xF44336); // Red for on_lease
                    break;
                case "sale":
                    fillColor = am5.color(0x9C27B0); // Purple for sale
                    break;
                case "sold":
                    fillColor = am5.color(0xFF9800); // Orange for sold
                    break;
                default:
                    fillColor = am5.color(0x0f0f0f); // Black for unknown status
            }

            const circle = am5.Circle.new(root, {
                radius: 6,
                tooltipY: 0,
                fill: fillColor,
                tooltipText: "{title}"
            });

            return am5.Bullet.new(root, {
                sprite: circle
            });
        });

        for (let i = 0; i < sessionData.length; i++) {
            const city = sessionData[i];
            addCity(city.longitude, city.latitude, city.title, city.status);
        }

        function addCity(longitude, latitude, title, status) {
            pointSeries.data.push({
                geometry: {type: "Point", coordinates: [longitude, latitude]},
                title: title,
                status: status
            });
        }

        chart.appear(1000, 100);
    }

    renderGraph(el, options) {
        const graphData = new ApexCharts(el, options);
        graphData.render();
    }

    viewProperties(type) {
        let domain, context;
        let name = this.getPropertyName(type);
        if (type === 'all') {
            domain = []
        } else {
            domain = [['stage', '=', type]]
        }
        context = {'create': false}
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: 'property.details',
            view_mode: 'kanban',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    viewPartner(type) {
        let name = "";
        if (type == 'customer') {
            name = "Customers"
        } else if (type == 'landlord') {
            name = 'Landlords'
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: 'res.partner',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
            context: {'create': false},
            domain: [['user_type', '=', type]],
        });
    }

    viewPropertySale(type) {
        let domain, context;
        let model = 'property.vendor'
        let name = this.getPropertyName(type);
        domain = [['stage', '=', type]]
        if (type == 'not_paid') {
            domain = [['payment_state', '=', 'not_paid'], ['sold_id', '!=', false]]
            model = 'account.move'
        }
        context = {'create': false}
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: model,
            view_mode: 'kanban',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    viewPropertyTenancies(type) {
        let domain, context, model;
        let name = this.getPropertyName(type);
        if (type === 'rent_total') {
            domain = ['|', ['type', '=', 'rent'], ['type', '=', 'full_rent']]
            model = 'rent.invoice'
        } else if (type === 'not_paid') {
            domain = [['payment_state', '=', type]]
            model = 'rent.invoice'
        } else if (type === 'extend_contract') {
            model = 'tenancy.details'
            domain = [['is_extended', '=', true]]
        } else {
            model = 'tenancy.details'
            domain = [['contract_type', '=', type]]
        }
        context = {'create': false}
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: model,
            view_mode: 'list',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    viewStatistic(type) {
        let name = ""
        let model = ""
        let context = {'create': false}
        if (type == 'region') {
            name = "Regions"
            model = "property.region"
        } else if (type == 'project') {
            name = "Projects"
            model = "property.project"
        } else if (type == 'sub_project') {
            name = "Sub Projects"
            model = "property.sub.project"
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: model,
            view_mode: 'list',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });

    }

    getPropertyName(type) {
        let name;
        if (type === 'all') {
            name = 'All Properties';
        } else if (type === 'booked') {
            name = 'Booked Properties'
        } else if (type === 'sale') {
            name = 'OnSale Properties'
        } else if (type === 'on_lease') {
            name = 'On Leased Properties'
        } else if (type === 'sold') {
            name = 'Sold Properties'
        } else if (type === 'available') {
            name = 'Available Properties'
        } else if (type === 'sold_total') {
            name = 'Sold Properties Total'
        } else if (type === 'new_contract') {
            name = 'Draft Contract'
        } else if (type === 'running_contract') {
            name = 'Running Contract'
        } else if (type === 'expire_contract') {
            name = 'Expire Contract'
        } else if (type === 'rent_total') {
            name = 'Total Rent Amount'
        } else if (type === 'not_paid') {
            name = 'Pending Invoice'
        } else if (type === 'close_contract') {
            name = 'Close Contracts'
        } else if (type === 'extend_contract') {
            name = 'Extended Contracts'
        } else if (type === 'refund') {
            name = 'Refunded Sale Contracts'
        } else {
            name = 'Properties'
        }
        return name;
    }
}

RentalDashboard.template = "rental_management.rental_dashboard";
registry.category("actions").add("property_dashboard", RentalDashboard);
