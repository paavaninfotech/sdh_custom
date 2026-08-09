import frappe
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

class CustomDeliveryNote(DeliveryNote):
    
    @property
    def is_standalone_zero_return(self):
        return self.is_return and (not self.return_against or str(self.return_against).strip() in ["", "None"])

    def clean_standalone_references(self):
        if self.is_standalone_zero_return:
            # CRITICAL: Use empty string "", NEVER Python None. 
            # This prevents Frappe from casting it to the string "None"
            self.return_against = ""
            
            for item in self.get("items"):
                item.dn_detail = ""
                item.against_sales_order = ""
                item.against_sales_invoice = ""
                item.serial_no = ""
                item.batch_no = ""

    def validate(self):
        self.clean_standalone_references()
        super().validate()

    def before_submit(self):
        self.clean_standalone_references()

    def check_sales_return_reference(self):
        if self.is_standalone_zero_return:
            for item in self.get("items"):
                if flt(item.rate) > 0 or flt(item.incoming_rate) > 0:
                    frappe.throw(f"Standalone returns only allowed for zero-valued crates. Item {item.item_code} has a value.")
            return 
        super().check_sales_return_reference()

    def validate_return_against(self):
        if self.is_standalone_zero_return:
            return
        if hasattr(super(), 'validate_return_against'):
            super().validate_return_against()

    def get_return_against_doc(self):
        if self.is_standalone_zero_return:
            # Return a dummy dictionary to prevent downstream core functions from crashing
            return frappe._dict({
                "doctype": "Delivery Note",
                "name": "Standalone Return",
                "posting_date": self.posting_date,
                "customer": self.customer,
                "company": self.company,
                "conversion_rate": 1.0
            })
        if hasattr(super(), 'get_return_against_doc'):
            return super().get_return_against_doc()

    def update_returned_qty(self):
        if self.is_standalone_zero_return:
            return
        super().update_returned_qty()

    def update_billing_status(self):
        if self.is_standalone_zero_return:
            return
        if hasattr(super(), 'update_billing_status'):
            super().update_billing_status()