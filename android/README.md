# mySNKRS for Android

A native Kotlin / Jetpack Compose app for mySNKRS. It's a client for the mySNKRS server that
runs on your Mac (`snkrs/web/app.py`), so the phone shows the same SQLite data as the web app:
the same inventory, the same StockX syncs. Nothing is stored or calculated separately on the phone.

**What's in it**

- **Inventory:** the totals (pairs, net if sold now, paid, profit), In stock / Sold tabs, the
  ★ Favorites filter, search, and condition/box tags. Each pair shows net now (bid), lowest ask
  (net), 6-month average, last sale and profit. You can star a pair, edit its one-line note, set
  what you paid, mark it sold (or undo), remove it, add a pair, and download the inventory as
  Excel or PDF. Pull down to refresh.
- **Check value:** style code, size, condition and box. The StockX panel shows net payout with
  the fee breakdown, lowest ask, last sale, 1M/3M/6M/3Y history (average, units, low–high, a
  step chart and the list of sales) and when it was synced. Also: retail price, the In inventory
  tags, note and favorite for pairs you own, Add to inventory, and the Other marketplaces links
  (StockX Used, GOAT, eBay, Vinted) searched at your size or all sizes, by style code, full name
  or model.
- **Light/dark theme:** System, Light or Dark, with the web app's colors. Switch it with the
  ☾/☀ button or in Settings.

## How the phone reaches the server: Tailscale

The app talks to the mySNKRS server (your Mac or your own server). Tailscale puts the phone and
that machine on a private network, so the app can reach it at home or on mobile data, and the
server isn't exposed to the internet.

1. **Server:** install Tailscale and sign in. Note its name, e.g. `<server>.<tailnet>.ts.net`
   (`tailscale status` shows it).
2. **Phone:** install Tailscale from the Play Store and sign in with the same account.
3. **Server, start mySNKRS** (it can keep listening only on 127.0.0.1):

   ```bash
   PYTHONPATH=. venv/bin/python -m snkrs.cli web
   ```

4. **Server, share it on your tailnet over HTTPS** (needs MagicDNS and HTTPS certificates turned
   on in the Tailscale admin console under DNS; Tailscale asks the first time):

   ```bash
   tailscale serve --bg 8000
   ```

   It prints the address, e.g. `https://<server>.<tailnet>.ts.net`. Only devices on your tailnet
   can open it. Stop sharing with `tailscale serve reset`.

5. **Phone, in mySNKRS:** open Settings, enter that `https://…ts.net` address and tap
   **Save and connect**.

*Without `tailscale serve`:* start the server with `--host <server's Tailscale IP>` (from
`tailscale ip -4`) and enter `http://<that IP>:8000` in the app. Tailscale still encrypts the
traffic. Avoid `--host 0.0.0.0`, which also opens the server to everyone on the same network.

## StockX syncing

Syncing happens in your own logged-in Chrome on a computer, the same as now. Open the web app at
the server's address once and drag its **⇅ Sync** button to the bookmarks bar. On StockX, open the pair,
pick the size, open **Market Data › Sales** and click that bookmark. Then pull to
refresh on the phone or tap Check value again. The app never contacts StockX for prices, uses no
StockX tokens and scrapes nothing. **Open** links just open StockX, GOAT, eBay or Vinted in your
phone's browser or app.

## Build and install

Requirements: Android Studio (or its bundled JDK 17+) and the Android SDK (platform 35).
`local.properties` points to the SDK; Android Studio creates it, or write
`sdk.dir=/Users/<you>/Library/Android/sdk` yourself.

**Android Studio:** open the `android/` folder and click Run with your phone plugged in
(USB debugging on).

**Command line:**

```bash
cd android
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The APK is `app/build/outputs/apk/debug/app-debug.apk`. You can also copy it to the phone and
open it there (allow installs from that app when asked).

**Emulator:** the emulator reaches the Mac at `10.0.2.2`, so enter `http://10.0.2.2:8000` in
Settings. No Tailscale needed.

## Code

| Path | What it is |
| --- | --- |
| `data/Api.kt` | OkHttp client for `/api/inventory`, `/api/evaluate`, `/api/stockx/history` and the exports |
| `data/Models.kt` | JSON models matching the FastAPI responses; condition/box labels |
| `data/Prefs.kt` | Server address, theme, favorites filter |
| `ui/InventoryScreen.kt` | Inventory list, totals, dialogs, Add pair |
| `ui/CheckValueScreen.kt` | Check value: StockX panel and other marketplaces |
| `ui/Chart.kt` | Sales step chart |
| `ui/theme/Theme.kt` | Light/dark palettes from `_theme.html` |

The app uses the server's existing API, and the server needed no changes for it.
