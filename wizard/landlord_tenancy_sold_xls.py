import base64
from io import BytesIO

import xlwt
from odoo import fields, models


class LandlordSaleTenancy(models.TransientModel):
    """Landlord Sale tenancy excel report"""

    _name = "landlord.sale.tenancy"
    _description = "Landlord Tenancy And sale Report"
    _rec_name = "landlord_id"

    landlord_id = fields.Many2one(
        "res.partner", domain="[('user_type','=','landlord')]"
    )
    report_for = fields.Selection(
        [("tenancy", "Rent"), ("sold", "Property Sold")], string="Report For"
    )

    def action_tenancy_sold_xls_report(self):
        """Process tenancy sold xls report"""
        if self.report_for == "tenancy":
            sheet1_title = "RENT INFORMATION - " + self.landlord_id.name
            sheet2_title = "Rent Information - " + self.landlord_id.name + " : PAID"
            sheet3_title = "Rent Information - " + self.landlord_id.name + " : NOT PAID"
            sheet4_title = (
                "Rent Information - " + self.landlord_id.name + " : PARTIAL PAID"
            )
            sheet5_title = "Rent Bills - " + self.landlord_id.name
            workbook = xlwt.Workbook(encoding="utf-8")
            # <<<<<<<<<<<<< Sheet 1 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            sheet1 = workbook.add_sheet("Landlord wise Contracts")
            domain = [("landlord_id", "=", self.landlord_id.id)]
            record = self.env["rent.invoice"].search(domain)
            self.action_create_landlord_tenancy_report(
                sheet=sheet1, sheet_title=sheet1_title, record=record, workbook=workbook
            )
            # <<<<<<<<<<<<<<< Sheet 2 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            sheet2 = workbook.add_sheet("Paid Contracts", cell_overwrite_ok=True)
            record_paid = self.env["rent.invoice"].search(
                domain + [("payment_state", "=", "paid")]
            )
            self.action_create_landlord_tenancy_report(
                sheet=sheet2,
                sheet_title=sheet2_title,
                record=record_paid,
                workbook=workbook,
            )

            # <<<<<<<<<<<<<<<< Sheet 3 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            sheet3 = workbook.add_sheet("Not Paid Contracts", cell_overwrite_ok=True)
            record_not_paid = self.env["rent.invoice"].search(
                domain + [("payment_state", "=", "not_paid")]
            )
            self.action_create_landlord_tenancy_report(
                sheet=sheet3,
                sheet_title=sheet3_title,
                record=record_not_paid,
                workbook=workbook,
            )
            # <<<<<<<<<<<<<<<<<<<< Sheet 4 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            sheet4 = workbook.add_sheet(
                "Partial Paid Contracts", cell_overwrite_ok=True
            )
            record_partial_paid = self.env["rent.invoice"].search(
                domain + [("payment_state", "=", "partial")]
            )
            self.action_create_landlord_tenancy_report(
                sheet=sheet4,
                sheet_title=sheet4_title,
                record=record_partial_paid,
                workbook=workbook,
            )
            # <<<<<<<<<<<<<<<<<<<< Sheet 5 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            sheet5 = workbook.add_sheet("Contract Bills", cell_overwrite_ok=True)
            contract_bills = self.env["rent.bill"].search(
                [("vendor_id", "=", self.landlord_id.id)]
            )
            self.action_create_landlord_tenancy_report(
                sheet=sheet5,
                sheet_title=sheet5_title,
                record=contract_bills,
                workbook=workbook,
                is_bill_record=True,
            )

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())
            attachment = self.env["ir.attachment"].sudo()
            filename = self.landlord_id.name + " Rent.xls"
            attachment_id = attachment.create(
                {"name": filename, "type": "binary", "public": False, "datas": out}
            )
            if attachment_id:
                report = {
                    "type": "ir.actions.act_url",
                    "url": "/web/content/%s?download=true" % (attachment_id.id),
                    "target": "self",
                }
                return report
        elif self.report_for == "sold":
            name = "Sold Information - " + self.landlord_id.name
            workbook = xlwt.Workbook(encoding="utf-8")
            sheet1 = workbook.add_sheet(
                "Landlord wise Sold Information", cell_overwrite_ok=True
            )
            border_squre = xlwt.Borders()
            border_squre.top = xlwt.Borders.HAIR
            border_squre.left = xlwt.Borders.HAIR
            border_squre.right = xlwt.Borders.HAIR
            border_squre.bottom = xlwt.Borders.HAIR
            border_squre.top_colour = xlwt.Style.colour_map["gray50"]
            border_squre.bottom_colour = xlwt.Style.colour_map["gray50"]
            border_squre.right_colour = xlwt.Style.colour_map["gray50"]
            border_squre.left_colour = xlwt.Style.colour_map["gray50"]
            al = xlwt.Alignment()
            al.horz = xlwt.Alignment.HORZ_CENTER
            al.vert = xlwt.Alignment.VERT_CENTER
            date_format = xlwt.XFStyle()
            date_format.num_format_str = "mm/dd/yyyy"
            date_format.font.name = "Century Gothic"
            date_format.borders = border_squre
            date_format.alignment = al

            xlwt.add_palette_colour("custom_red", 0x21)
            workbook.set_colour_RGB(0x21, 240, 210, 211)
            xlwt.add_palette_colour("custom_green", 0x22)
            workbook.set_colour_RGB(0x22, 210, 241, 214)
            xlwt.add_palette_colour("custom_yellow", 0x23)
            workbook.set_colour_RGB(0x23, 255, 255, 224)
            xlwt.add_palette_colour("custom_blue", 0x24)
            workbook.set_colour_RGB(0x24, 240, 255, 255)

            red_bg = xlwt.easyxf(
                "align: vert centre, horiz right;"
                "pattern: pattern solid, fore_colour custom_red;"
                " font:name Century Gothic, bold on;"
                "border:  top hair, bottom hair, left hair, right hair,"
                " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
            )
            green_bg = xlwt.easyxf(
                "align: vert centre, horiz right;"
                "pattern: pattern solid, fore_colour custom_green; "
                "font:name Century Gothic, bold on;"
                "border:  top hair, bottom hair, left hair, right hair, "
                "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
            )
            # Font Color
            red = xlwt.easyxf(
                "align: vert centre, horiz center;"
                "font: color-index red, name Century Gothic;"
                "border:  top hair, bottom hair, left hair, right hair,"
                " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            green = xlwt.easyxf(
                "align: vert centre, horiz center;"
                "font: color-index green, name Century Gothic;"
                "border:  top hair, bottom hair, left hair, right hair,"
                " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            blue_gray = xlwt.easyxf(
                "align: vert centre, horiz center;"
                "font: color-index blue_gray, name Century Gothic;"
                "border:  top hair, bottom hair, left hair, right hair,"
                " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )

            title = xlwt.easyxf(
                "font: height 440, name Century Gothic, bold on, color_index blue_gray; "
                "align: vert center, horz center;border: bottom thick, bottom_color sea_green;"
            )
            sub_title = xlwt.easyxf(
                "font: height 185, name Century Gothic, bold on, color_index gray80; "
                "align: vert center, horz center; "
                "border: top hair, bottom hair, left hair, right hair,"
                "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            border_all_right = xlwt.easyxf(
                "align:horz right, vert center;"
                "font:name Century Gothic;"
                "border:  top hair, bottom hair, left hair, right hair,"
                " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )
            border_all_center = xlwt.easyxf(
                "align:horz center, vert center;"
                "font:name Century Gothic;"
                "border:  top hair, bottom hair, left hair, right hair,"
                " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
            )

            sheet1.set_panes_frozen(True)
            sheet1.set_horz_split_pos(1)
            sheet1.set_horz_split_pos(2)
            sheet1.set_vert_split_pos(1)
            sheet1.show_grid = False

            for num in range(1, 13):
                sheet1.col(num).width = 4000

            sheet1.row(0).height = 1000
            sheet1.row(1).height = 600
            sheet1.col(0).width = 400
            sheet1.col(9).width = 5000
            sheet1.col(11).width = 5500
            sheet1.col(2).width = 5000
            sheet1.col(4).width = 5000
            sheet1.col(8).width = 5500
            sheet1.write_merge(0, 0, 1, 12, name, title)
            sheet1.write(1, 1, "Date", sub_title)
            sheet1.write(1, 2, "Sequence", sub_title)
            sheet1.write(1, 3, "Customer", sub_title)
            sheet1.write(1, 4, "Property", sub_title)
            sheet1.write(1, 5, "Payment Term", sub_title)
            sheet1.write(1, 6, "Currency", sub_title)
            sheet1.write(1, 7, "Sell Price", sub_title)
            sheet1.write(1, 8, "Book price", sub_title)
            sheet1.write(1, 9, "Payable Amount", sub_title)
            sheet1.write(1, 10, "Paid Amount", sub_title)
            sheet1.write(1, 11, "Remaining Amount", sub_title)
            sheet1.write(1, 12, "Sold Status", sub_title)

            record = self.env["property.vendor"].search(
                [("landlord_id", "=", self.landlord_id.id)]
            )
            main_total_paid, main_total_remaining, total_sell_price = 0.0, 0.0, 0.0
            total_book_price, total_payable_price = 0.0, 0.0
            row = 2
            for rec in record:
                main_total_paid += rec.paid_amount
                main_total_remaining += rec.remaining_amount
                total_sell_price += rec.total_sell_amount
                total_book_price += rec.book_price
                total_payable_price += rec.payable_amount
                if rec.stage == "booked":
                    stage = "Booked"
                    style1 = blue_gray
                elif rec.stage == "refund":
                    stage = "Refund"
                    style1 = red
                elif rec.stage == "sold":
                    stage = "Sold"
                    style1 = green
                elif rec.stage == "cancel":
                    stage = "Cancel"
                    style1 = red
                elif rec.stage == "locked":
                    stage = "Locked"
                    style1 = green

                sheet1.row(row).height = 400
                sheet1.write(row, 1, rec.date, date_format)
                sheet1.write(row, 2, rec.sold_seq, border_all_center)
                sheet1.write(row, 3, rec.customer_id.name, border_all_center)
                sheet1.write(row, 4, rec.property_id.name, border_all_center)
                sheet1.write(
                    row,
                    5,
                    self.action_get_payment_term(rec.payment_term),
                    border_all_center,
                )
                sheet1.write(
                    row,
                    6,
                    f"{rec.currency_id.symbol} ({rec.currency_id.name})",
                    border_all_center,
                )
                sheet1.write(row, 7, f"{rec.total_sell_amount}", border_all_right)
                sheet1.write(row, 8, f"{rec.book_price}", border_all_right)
                sheet1.write(row, 9, f"{rec.payable_amount}", border_all_right)
                sheet1.write(row, 10, f"{rec.paid_amount}", border_all_right)
                sheet1.write(row, 11, f"{rec.remaining_amount}", border_all_right)
                sheet1.write(row, 12, stage, style1)
                row += 1

            sheet1.row(row).height = 400
            sheet1.write(row, 6, "Totals", sub_title)
            sheet1.write(row, 7, f"{total_sell_price}", green_bg)
            sheet1.write(row, 8, f"{total_book_price}", green_bg)
            sheet1.write(row, 9, f"{total_payable_price}", green_bg)
            sheet1.write(row, 10, f"{main_total_paid}", green_bg)
            sheet1.write(row, 11, f"{main_total_remaining}", red_bg)

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env["ir.attachment"].sudo()
            filename = self.landlord_id.name + " Sold.xls"
            attachment_id = attachment.create(
                {"name": filename, "type": "binary", "public": False, "datas": out}
            )
            if attachment_id:
                report = {
                    "type": "ir.actions.act_url",
                    "url": "/web/content/%s?download=true" % (attachment_id.id),
                    "target": "self",
                }
                return report

    def action_get_payment_term(self, term):
        """Get payment term text"""
        name = ""
        if term == "monthly":
            name = "Monthly"
        elif term == "full_payment":
            name = "Full Payment"
        elif term == "quarterly":
            name = "Quarterly"
        else:
            name = " "
        return name

    def action_create_landlord_tenancy_report(
        self, sheet, sheet_title, record, workbook, is_bill_record=False
    ):
        """Print landlord tenanct report"""
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.set_horz_split_pos(2)
        sheet.set_vert_split_pos(1)
        sheet.show_grid = False
        border_squre = xlwt.Borders()
        border_squre.top = xlwt.Borders.HAIR
        border_squre.left = xlwt.Borders.HAIR
        border_squre.right = xlwt.Borders.HAIR
        border_squre.bottom = xlwt.Borders.HAIR
        border_squre.top_colour = xlwt.Style.colour_map["gray50"]
        border_squre.bottom_colour = xlwt.Style.colour_map["gray50"]
        border_squre.right_colour = xlwt.Style.colour_map["gray50"]
        border_squre.left_colour = xlwt.Style.colour_map["gray50"]
        al = xlwt.Alignment()
        al.horz = xlwt.Alignment.HORZ_CENTER
        al.vert = xlwt.Alignment.VERT_CENTER
        date_format = xlwt.XFStyle()
        date_format.num_format_str = "mm/dd/yyyy"
        date_format.font.name = "Century Gothic"
        date_format.borders = border_squre
        date_format.alignment = al

        xlwt.add_palette_colour("custom_red", 0x21)
        workbook.set_colour_RGB(0x21, 240, 210, 211)
        xlwt.add_palette_colour("custom_green", 0x22)
        workbook.set_colour_RGB(0x22, 210, 241, 214)
        xlwt.add_palette_colour("custom_yellow", 0x23)
        workbook.set_colour_RGB(0x23, 255, 255, 224)
        xlwt.add_palette_colour("custom_blue", 0x24)
        workbook.set_colour_RGB(0x24, 240, 255, 255)

        italic_on = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic, italic on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )

        red_bg = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "pattern: pattern solid, fore_colour custom_red; "
            "font:name Century Gothic;border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
        )
        green_bg = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "pattern: pattern solid, fore_colour custom_green; "
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair,"
            " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
        )
        yellow_bg = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "pattern: pattern solid, fore_colour custom_yellow; "
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair,"
            " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
        )
        blue_bg = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "pattern: pattern solid, fore_colour custom_blue; "
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair,"
            " top_color gray50, bottom_color gray50, left_color gray50, right_color gray50;"
        )

        # Font Color
        red = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "font: color-index red, name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        green = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "font: color-index green, name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        magenta_ega = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "font: color-index magenta_ega, name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        gold = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "font: color-index gold, name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        violet = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "font: color-index violet, name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        blue_gray = xlwt.easyxf(
            "align: vert centre, horiz center;"
            "font: color-index blue_gray, name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )

        title = xlwt.easyxf(
            "font: height 440, name Century Gothic, bold on, color_index blue_gray; "
            "align: vert center, horz center;"
            "border: bottom thick, bottom_color sea_green;"
        )
        sub_title = xlwt.easyxf(
            "font: height 185, name Century Gothic, bold on, color_index gray80; "
            "align: vert center, horz center; "
            "border: top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        border_all_right = xlwt.easyxf(
            "align:horz right, vert center;"
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        border_all_center = xlwt.easyxf(
            "align:horz center, vert center;"
            "font:name Century Gothic;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )
        total_paid_text = xlwt.easyxf(
            "pattern: pattern solid, fore_colour custom_green;"
            "align:horz right, vert center;"
            "font:name Century Gothic, bold on;"
            "border:  top hair, bottom hair, left hair, right hair, "
            "top_color gray50, bottom_color gray50, left_color gray50, right_color gray50"
        )

        for num in range(1, 11):
            sheet.col(num).width = 4000

        sheet.col(5).width = 5000
        sheet.col(2).width = 5500
        sheet.col(9).width = 5000
        sheet.col(10).width = 5000
        sheet.col(6).width = 5000
        sheet.row(0).height = 1000
        sheet.row(1).height = 600
        sheet.col(0).width = 400
        sheet.write_merge(0, 0, 1, 10, sheet_title, title)
        sheet.write(1, 1, "Date", sub_title)
        sheet.write(1, 2, "Contract Reference", sub_title)
        sheet.write(1, 3, "Tenant", sub_title)
        sheet.write(1, 4, "Property", sub_title)
        if is_bill_record:
            sheet.write(1, 5, "Bill Reference", sub_title)
        else:
            sheet.write(1, 5, "Invoice Reference", sub_title)
        sheet.write(1, 6, "Payment Term", sub_title)
        sheet.write(1, 7, "Currency", sub_title)
        sheet.write(1, 8, "Amount", sub_title)
        sheet.write(1, 9, "Payment Status", sub_title)
        sheet.write(1, 10, "Contract Status", sub_title)
        row = 2
        total_amount = 0.0
        for rec in record:
            if is_bill_record:
                total_amount += rec.rent_bill_id.amount_total
            else:
                total_amount += rec.rent_invoice_id.amount_total

            payment_term = self.action_get_payment_term(rec.tenancy_id.payment_term)
            if rec.payment_state == "paid":
                status = "Paid"
                style0 = green
            elif rec.payment_state == "not_paid":
                status = "Not Paid"
                style0 = red
            elif rec.payment_state == "reversed":
                status = "Reversed"
                style0 = magenta_ega
            elif rec.payment_state == "partial":
                status = "Partial Paid"
                style0 = blue_gray
            elif rec.payment_state == "in_payment":
                status = "In Payment"
                style0 = violet
            elif rec.payment_state == "invoicing_legacy":
                status = "Invoicing App Legacy"
                style0 = gold
            else:
                status = " "
                style0 = border_all_center

            if rec.tenancy_id.contract_type == "cancel_contract":
                contract_status = "Cancel"
                style1 = red_bg
            elif rec.tenancy_id.contract_type == "close_contract":
                contract_status = "Close"
                style1 = red_bg
            elif rec.tenancy_id.contract_type == "running_contract":
                contract_status = "Running"
                style1 = green_bg
            elif rec.tenancy_id.contract_type == "expire_contract":
                contract_status = "Expire"
                style1 = yellow_bg
            else:
                contract_status = " "
                style1 = blue_bg

            if is_bill_record:
                if not rec.rent_bill_id.state:
                    tenancy_seq = " "
                    style2 = border_all_center
                elif rec.rent_bill_id.state == "draft":
                    tenancy_seq = "Draft Bill"
                    style2 = italic_on
                else:
                    tenancy_seq = rec.rent_bill_id.name
                    style2 = border_all_center
            else:
                if not rec.rent_invoice_id.state:
                    tenancy_seq = " "
                    style2 = border_all_center
                elif rec.rent_invoice_id.state == "draft":
                    tenancy_seq = "Draft Invoice"
                    style2 = italic_on
                else:
                    tenancy_seq = rec.rent_invoice_id.name
                    style2 = border_all_center

            sheet.row(row).height = 400
            sheet.write(row, 1, rec.invoice_date, date_format)
            sheet.write(row, 2, rec.tenancy_id.tenancy_seq, border_all_center)
            sheet.write(row, 3, rec.customer_id.name, border_all_center)
            sheet.write(row, 4, rec.tenancy_id.property_id.name, border_all_center)
            sheet.write(row, 5, tenancy_seq, style2)
            sheet.write(row, 6, payment_term, border_all_center)
            sheet.write(
                row,
                7,
                f"{rec.currency_id.symbol} ({rec.currency_id.name})",
                border_all_center,
            )
            if is_bill_record:
                sheet.write(
                    row, 8, f"{rec.rent_bill_id.amount_total}", border_all_right
                )
            else:
                sheet.write(
                    row, 8, f"{rec.rent_invoice_id.amount_total}", border_all_right
                )
            sheet.write(row, 9, status, style0)
            sheet.write(row, 10, contract_status, style1)
            row += 1
        sheet.row(row).height = 400
        sheet.write(row, 7, "Totals", sub_title)
        sheet.write(row, 8, f"{total_amount}", total_paid_text)

        # def action_tenancy_sold_xls_report(self):
        if self.report_for == "tenancy":
            name = "Rent Information - " + self.landlord_id.name
            sheet2_name = "Rent Information - " + self.landlord_id.name + " : PAID"
            sheet3_name = "Rent Information - " + self.landlord_id.name + " : NOT PAID"
            sheet4_name = (
                "Rent Information - " + self.landlord_id.name + " : PARTIAL PAID"
            )
            sheet5_name = "Contract Bill -" + self.landlord_id.name
            workbook = xlwt.Workbook(encoding="utf-8")

            # Font Color
            red = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index red"
            )
            green = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index green"
            )
            magenta_ega = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index magenta_ega"
            )
            gold = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index gold"
            )
            violet = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index violet"
            )
            blue_gray = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index blue_gray"
            )
            # Style
            sheet_style = xlwt.easyxf("align: vert centre, horiz centre")
            sheet_style_amount = xlwt.easyxf("align: vert centre, horiz right")
            heading = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on,height 200"
            )
            main_heading = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on,height 320"
            )

            # Sheet
            xlwt.add_palette_colour("warning", 0x21)
            workbook.set_colour_RGB(0x21, 75, 211, 152)
            sheet1 = workbook.add_sheet(
                "Landlord wise Contracts", cell_overwrite_ok=True
            )
            sheet2 = workbook.add_sheet("Paid Contracts", cell_overwrite_ok=True)
            sheet3 = workbook.add_sheet("Not Paid Contracts", cell_overwrite_ok=True)
            sheet4 = workbook.add_sheet(
                "Partial Paid Contracts", cell_overwrite_ok=True
            )
            workbook.add_sheet("Contract Bills", cell_overwrite_ok=True)
            date_format = xlwt.XFStyle()
            date_format.num_format_str = "mm/dd/yyyy"

            # SHEET1
            sheet1.write_merge(0, 1, 0, 8, name, main_heading)
            sheet1.col(0).width = 2800
            sheet1.col(1).width = 3500
            sheet1.col(2).width = 7000
            sheet1.col(3).width = 7000
            sheet1.col(4).width = 6000
            sheet1.col(5).width = 5500
            sheet1.col(6).width = 3000
            sheet1.col(7).width = 5500
            sheet1.col(8).width = 5500
            sheet1.row(2).height = 500
            sheet1.write(2, 0, "Date", heading)
            sheet1.write(2, 1, "Contract Ref.", heading)
            sheet1.write(2, 2, "Tenant", heading)
            sheet1.write(2, 3, "Property", heading)
            sheet1.write(2, 4, "Invoice Ref.", heading)
            sheet1.write(2, 5, "Payment Term", heading)
            sheet1.write(2, 6, "Amount", heading)
            sheet1.write(2, 7, "Payment Status", heading)
            sheet1.write(2, 8, "Contract Status", heading)
            c = 3
            rent_invoice = self.env["rent.invoice"].search(
                [("landlord_id", "=", self.landlord_id.id)]
            )
            for data in rent_invoice:
                amount = (
                    str(data.rent_invoice_id.amount_total)
                    + " "
                    + str(data.currency_id.symbol)
                )
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold

                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"
                if data.tenancy_id.payment_term == "monthly":
                    payment_term = "Monthly"
                elif data.tenancy_id.payment_term == "full_payment":
                    payment_term = "Full Payment"
                else:
                    payment_term = "Quarterly"
                sheet1.write(c, 0, data.invoice_date, date_format)
                sheet1.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet1.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet1.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet1.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet1.write(c, 5, payment_term, sheet_style)
                sheet1.write(c, 6, amount, sheet_style_amount)
                sheet1.write(c, 7, status, style0)
                sheet1.write(c, 8, stage, sheet_style)
                c += 1

            # Sheet 2
            sheet2.write_merge(0, 1, 0, 7, sheet2_name, main_heading)
            sheet2.col(0).width = 2800
            sheet2.col(1).width = 3500
            sheet2.col(2).width = 7000
            sheet2.col(3).width = 7000
            sheet2.col(4).width = 6000
            sheet2.col(5).width = 3000
            sheet2.col(6).width = 5500
            sheet2.col(7).width = 5500
            sheet2.row(2).height = 500
            sheet2.write(2, 0, "Date", heading)
            sheet2.write(2, 1, "Contract Ref.", heading)
            sheet2.write(2, 2, "Tenant", heading)
            sheet2.write(2, 3, "Property", heading)
            sheet2.write(2, 4, "Invoice Ref.", heading)
            sheet2.write(2, 5, "Amount", heading)
            sheet2.write(2, 6, "Payment Status", heading)
            sheet2.write(2, 7, "Contract Status", heading)
            c = 3
            rent_invoice = self.env["rent.invoice"].search(
                [
                    ("landlord_id", "=", self.landlord_id.id),
                    ("payment_state", "=", "paid"),
                ]
            )
            for data in rent_invoice:
                amount = (
                    str(data.rent_invoice_id.amount_total)
                    + " "
                    + str(data.currency_id.symbol)
                )
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold
                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"

                sheet2.write(c, 0, data.invoice_date, date_format)
                sheet2.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet2.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet2.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet2.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet2.write(c, 5, amount, sheet_style_amount)
                sheet2.write(c, 6, status, style0)
                sheet2.write(c, 7, stage, sheet_style)
                c += 1

            # Sheet 3
            sheet3.write_merge(0, 1, 0, 7, sheet3_name, main_heading)
            sheet3.col(0).width = 2800
            sheet3.col(1).width = 3500
            sheet3.col(2).width = 7000
            sheet3.col(3).width = 7000
            sheet3.col(4).width = 6000
            sheet3.col(5).width = 3000
            sheet3.col(6).width = 5500
            sheet3.col(7).width = 5500
            sheet3.row(2).height = 500
            sheet3.write(2, 0, "Date", heading)
            sheet3.write(2, 1, "Contract Ref.", heading)
            sheet3.write(2, 2, "Tenant", heading)
            sheet3.write(2, 3, "Property", heading)
            sheet3.write(2, 4, "Invoice Ref.", heading)
            sheet3.write(2, 5, "Amount", heading)
            sheet3.write(2, 6, "Payment Status", heading)
            sheet3.write(2, 7, "Contract Status", heading)
            c = 3
            rent_invoice = self.env["rent.invoice"].search(
                [
                    ("landlord_id", "=", self.landlord_id.id),
                    ("payment_state", "=", "not_paid"),
                ]
            )
            for data in rent_invoice:
                amount = (
                    str(data.rent_invoice_id.amount_total)
                    + " "
                    + str(data.currency_id.symbol)
                )
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold
                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"

                sheet3.write(c, 0, data.invoice_date, date_format)
                sheet3.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet3.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet3.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet3.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet3.write(c, 5, amount, sheet_style_amount)
                sheet3.write(c, 6, status, style0)
                sheet3.write(c, 7, stage, sheet_style)
                c += 1

            # Sheet 4
            sheet4.write_merge(0, 1, 0, 7, sheet4_name, main_heading)
            sheet4.col(0).width = 2800
            sheet4.col(1).width = 3500
            sheet4.col(2).width = 7000
            sheet4.col(3).width = 7000
            sheet4.col(4).width = 6000
            sheet4.col(5).width = 3000
            sheet4.col(6).width = 5500
            sheet4.col(7).width = 5500
            sheet4.row(2).height = 500
            sheet4.write(2, 0, "Date", heading)
            sheet4.write(2, 1, "Contract Ref..", heading)
            sheet4.write(2, 2, "Tenant", heading)
            sheet4.write(2, 3, "Property", heading)
            sheet4.write(2, 4, "Invoice Ref.", heading)
            sheet4.write(2, 5, "Amount", heading)
            sheet4.write(2, 6, "Payment Status", heading)
            sheet4.write(2, 7, "Contract Status", heading)
            c = 3
            rent_invoice = self.env["rent.invoice"].search(
                [
                    ("landlord_id", "=", self.landlord_id.id),
                    ("payment_state", "=", "partial"),
                ]
            )
            for data in rent_invoice:
                amount = (
                    str(data.rent_invoice_id.amount_total)
                    + " "
                    + str(data.currency_id.symbol)
                )
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold
                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"

                sheet4.write(c, 0, data.invoice_date, date_format)
                sheet4.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet4.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet4.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet4.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet4.write(c, 5, amount, sheet_style_amount)
                sheet4.write(c, 6, status, style0)
                sheet4.write(c, 7, stage, sheet_style)
                c += 1

            # sheet 5
            sheet1.write_merge(0, 1, 0, 8, sheet5_name, main_heading)
            sheet1.col(0).width = 2800
            sheet1.col(1).width = 3500
            sheet1.col(2).width = 7000
            sheet1.col(3).width = 7000
            sheet1.col(4).width = 6000
            sheet1.col(5).width = 5500
            sheet1.col(6).width = 3000
            sheet1.col(7).width = 5500
            sheet1.col(8).width = 5500
            sheet1.row(2).height = 500
            sheet1.write(2, 0, "Date", heading)
            sheet1.write(2, 1, "Contract Ref.", heading)
            sheet1.write(2, 2, "Tenant", heading)
            sheet1.write(2, 3, "Property", heading)
            sheet1.write(2, 4, "Bill Ref.", heading)
            sheet1.write(2, 5, "Payment Term", heading)
            sheet1.write(2, 6, "Amount", heading)
            sheet1.write(2, 7, "Payment Status", heading)
            sheet1.write(2, 8, "Contract Status", heading)
            c = 3
            rent_bill = self.env["rent.bill"].search(
                [("vendor_id", "=", self.landlord_id.id)]
            )
            for data in rent_bill:
                amount = (
                    str(data.rent_bill_id.amount_total)
                    + " "
                    + str(data.currency_id.symbol)
                )
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold

                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"
                if data.tenancy_id.payment_term == "monthly":
                    payment_term = "Monthly"
                elif data.tenancy_id.payment_term == "full_payment":
                    payment_term = "Full Payment"
                else:
                    payment_term = "Quarterly"
                sheet1.write(c, 0, data.invoice_date, date_format)
                sheet1.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet1.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet1.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet1.write(c, 4, data.rent_bill_id.name, sheet_style)
                sheet1.write(c, 5, payment_term, sheet_style)
                sheet1.write(c, 6, amount, sheet_style_amount)
                sheet1.write(c, 7, status, style0)
                sheet1.write(c, 8, stage, sheet_style)
                c += 1

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())
            attachment = self.env["ir.attachment"].sudo()
            filename = self.landlord_id.name + ".xls"
            attachment_id = attachment.create(
                {"name": filename, "type": "binary", "public": False, "datas": out}
            )
            if attachment_id:
                report = {
                    "type": "ir.actions.act_url",
                    "url": "/web/content/%s?download=true" % (attachment_id.id),
                    "target": "self",
                }
                return report
        elif self.report_for == "sold":
            name = "Sold Information - " + self.landlord_id.name
            workbook = xlwt.Workbook(encoding="utf-8")
            # Font Color
            red = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index red"
            )
            green = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index green"
            )
            magenta_ega = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index magenta_ega"
            )
            gold = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index gold"
            )
            violet = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index violet"
            )
            blue_gray = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on, color-index blue_gray"
            )
            sheet_style = xlwt.easyxf("align: vert centre, horiz centre")
            heading = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on,height 200"
            )
            main_heading = xlwt.easyxf(
                "align: vert centre, horiz centre;font: bold on,height 320"
            )
            sheet_style_amount = xlwt.easyxf("align: vert centre, horiz right")
            sheet1 = workbook.add_sheet(
                "Landlord wise Sold Information", cell_overwrite_ok=True
            )
            date_format = xlwt.XFStyle()
            date_format.num_format_str = "mm/dd/yyyy"
            sheet1.write_merge(0, 1, 0, 7, name, main_heading)
            sheet1.col(0).width = 2800
            sheet1.col(1).width = 3000
            sheet1.col(2).width = 7000
            sheet1.col(3).width = 7000
            sheet1.col(4).width = 3000
            sheet1.col(5).width = 5500
            sheet1.col(6).width = 5500
            sheet1.col(7).width = 3000
            sheet1.row(2).height = 500
            sheet1.write(2, 0, "Date", heading)
            sheet1.write(2, 1, "Sequence", heading)
            sheet1.write(2, 2, "Customer", heading)
            sheet1.write(2, 3, "Property", heading)
            sheet1.write(2, 4, "Sale Price", heading)
            sheet1.write(2, 5, "Invoice Reference", heading)
            sheet1.write(2, 6, "Payment Status", heading)
            sheet1.write(2, 7, "Sold Status", heading)
            c = 3
            property_sold = self.env["property.vendor"].search(
                [("landlord_id", "=", self.landlord_id.id)]
            )
            for data in property_sold:
                amount = (
                    str(data.total_sell_amount) + " " + str(data.currency_id.symbol)
                )
                if data.sold_invoice_payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.sold_invoice_payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.sold_invoice_payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.sold_invoice_payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.sold_invoice_payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold

                if data.stage == "booked":
                    stage = "Booked"
                elif data.stage == "refund":
                    stage = "Refund"
                else:
                    stage = "Sold"

                sheet1.col(c).width = 7000
                sheet1.write(c, 0, data.date, date_format)
                sheet1.write(c, 1, data.sold_seq, sheet_style)
                sheet1.write(c, 2, data.customer_id.name, sheet_style)
                sheet1.write(c, 3, data.property_id.name, sheet_style)
                sheet1.write(c, 4, amount, sheet_style_amount)
                sheet1.write(c, 5, data.sold_invoice_id.name, sheet_style)
                sheet1.write(c, 6, status, style0)
                sheet1.write(c, 7, stage, sheet_style)
                c += 1

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env["ir.attachment"].sudo()
            filename = self.landlord_id.name + ".xls"
            attachment_id = attachment.create(
                {"name": filename, "type": "binary", "public": False, "datas": out}
            )
            if attachment_id:
                report = {
                    "type": "ir.actions.act_url",
                    "url": "/web/content/%s?download=true" % (attachment_id.id),
                    "target": "self",
                }
                return report
