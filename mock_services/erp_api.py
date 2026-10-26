
from fastapi import FastAPI

app = FastAPI(title="Mock ERP API")

ERP_INVENTORY = {
    "SKU-101": {
        "product_name": "Wireless Mouse",
        "quantity": 15,
    },
    "SKU-102": {
        "product_name": "Mechanical Keyboard",
        "quantity": 8,
    },
    "SKU-103": {
        "product_name": "USB-C Hub",
        "quantity": 10,
    },
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "erp"}


@app.get("/inventory")
def get_inventory():
    return {"inventory": ERP_INVENTORY}
