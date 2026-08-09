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

        items_list = []

        # Iterate over the item columns to populate the items table
        for item_code in item_columns:
            raw_qty = row[item_code]
            
            # Only process if the cell has a valid number greater than 0
            if pd.notna(raw_qty) and float(raw_qty) > 0:
                # Keep quantity POSITIVE even for returns (ERPNext handles return logic via is_return=1)
                items_list.append({
                    "item_code": item_code,
                    "qty": float(raw_qty)
                })
        
        # Only save if there is at least one item with a quantity
        if items_list:
            dn = frappe.get_doc({
                "doctype": "Delivery Note",
                "customer": customer,
                "posting_date": doc.delivery_date,
                "custom_shift": doc.shift,
                "is_return": 1 if is_return else 0,
                "items": items_list
            })
            
            dn.insert()
            # dn.submit() # Uncomment if you want auto-submission
            created_notes.append(dn.name)

    if created_notes:
        doc_type_name = "Return Delivery Notes" if is_return else "Delivery Notes"
        frappe.msgprint(f"Successfully created {len(created_notes)} {doc_type_name}.")
    else:
        frappe.msgprint("No records were created. Please check the quantities in your file.")