{
    "name": "NC Stock Return Link - Automatic Credit Notes from Returns",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Automatically link credit notes to stock returns and lock edited lines",
    "description": """
Automated Credit Note Management
================================
This module automatically links credit notes to validated stock returns 
and prevents editing of lines with associated returns.

Key Features:
-------------
• Automatic credit note adjustment based on stock returns
• Intelligent matching between original and credit note lines
• Locking of lines with associated returns to prevent manual edits
• Automatic removal of lines without returns
• Detailed logging for debugging and traceability
• Chatter notifications for user awareness

Business Benefits:
------------------
• Eliminates manual errors in credit note processing
• Ensures compliance between accounting and inventory
• Saves time on credit note management
• Provides complete audit trail

Compatibility:
--------------
• Odoo 18.0
• Requires: account, stock, sale_stock modules

Installation:
-------------
1. Install the module through Odoo Apps
2. No additional configuration required
3. Works automatically when creating credit notes

Support:
-------
• Website: https://technogia.dev
• Email: support@technogia.dev
    """,
    "author": "Technogia",
    "website": "https://technogia.dev",
    "license": "LGPL-3",
    "depends": ["account", "stock", "sale_stock"],
    "data": [
        "views/account_move_view.xml",
    ],
    "demo": [],
    "images": [
        "static/description/screenshot_1.png",
        "static/description/screenshot_2.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "price": 350.00,
    "currency": "USD",
}
