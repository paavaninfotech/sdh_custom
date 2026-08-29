import frappe
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

@frappe.whitelist()
def enqueue_bulk_invoices(from_date, to_date, invoice_date):
    # Trigger the background job using the 'long' queue (default 1500s timeout)
    frappe.enqueue(
        "sdh_custom.api.process_bulk_invoices_job",
        queue="long",
        timeout=3600, # Extended timeout for high-volume data
        from_date=from_date,
        to_date=to_date,
        invoice_date=invoice_date,
        user=frappe.session.user
    )
    return {"status": "queued", "message": "The bulk generation job has been added to the background queue."}

def process_bulk_invoices_job(from_date, to_date, invoice_date, user):
    frappe.db.auto_commit_on_many_writes = 1
    
    deliveries = frappe.db.get_all(
        "Delivery Note",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "per_billed": ["<", 100],
            "status": ["not in", ["Closed", "Cancelled"]]
        },
        fields=["name", "customer"],
        order_by="posting_date asc"
    )

    if not deliveries:
        frappe.publish_realtime("bulk_invoice_update", "No unbilled deliveries found.", user=user)
        return

    customer_deliveries = {}
    for d in deliveries:
        customer_deliveries.setdefault(d.customer, []).append(d.name)

    success_count = 0
    error_count = 0

    for customer, dns in customer_deliveries.items():
        try:
            si = make_sales_invoice(dns[0])
            si.posting_date = invoice_date
            si.set_posting_time = 1

            if len(dns) > 1:
                for dn_name in dns[1:]:
                    mapped_doc = make_sales_invoice(dn_name)
                    for item in mapped_doc.get("items"):
                        si.append("items", item)

            si.set("taxes", [])
            si.set_missing_values()
            si.calculate_taxes_and_totals()
            
            si.insert()
            # Commit after each customer to save progress
            frappe.db.commit() 
            success_count += 1

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(title=f"Bulk Invoice Failed: {customer}", message=frappe.get_traceback())
            error_count += 1

    # Send completion notification to the user who triggered it
    final_message = f"Job completed: {success_count} invoices created, {error_count} failed."
    frappe.publish_realtime("bulk_invoice_update", final_message, user=user)

@frappe.whitelist()
def enqueue_bulk_purchase_invoices(from_date, to_date, invoice_date):
    frappe.enqueue(
        "sdh_custom.api.process_bulk_pi_job",
        queue="long",
        timeout=3600,
        from_date=from_date,
        to_date=to_date,
        invoice_date=invoice_date,
        user=frappe.session.user
    )
    return {"status": "queued", "message": "The bulk Purchase Invoice job has been added to the queue."}

def process_bulk_pi_job(from_date, to_date, invoice_date, user):
    frappe.db.auto_commit_on_many_writes = 1
    
    # 1. Fetch unbilled Purchase Receipts, including the is_return flag
    receipts = frappe.db.get_all(
        "Purchase Receipt",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
            "per_billed": ["<", 100],
            "status": ["not in", ["Closed", "Cancelled"]]
        },
        fields=["name", "supplier", "is_return"],
        order_by="posting_date asc"
    )

    if not receipts:
        frappe.publish_realtime("bulk_pi_update", "No unbilled Purchase Receipts found.", user=user)
        return

    # 2. Group by Supplier and split by normal vs. return
    supplier_normals = {}
    supplier_returns = {}
    
    for r in receipts:
        if r.is_return:
            supplier_returns.setdefault(r.supplier, []).append(r.name)
        else:
            supplier_normals.setdefault(r.supplier, []).append(r.name)

    success_count = 0
    error_count = 0

    # 3. Helper function to generate invoices to avoid repeating code
    def create_invoices(supplier_dict, is_return_batch):
        nonlocal success_count, error_count
        
        # Set the format for Supplier Invoice No
        suffix = "Return" if is_return_batch else "Inv"
        supplier_invoice_no = f"{invoice_date}-{suffix}"

        for supplier, prs in supplier_dict.items():
            try:
                # Initialize SI mapping with the first Purchase Receipt
                pi = make_purchase_invoice(prs[0])
                pi.posting_date = invoice_date
                pi.set_posting_time = 1
                
                # Apply mandatory supplier invoice fields
                pi.bill_no = supplier_invoice_no
                pi.bill_date = invoice_date

                # Map and append the remaining items
                if len(prs) > 1:
                    for pr_name in prs[1:]:
                        mapped_doc = make_purchase_invoice(pr_name)
                        for item in mapped_doc.get("items"):
                            pi.append("items", item)

                pi.set("taxes", [])
                pi.set_missing_values()
                pi.calculate_taxes_and_totals()
                
                pi.insert()
                frappe.db.commit() 
                success_count += 1

            except Exception as e:
                frappe.db.rollback()
                frappe.log_error(title=f"Bulk PI Failed: {supplier} (Return: {is_return_batch})", message=frappe.get_traceback())
                error_count += 1

    # 4. Execute standard receipts first, then returns
    if supplier_normals:
        create_invoices(supplier_normals, is_return_batch=0)
        
    if supplier_returns:
        create_invoices(supplier_returns, is_return_batch=1)

    final_message = f"Job completed: {success_count} Purchase Invoices created, {error_count} failed."
    frappe.publish_realtime("bulk_pi_update", final_message, user=user)