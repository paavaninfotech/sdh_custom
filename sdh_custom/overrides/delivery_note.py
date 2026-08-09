import frappe
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

class CustomDeliveryNote(DeliveryNote):
    
    def validate(self):
        # 1. Clean up literal "None" strings that might be saved in the database
        if self.return_against == "None":
            self.return_against = None
            
        for item in self.get("items"):
            if item.dn_detail == "None":
                item.dn_detail = None
                
        super().validate()

    def check_sales_return_reference(self):
        # 2. Bypass validation for zero-valued crates
        if self.is_return and not self.return_against:
            for item in self.get("items"):
                if flt(item.rate) > 0 or flt(item.incoming_rate) > 0:
                    frappe.throw(f"Standalone returns are only allowed for zero-valued items. Item {item.item_code} has a rate greater than zero.")
            return 
            
        super().check_sales_return_reference()

    def validate_return_against(self):
        # 3. Bypass secondary checks
        if self.is_return and not self.return_against:
            return
            
        if hasattr(super(), 'validate_return_against'):
            super().validate_return_against()

    def update_returned_qty(self):
        # 4. CRITICAL FOR SUBMIT: Bypass updating the original document's quantities
        if self.is_return and not self.return_against:
            return
            
        super().update_returned_qty()