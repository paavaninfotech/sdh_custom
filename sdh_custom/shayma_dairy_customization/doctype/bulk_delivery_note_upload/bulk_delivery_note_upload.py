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
        # Read the Excel file
        df = pd.read_excel(file_path)
    except Exception as e:
        frappe.throw(f"Error reading the Excel file: {str(e)}")

    # Extract item codes (all columns except the first one)
    item_columns = df.columns[1:]
    created_notes = []
    
    # Check if this upload is flagged as a return
    is_return = doc.get("is_return", 0)

    # Iterate over each row (Customer)
    for index, row in df.iterrows():
        customer = row[df.columns[0]]
        
        if pd.isna(customer):
            continue # Skip empty rows

        # Initialize a new Delivery Note
        dn = frappe.new_doc("Delivery Note")
        dn.customer = customer
        dn.posting_date = doc.delivery_date
        dn.custom_shift = doc.shift 
        
        # If it's a return, flag the Delivery Note as a return
        if is_return:
            dn.is_return = 1
        
        has_items = False

        # Iterate over the item columns to populate the items table
        for item_code in item_columns:
            raw_qty = row[item_code]
            
            # Only process if the cell has a valid number greater than 0
            if pd.notna(raw_qty) and float(raw_qty) > 0:
                
                # If is_return is checked, convert the positive Excel qty to negative
                final_qty = float(raw_qty) * -1 if is_return else float(raw_qty)
                
                dn.append("items", {
                    "item_code": item_code,
                    "qty": final_qty
                })
                has_items = True
        
        # Only save if there is at least one item with a quantity
        if has_items:
            dn.insert()
            # dn.submit() # Uncomment if you want auto-submission
            created_notes.append(dn.name)

    if created_notes:
        # Dynamic success message based on the document type created
        doc_type_name = "Return Delivery Notes" if is_return else "Delivery Notes"
        frappe.msgprint(f"Successfully created {len(created_notes)} {doc_type_name}.")
    else:
        frappe.msgprint("No records were created. Please check the quantities in your file.")