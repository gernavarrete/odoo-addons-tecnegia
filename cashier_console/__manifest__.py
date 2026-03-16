{
    "name": "Cashier Console",
    "summary": "Guided cashier operations to collect sales orders and print fiscal documents",
    "version": "18.0.1.0.0",
    "category": "Accounting/Point of Sale",
    "author": "Technogia",
    "website": "https://www.technogia.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "sale_management",
        "account",
        "hr",
        "point_of_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/cashier_session_views.xml",
        "views/cashier_order_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/cashier_payment_wizard_views.xml",
        "views/cashier_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "cashier_console/static/src/scss/dashboard.scss",
        ],
    },
    "images": ["static/description/icon.svg"],
    "application": True,
    "installable": True,
}
