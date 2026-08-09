import frappe
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

class CustomDeliveryNote(DeliveryNote):
    
    def check_sales_return_reference(self):
        # This is the primary method in ERPNext's SellingController that enforces 
        # the link between a return and an original document.
        if self.is_return and (not self.return_against or self.return_against == "None"):
            
            # SAFETY GUARD: Ensure this is ONLY allowed for zero-valued crates
            for item in self.get("items"):
                if flt(item.rate) > 0 or flt(item.incoming_rate) > 0:
                    frappe.throw(f"Standalone returns are only allowed for zero-valued items. Item {item.item_code} has a rate greater than zero.")
            
            # If all items are zero-valued, we exit the function immediately.
            # This completely bypasses the core ERPNext check that crashes.
            return 
            
        # If it's a normal return (with a reference), run the standard core logic
        super().check_sales_return_reference()

    def validate_return_against(self):
        # Some ERPNext versions also run this secondary check on the Delivery Note level.
        if self.is_return and (not self.return_against or self.return_against == "None"):
            return
            
        # Run standard logic if the method exists in the parent class
        if hasattr(super(), 'validate_return_against'):
            super().validate_return_against()