package app.mysnkrs.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.mysnkrs.SnkrsApp
import app.mysnkrs.data.ThemeMode
import app.mysnkrs.ui.theme.Snkrs
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(onSaved: () -> Unit) {
    val app = SnkrsApp.instance
    val c = Snkrs.colors
    val scope = rememberCoroutineScope()
    var url by remember { mutableStateOf(app.prefs.serverUrl) }
    var status by remember { mutableStateOf<Pair<Boolean, String>?>(null) }
    var testing by remember { mutableStateOf(false) }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Panel(Modifier.fillMaxWidth()) {
            Text("Server on your Mac", color = c.fg, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
            Text(
                "mySNKRS on the phone shows the data on your Mac: the same inventory and StockX syncs as the web app.",
                color = c.gray400, fontSize = 13.sp, modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
            )
            Field(url, { url = it }, "Server address", placeholder = "https://macbook.tailnet.ts.net", modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PrimaryButton(if (testing) "Connecting…" else "Save and connect", {
                    app.prefs.updateServerUrl(url)
                    testing = true
                    scope.launch {
                        status = try {
                            app.api.ping()
                            onSaved()
                            true to "Connected to ${app.api.url("").toString().trimEnd('/')}"
                        } catch (e: Exception) {
                            false to (e.message ?: "Could not connect")
                        }
                        testing = false
                    }
                }, enabled = !testing && url.isNotBlank())
            }
            status?.let { (ok, msg) ->
                Text(msg, color = if (ok) c.positive else c.negative, fontSize = 13.sp, modifier = Modifier.padding(top = 10.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text(
                "Use the address from `tailscale serve` (https://<mac>.<tailnet>.ts.net) or http://<Mac's Tailscale IP>:8000. " +
                    "See android/README.md in the repo for setup.",
                color = c.gray500, fontSize = 12.sp, lineHeight = 16.sp,
            )
        }

        Panel(Modifier.fillMaxWidth()) {
            Text("Theme", color = c.fg, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(ThemeMode.SYSTEM to "System", ThemeMode.LIGHT to "Light", ThemeMode.DARK to "Dark").forEach { (m, label) ->
                    Pill(label, app.prefs.themeMode == m, { app.prefs.updateThemeMode(m) })
                }
            }
        }

        Panel(Modifier.fillMaxWidth()) {
            Text("StockX prices", color = c.fg, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
            Text(
                "Prices only come from syncs you do yourself on your Mac: open the pair on StockX in Chrome, pick the size, open " +
                    "Market Data › Sales and click the ⇅ Sync bookmark. The phone app never contacts StockX for prices; " +
                    "Open links just open StockX, GOAT, eBay or Vinted in your browser.",
                color = c.gray400, fontSize = 13.sp, lineHeight = 18.sp, modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}
