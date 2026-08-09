import frappe
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

class CustomDeliveryNote(DeliveryNote):
    def validate_return_against(self):
        # Override core method to allow standalone returns without return_against
        if self.is_return:
            # Skip core check that mandates self.return_against
            pass
        else:
            super().validate_return_against()
    
    def check_sales_return_reference(self):
        # Override core method to allow standalone returns without return_against
        if self.is_return:
            # Skip core check that mandates self.return_against
            pass
        else:
            super().validate_return_against()
    