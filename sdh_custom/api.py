import frappe
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

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