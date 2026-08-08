# Copyright (c) 2026, Paavan Infotech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import pandas as pd
from frappe.utils.file_manager import get_file_path

class BulkDeliveryNoteUpload(Document):
	pass

@frappe.whitelist()
def generate_delivery_notes(docname):
    # Fetch the upload utility document
    doc = frappe.get_doc("Bulk Delivery Note Upload", docname)
    
    if not doc.upload_file:
        frappe.throw("Please attach an Excel file first.")
        
    # Get the physical file path of the attached Excel file
    file_path = get_file_path(doc.upload_file)
    
    try:
        # Read the Excel file. 
        # Assuming the first column is 'Customer' and the rest are Item Codes
        df = pd.read_excel(file_path)
    except Exception as e:
        frappe.throw(f"Error reading the Excel file: {str(e)}")

    # Extract item codes (all columns except the first one)
    item_columns = df.columns[1:]
    
    created_notes = []

    # Iterate over each row (Customer)
    for index, row in df.iterrows():
        customer = row[df.columns[0]] # Grabs the customer name/ID from the first column
        
        if pd.isna(customer):
            continue # Skip empty rows

        # Initialize a new Delivery Note
        dn = frappe.new_doc("Delivery Note")
        dn.customer = customer
        dn.posting_date = doc.delivery_date
        # Assuming you have a custom field for shift on the Delivery Note
        dn.custom_shift = doc.shift 
        
        has_items = False

        # Iterate over the item columns to populate the items table
        for item_code in item_columns:
            qty = row[item_code]
            
            # Only add the item if the quantity is greater than 0
            if pd.notna(qty) and float(qty) > 0:
                dn.append("items", {
                    "item_code": item_code,
                    "qty": float(qty)
                })
                has_items = True
        
        # Only save if there is at least one item with a quantity
        if has_items:
            dn.insert()
            # Uncomment the next line if you want it to auto-submit
            # dn.submit() 
            created_notes.append(dn.name)

    if created_notes:
        frappe.msgprint(f"Successfully created {len(created_notes)} Delivery Notes.")
    else:
        frappe.msgprint("No Delivery Notes were created. Please check the quantities in your file.")
