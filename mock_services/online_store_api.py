
from fastapi import FastAPI

app = FastAPI(title="Mock Online Store API")

ONLINE_INVENTORY = {
    "SKU-101": {
        "product_name": "Wireless Mouse",
        "quantity": 20,
    },
    "SKU-102": {
        "product_name": "Mechanical Keyboard",
        "quantity": 8,
    },
    "SKU-103": {
        "product_name": "USB-C Hub",
        "quantity": 12,
    },
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "online-store"}


@app.get("/inventory")
def get_inventory():
    return {"inventory": ONLINE_INVENTORY}
