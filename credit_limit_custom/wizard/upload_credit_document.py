from odoo import models, fields, api, _


class UploadCreditDocument(models.TransientModel):
    _name = "upload.credit.document"
    _description = "Upload Credit Documentation"

    file_data = fields.Binary(string="File", required=True)
    file_name = fields.Char(string="File Name")
    description = fields.Char(
        string="Document Description", required=True, help="E.g. Balance Sheet 2024"
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, readonly=True
    )

    def action_upload(self):
        """Creates the attachment and links it to the partner."""
        self.ensure_one()

        # Create the attachment in Odoo standard model
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{self.description} ({self.file_name})",
                "type": "binary",
                "datas": self.file_data,
                "res_model": "res.partner",
                "res_id": self.partner_id.id,
                "mimetype": (
                    "application/pdf"
                    if self.file_name and self.file_name.endswith(".pdf")
                    else False
                ),
            }
        )

        # Post a message in the chatter
        self.partner_id.message_post(
            body=_("Credit documentation uploaded: %s") % self.description,
            attachment_ids=[attachment.id],
        )

        return {"type": "ir.actions.act_window_close"}
