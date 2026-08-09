import frappe
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

class CustomDeliveryNote(DeliveryNote):
    
    @property
    def is_standalone_zero_return(self):
        # Safely catch Python None, empty strings, and literal "None" strings
        return self.is_return and (not self.return_against or str(self.return_against).strip() in ["", "None"])

    def validate(self):
        # Forcefully clean the data before saving so "None" strings don't sneak into the DB
        if self.is_standalone_zero_return:
            self.return_against = None
            for item in self.get("items"):
                if not item.dn_detail or str(item.dn_detail).strip() == "None":
                    item.dn_detail = None
        
        super().validate()

    def check_sales_return_reference(self):
        # Bypass core validation but enforce our strict zero-valuation constraint
        if self.is_standalone_zero_return:
            for item in self.get("items"):
                if flt(item.rate) > 0 or flt(item.incoming_rate) > 0:
                    frappe.throw(f"Standalone returns are only allowed for zero-valued crates. Item {item.item_code} has a value.")
            return 
            
        super().check_sales_return_reference()

    def validate_return_against(self):
        if self.is_standalone_zero_return:
            return
            
        if hasattr(super(), 'validate_return_against'):
            super().validate_return_against()

    def update_returned_qty(self):
        # CRITICAL: This is the primary function called during SUBMIT that fetches the original doc
        if self.is_standalone_zero_return:
            return
            
        super().update_returned_qty()