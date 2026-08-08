// Copyright (c) 2026, Paavan Infotech and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Bulk Delivery Note Upload", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Bulk Delivery Note Upload', {
    refresh: function(frm) {
        frm.add_custom_button(__('Generate Delivery Notes'), function() {
            if (!frm.doc.upload_file) {
                frappe.msgprint("Please upload a file before processing.");
                return;
            }
            
            frappe.call({
                // Adjust the path below to match your custom app's module structure
                method: "sdh_custom.shayma_dairy_customization.doctype.bulk_delivery_note_upload.bulk_delivery_note_upload.generate_delivery_notes",
                args: {
                    docname: frm.doc.name
                },
                freeze: true,
                freeze_message: "Generating Delivery Notes...",
                callback: function(r) {
                    if (!r.exc) {
                        frm.reload_doc();
                    }
                }
            });
        });
    }
});