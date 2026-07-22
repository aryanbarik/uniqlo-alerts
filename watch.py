"""
Uniqlo restock watcher.
Polls Uniqlo's product API and pings a Discord webhook when a watched
color/size combo flips from out-of-stock to in-stock.

To add a product: copy the full product-page URL from uniqlo.com and paste
it into WATCHLIST below. The URL already contains everything needed
(product id, colorDisplayCode, sizeDisplayCode). That's it.
"""

import json
import os
import re
import sys
import requests
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# WATCHLIST — paste Uniqlo product-page URLs here, one per line.
# Add as many as you like. The optional "label" is just for readable alerts;
# if you omit it, the product id is used.
# ---------------------------------------------------------------------------
WATCHLIST = [
    {
        "url": "https://www.uniqlo.com/us/en/products/E484776-000/00?colorDisplayCode=09&sizeDisplayCode=006",
        "label": "E484776-000 Black XL",
    },
    {
        "url": "https://www.uniqlo.com/us/en/products/E482756-000/00?colorDisplayCode=00&sizeDisplayCode=006",
        "label": "E482756-000 White XL",
    },
    {
        "url": "https://www.uniqlo.com/us/en/products/E486158-000/00?colorDisplayCode=62&sizeDisplayCode=006",
        "label": "E486158-000 Blue XL",
    },
    {
        "url": "https://www.uniqlo.com/us/en/products/E487966-000/00?colorDisplayCode=07&sizeDisplayCode=006",
        "label": "E487966-000 Gray XL",
    },
    {
        "url": "https://www.uniqlo.com/us/en/products/E486159-000/00?colorDisplayCode=00&sizeDisplayCode=006",
        "label": "E486159-000 White XL",
    },
    # --- Add more below, same shape ---------------------------------------
    # {
    #     "url": "PASTE_UNIQLO_URL_HERE",
    #     "label": "Optional friendly name",
    # },
]

# ---------------------------------------------------------------------------
API = (
    "https://www.uniqlo.com/us/api/commerce/v5/en/products/"
    "{pid}/price-groups/00/l2s?withPrices=false&withStocks=true&httpFailure=true"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
    "x-fr-clientid": "uq.us.web-spa",  # Uniqlo web client id; update if 403s appear
}

STATE_FILE = "stock_state.json"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
DISCORD_USER_ID = "442188946252890122"


def parse_url(url):
    """Extract product_id, color, size from a Uniqlo product URL."""
    path = urlparse(url).path
    m = re.search(r"/products/([A-Z0-9\-]+)", path)
    if not m:
        raise ValueError(f"Could not find product id in URL: {url}")
    product_id = m.group(1)

    q = parse_qs(urlparse(url).query)
    color = q.get("colorDisplayCode", [None])[0]
    size = q.get("sizeDisplayCode", [None])[0]
    if not color or not size:
        raise ValueError(f"URL missing colorDisplayCode/sizeDisplayCode: {url}")

    return product_id, color, size


def check_item(product_id, color, size, debug=False):
    """Return True if the specific color+size combo is in stock."""
    url = API.format(pid=product_id)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()

    if debug:
        print(json.dumps(data, indent=2)[:3000])

    result = data.get("result", {})
    l2s = result.get("l2s", [])

    # stocks may be a dict keyed by l2Id, depending on API version
    raw_stocks = result.get("stocks", {})
    stocks = raw_stocks if isinstance(raw_stocks, dict) else {}

    for sku in l2s:
        sku_color = sku.get("color", {}).get("displayCode")
        sku_size = sku.get("size", {}).get("displayCode")
        if sku_color == color and sku_size == size:
            stock = sku.get("stock") or stocks.get(sku.get("l2Id"), {})
            qty = stock.get("quantity", 0)
            status = stock.get("statusCode", "")
            return qty > 0 or status == "IN_STOCK"
    return False


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def notify(label, url):
    msg = f"<@{DISCORD_USER_ID}> 🎉 BACK IN STOCK: {label}\n{url}"
    print(msg)
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=15)
        except Exception as e:
            print(f"[discord error] {e}")


def main():
    debug = os.environ.get("DEBUG") == "1"
    state = load_state()
    any_error = False

    for entry in WATCHLIST:
        url = entry["url"]
        try:
            product_id, color, size = parse_url(url)
        except ValueError as e:
            print(f"[skip] {e}")
            any_error = True
            continue

        label = entry.get("label") or f"{product_id} ({color}/{size})"
        key = f"{product_id}-{color}-{size}"

        try:
            in_stock = check_item(product_id, color, size, debug=debug)
        except Exception as e:
            print(f"[error] {label}: {e}")
            any_error = True
            continue

        was_in_stock = state.get(key, False)
        if in_stock and not was_in_stock:
            notify(label, url)
        else:
            marker = "in stock" if in_stock else "out of stock"
            print(f"[{marker}] {label}")

        state[key] = in_stock

    save_state(state)
    # Non-zero exit on error is optional; keep 0 so the Action still commits state.
    sys.exit(0)


if __name__ == "__main__":
    main()
