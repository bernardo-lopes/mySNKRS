package app.mysnkrs

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import app.mysnkrs.data.NewPair
import app.mysnkrs.data.ThemeMode
import app.mysnkrs.ui.AddPairDialog
import app.mysnkrs.ui.CheckValueScreen
import app.mysnkrs.ui.CheckValueViewModel
import app.mysnkrs.ui.InventoryScreen
import app.mysnkrs.ui.InventoryViewModel
import app.mysnkrs.ui.SettingsScreen
import app.mysnkrs.ui.theme.DarkPalette
import app.mysnkrs.ui.theme.LightPalette
import app.mysnkrs.ui.theme.Snkrs
import app.mysnkrs.ui.theme.SnkrsTheme

private enum class Tab(val label: String) { CHECK("Check value"), INVENTORY("Inventory"), SETTINGS("Settings") }

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = SnkrsApp.instance.prefs
        setContent {
            val light = when (prefs.themeMode) {
                ThemeMode.LIGHT -> true
                ThemeMode.DARK -> false
                ThemeMode.SYSTEM -> !isSystemInDarkTheme()
            }
            LaunchedEffect(light) {
                val bg = (if (light) LightPalette else DarkPalette).ink900.toArgb()
                val style = if (light) SystemBarStyle.light(bg, bg) else SystemBarStyle.dark(bg)
                enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
            }
            SnkrsTheme(light) { App(light) }
        }
    }
}

@Composable
private fun App(light: Boolean) {
    val prefs = SnkrsApp.instance.prefs
    val c = Snkrs.colors
    val inventory: InventoryViewModel = viewModel()
    val check: CheckValueViewModel = viewModel()
    var tab by rememberSaveable { mutableStateOf(if (prefs.serverUrl.isBlank()) Tab.SETTINGS else Tab.INVENTORY) }
    var adding by remember { mutableStateOf<NewPair?>(null) }
    var addOpen by remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }

    BackHandler(enabled = tab != Tab.INVENTORY && prefs.serverUrl.isNotBlank()) { tab = Tab.INVENTORY }

    LaunchedEffect(tab) { if (tab == Tab.INVENTORY && prefs.serverUrl.isNotBlank()) inventory.load() }
    LaunchedEffect(inventory.message) { inventory.message?.let { snackbar.showSnackbar(it); inventory.message = null } }
    LaunchedEffect(check.message) { check.message?.let { snackbar.showSnackbar(it); check.message = null } }

    Scaffold(
        containerColor = c.ink900,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            Column(Modifier.statusBarsPadding()) {
                Row(Modifier.fillMaxWidth().height(52.dp).padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("mySNKRS", color = c.fg, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    Spacer(Modifier.weight(1f))
                    // Same quick light/dark switch as the web header
                    Text(
                        if (light) "☾" else "☀\uFE0E", color = c.gray300, fontSize = 20.sp,
                        modifier = Modifier.clickable { prefs.updateThemeMode(if (light) ThemeMode.DARK else ThemeMode.LIGHT) }.padding(8.dp),
                    )
                }
                HorizontalDivider(color = c.ink700)
            }
        },
        bottomBar = {
            NavigationBar(containerColor = c.ink800) {
                Tab.entries.forEach { t ->
                    NavigationBarItem(
                        selected = tab == t,
                        onClick = { tab = t },
                        icon = {
                            Icon(
                                when (t) { Tab.CHECK -> Icons.Filled.Search; Tab.INVENTORY -> Icons.AutoMirrored.Filled.List; Tab.SETTINGS -> Icons.Filled.Settings },
                                contentDescription = null,
                            )
                        },
                        label = { Text(t.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = c.fgInverse, indicatorColor = c.fg,
                            selectedTextColor = c.fg, unselectedIconColor = c.gray400, unselectedTextColor = c.gray400,
                        ),
                    )
                }
            }
        },
    ) { inner ->
        Column(Modifier.fillMaxSize().padding(inner)) {
            when (tab) {
                Tab.CHECK -> CheckValueScreen(
                    check,
                    onAddToInventory = { adding = it; addOpen = true },
                    onShowInInventory = { sku -> inventory.search = sku; tab = Tab.INVENTORY },
                )
                Tab.INVENTORY -> InventoryScreen(
                    inventory,
                    onOpen = { item -> check.open(item); tab = Tab.CHECK },
                    onAdd = { adding = null; addOpen = true },
                )
                Tab.SETTINGS -> SettingsScreen(onSaved = { inventory.load() })
            }
        }
    }

    if (addOpen) {
        AddPairDialog(adding, onDismiss = { addOpen = false }) { pair, done ->
            inventory.add(pair) { ok ->
                done(ok)
                if (ok) {
                    addOpen = false
                    check.refreshOwnership()
                }
            }
        }
    }
}
