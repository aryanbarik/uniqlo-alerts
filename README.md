# uniqlo-alerts

A tiny bot that watches specific Uniqlo product/color/size combos and pings you on Discord the moment one comes back in stock.

No scraping, no headless browser — it hits the same internal JSON API Uniqlo's own site uses, so it gets clean stock data directly.

Runs on a free GitHub Actions cron (every 15 minutes) with no server to maintain.

## How it works

1. `watch.py` reads a list of Uniqlo product URLs (`WATCHLIST` in the script).
2. For each one, it calls Uniqlo's product API and checks the stock status for that exact color + size.
3. It compares the result to the last known state (saved in `stock_state.json`, committed back to the repo each run).
4. If something flips from **out of stock → in stock**, it posts an alert to a Discord webhook (optionally `@`-mentioning you).

Alerts only fire on that transition — so it won't spam you every 15 minutes for something that's already in stock, only the moment it becomes available.

## Setup

### 1. Fork or clone this repo

Use the "Use this template" / "Fork" button on GitHub, or:

```bash
git clone https://github.com/aryanbarik/uniqlo-alerts.git
cd uniqlo-alerts
```

### 2. Create a Discord webhook

In the Discord server you want alerts posted to:

1. **Server Settings → Integrations → Webhooks → New Webhook**
2. Optionally rename it and pick the channel it posts to
3. Click **Copy Webhook URL** — you'll need this in step 4

(No server handy? Create one for yourself: server icon `+` → "Create My Own" → "For me and my friends".)

### 3. (Optional) Get your Discord user ID to be @-mentioned

By default alerts post without pinging anyone. To get pinged directly:

1. Discord → **User Settings → Advanced → enable Developer Mode**
2. Right-click your username → **Copy User ID**

### 4. Add repo secrets

In your fork: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value | Required |
|---|---|---|
| `DISCORD_WEBHOOK` | The webhook URL from step 2 | Yes |
| `DISCORD_USER_ID` | Your Discord user ID from step 3 | No — omit to skip the @-mention |

### 5. Edit your watchlist

Open `watch.py` and edit the `WATCHLIST` list near the top:

```python
WATCHLIST = [
    {
        "url": "https://www.uniqlo.com/us/en/products/E123456-000/00?colorDisplayCode=00&sizeDisplayCode=004",
        "label": "Optional friendly name",
    },
    # add as many as you like, same shape
]
```

To get the URL: go to the product page on uniqlo.com, pick the color and size you want, and copy the URL straight from your browser's address bar — it already contains everything the script needs (`colorDisplayCode` and `sizeDisplayCode` are query params baked right in). No need to decode anything yourself.

Commit and push your changes.

### 6. Enable Actions and test it

1. Go to the **Actions** tab of your repo (enable workflows if prompted)
2. Select **"Uniqlo stock watch"** → **Run workflow** to trigger it immediately
3. Check the run log — you should see a line per watched item (`[in stock] ...` / `[out of stock] ...`)
4. If an item is already in stock on this first run, you'll get a real Discord alert right away — that's expected, and a good way to confirm the webhook works end-to-end

After that, it runs automatically every 15 minutes via the scheduled workflow in `.github/workflows/watch.yml`.

## Adding more products later

Just paste another Uniqlo product URL into `WATCHLIST` and push. No other changes needed.

## Notes / troubleshooting

- GitHub's cron scheduler is best-effort and can lag a few minutes under load — not second-precise.
- If checks start failing with 403s, Uniqlo may have rotated their `x-fr-clientid` header value or API version (`v5`) — check the current value used by uniqlo.com in your browser's network tab and update `HEADERS` / `API` in `watch.py`.
- For hot/limited items that can sell out in minutes, pair this with Uniqlo's own "notify me" button as a backup — a 15-minute poll interval won't always beat a flash restock.
- Set `DEBUG=1` as an environment variable when running locally to dump the raw API response, useful if Uniqlo changes their response shape and stock detection stops working.
