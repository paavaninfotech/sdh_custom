# Copyright (c) 2026, Paavan Infotech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import pandas as pd
from frappe.utils.file_manager import get_file_path

class BulkDeliveryNoteUpload(Document):
	pass

def get_item_details(item_code):
    """
    Helper function to manually fetch mandatory item details 
    so we don't rely on Frappe's problematic set_missing_values()
    """
    return frappe.db.get_value("Item", item_code, 
                               ["stock_uom", "item_name", "default_warehouse"], as_dict=True)

@frappe.whitelist()
def generate_delivery_notes(docname):
    # Fetch the upload utility document
    doc = frappe.get_doc("Bulk Delivery Note Upload", docname)
    
    if not doc.upload_file:
        frappe.throw("Please attach an Excel file first.")
        
    # Get the physical file path of the attached Excel file
    file_path = get_file_path(doc.upload_file)
    
    try:
        # Read the Excel file using pandas
        df = pd.read_excel(file_path)
    except Exception as e:
        frappe.throw(f"Error reading the Excel file: {str(e)}")

    # Extract item codes (all columns except the first one)
    item_columns = df.columns[1:]
    created_docs = []
    
    # Check if this upload is flagged as a return
    is_return = doc.get("is_return", 0)

    # Iterate over each row (Customer)
    for index, row in df.iterrows():
        customer = row[df.columns[0]]
        
        # Skip empty customer rows
        if pd.isna(customer) or not str(customer).strip(): 
            continue

        has_items = False

        # ==========================================================
        # PATH A: IF RETURN -> CREATE STOCK ENTRY (MATERIAL RECEIPT)
        # ==========================================================
        if is_return:
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Receipt"
            se.posting_date = doc.delivery_date
            
            # Stamping the Customer onto the Stock Entry for ledger tracking
            # Note: Ensure 'custom_customer' field exists on the Stock Entry Doctype
            se.custom_customer = str(customer).strip() 

            for raw_item_code in item_columns:
                item_code = str(raw_item_code).strip()
                
                # Ignore pandas 'Unnamed' empty columns
                if not item_code or 'Unnamed' in item_code or item_code.lower() == 'nan': 
                    continue

                raw_qty = row[raw_item_code]
                
                # Process valid quantities
                if pd.notna(raw_qty) and str(raw_qty).strip() and float(raw_qty) > 0:
                    item_details = get_item_details(item_code)
                    
                    if not item_details: 
                        continue

                    se.append("items", {
                        "item_code": item_code,
                        "qty": float(raw_qty), 
                        "uom": item_details.stock_uom,
                        "stock_uom": item_details.stock_uom,
                        "conversion_factor": 1.0,
                        "t_warehouse": item_details.default_warehouse,
                        "basic_rate": 0.0 # Force zero valuation for incoming empty crates
                    })
                    has_items = True
            
            if has_items:
                se.insert()
                # se.submit() # Uncomment this line if you want it to auto-submit
                created_docs.append(se.name)

        # ==========================================================
        # PATH B: IF NORMAL -> CREATE DELIVERY NOTE
        # ==========================================================
        else:
            dn = frappe.new_doc("Delivery Note")
            dn.customer = str(customer).strip()
            dn.posting_date = doc.delivery_date
            
            # Safely apply custom shift if provided
            if doc.get("shift"): 
                dn.custom_shift = doc.shift 

            for raw_item_code in item_columns:
                item_code = str(raw_item_code).strip()
                
                if not item_code or 'Unnamed' in item_code or item_code.lower() == 'nan': 
                    continue

                raw_qty = row[raw_item_code]
                
                # Process valid quantities
                if pd.notna(raw_qty) and str(raw_qty).strip() and float(raw_qty) > 0:
                    item_details = get_item_details(item_code)
                    
                    if not item_details: 
                        continue

                    dn.append("items", {
                        "item_code": item_code,
                        "qty": float(raw_qty),
                        "uom": item_details.stock_uom,
                        "stock_uom": item_details.stock_uom,
                        "conversion_factor": 1.0,
                        "warehouse": item_details.default_warehouse
                    })
                    has_items = True
            
            if has_items:
                dn.insert()
                # dn.submit() # Uncomment this line if you want it to auto-submit
                created_docs.append(dn.name)

    # ==========================================================
    # FINAL MESSAGING
    # ==========================================================
    if created_docs:
        doc_type = "Stock Entries (Material Receipts)" if is_return else "Delivery Notes"
        frappe.msgprint(f"Successfully created {len(created_docs)} {doc_type}.")
    else:
        frappe.msgprint("No records were created. Please check the quantities and item codes in your file.")