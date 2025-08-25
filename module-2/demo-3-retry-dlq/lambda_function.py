import json


def lambda_handler(event, context):
    if isinstance(event, str):
        try:
            event = json.loads(event)
        except json.JSONDecodeError:
            pass

    # Accept either a raw payload OR an EventBridge envelope
    payload = event.get("detail", event) if isinstance(event, dict) else {}
    price = payload.get("price")

    if price is None:
        raise Exception("Missing price")

    order_id = payload.get("order_id")
    print(f"Processed order {order_id} at price {price}")
    return {"ok": True, "order_id": order_id, "price": price}
