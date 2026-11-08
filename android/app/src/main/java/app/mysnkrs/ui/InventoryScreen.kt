package app.mysnkrs.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.mysnkrs.data.Grades
import app.mysnkrs.data.InventoryItem
import app.mysnkrs.data.NewPair
import app.mysnkrs.ui.theme.Snkrs

private sealed interface InvDialog {
    data class Note(val item: InventoryItem) : InvDialog
    data class Paid(val item: InventoryItem) : InvDialog
    data class Sold(val item: InventoryItem) : InvDialog
    data class Remove(val item: InventoryItem) : InvDialog
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InventoryScreen(vm: InventoryViewModel, onOpen: (InventoryItem) -> Unit, onAdd: () -> Unit) {
    val c = Snkrs.colors
    val context = LocalContext.current
    var dialog by remember { mutableStateOf<InvDialog?>(null) }
    val data = vm.data
    val items = vm.visibleItems()

    PullToRefreshBox(isRefreshing = vm.loading && data != null, onRefresh = vm::load, modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            contentPadding = ScreenPadding,
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxSize(),
        ) {
            vm.error?.let { err -> item { ErrorBanner(err, vm::load) } }

            data?.totals?.let { t ->
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(Modifier.height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            StatCard("Pairs", "${t.pairs}", "${t.synced} synced · ${t.stockxEligible} DS in original box", Modifier.weight(1f).fillMaxHeight())
                            StatCard("Net if sold now on StockX", usd(t.netPayoutNow), "${t.priced} of ${t.stockxEligible} StockX-eligible pairs priced", Modifier.weight(1f).fillMaxHeight())
                        }
                        Row(Modifier.height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            StatCard("Paid", usd(t.paid), "Edit with \"Paid\" on each pair", Modifier.weight(1f).fillMaxHeight())
                            StatCard(
                                "Profit if sold now", usd(t.profitNow), "Priced pairs with a purchase price", Modifier.weight(1f).fillMaxHeight(),
                                valueColor = profitColor(t.profitNow),
                            )
                        }
                    }
                }
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
                        Pill("In stock", vm.status == "for_sale", { vm.selectStatus("for_sale") })
                        Pill("Sold", vm.status == "sold", { vm.selectStatus("sold") })
                        Pill("★ Favorites", vm.favoritesOnly, vm::toggleFavoritesOnly, activeBg = c.star, activeFg = Color(0xFF111318))
                    }
                    Field(vm.search, { vm.search = it }, "Search", placeholder = "Name, style code, size or note", modifier = Modifier.fillMaxWidth())
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        OutlineButton("+ Add pair", onAdd, filled = true)
                        Spacer(Modifier.weight(1f))
                        OutlineButton("↓ Excel", { openUrl(context, vm.exportUrl("xlsx")) })
                        OutlineButton("↓ PDF", { openUrl(context, vm.exportUrl("pdf")) })
                    }
                }
            }

            if (data == null && vm.loading) {
                item { Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = c.fg) } }
            } else if (data != null && items.isEmpty()) {
                item {
                    Text(
                        when {
                            vm.favoritesOnly -> "No favorites here yet. Tap ☆ on a pair to add it."
                            vm.status == "sold" -> "No sold pairs yet"
                            else -> "No pairs yet. Use + Add pair."
                        },
                        color = c.gray500, fontSize = 14.sp, textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth().padding(vertical = 32.dp),
                    )
                }
            }

            items(items, key = { it.id }) { item ->
                InventoryCard(
                    item = item,
                    sold = vm.status == "sold",
                    onOpen = { onOpen(item) },
                    onFavorite = { vm.toggleFavorite(item) },
                    onNote = { dialog = InvDialog.Note(item) },
                    onPaid = { dialog = InvDialog.Paid(item) },
                    onSold = { dialog = InvDialog.Sold(item) },
                    onUnsold = { vm.markUnsold(item) },
                    onRemove = { dialog = InvDialog.Remove(item) },
                )
            }

            if (data != null) {
                item {
                    Text(
                        "Prices come from your StockX syncs on your Mac. To price a pair: on the Mac, open it on StockX, pick its size, open " +
                            "Market Data › Sales and click the ⇅ Sync bookmark, then pull down here to refresh. Net if you sell now is the highest bid " +
                            "minus 9% + 3% + \$5 shipping; under the lowest ask is the net if you list at that price. Both show only for DS pairs in " +
                            "their original box, since StockX doesn't accept anything else.",
                        color = c.gray500, fontSize = 11.sp, lineHeight = 15.sp,
                        modifier = Modifier.padding(top = 4.dp, bottom = 24.dp),
                    )
                }
            }
        }
    }

    when (val d = dialog) {
        is InvDialog.Note -> NoteDialog(d.item.notes.orEmpty(), d.item.displayTitle, { dialog = null }) {
            vm.setNote(d.item, it); dialog = null
        }
        is InvDialog.Paid -> PromptDialog(
            "What you paid", "\"${d.item.displayTitle}\". Leave empty to clear.",
            listOf(Triple("Paid ($)", d.item.purchasePrice?.let(::plain) ?: "", true)), "Save", { dialog = null },
        ) { (price) ->
            if (price.isEmpty() || price.toDoubleOrNull() != null) {
                vm.setPaid(d.item, price.toDoubleOrNull()); dialog = null
            }
        }
        is InvDialog.Sold -> PromptDialog(
            "Mark as sold", "\"${d.item.displayTitle}\"",
            listOf(Triple("Sold for ($)", d.item.netPayoutNow?.let(::plain) ?: "", true), Triple("Where did it sell?", "StockX", false)),
            "Mark sold", { dialog = null },
        ) { (price, platform) ->
            vm.markSold(d.item, price.toDoubleOrNull(), platform.ifBlank { null }); dialog = null
        }
        is InvDialog.Remove -> AlertDialog(
            onDismissRequest = { dialog = null },
            title = { Text("Remove pair?", fontSize = 18.sp) },
            text = { Text("Remove \"${d.item.displayTitle}\" (${d.item.size}) from your inventory?") },
            confirmButton = { TextButton(onClick = { vm.delete(d.item); dialog = null }) { Text("Remove", color = c.negative) } },
            dismissButton = { TextButton(onClick = { dialog = null }) { Text("Cancel") } },
            containerColor = c.ink800,
        )
        null -> {}
    }
}

private fun plain(v: Double): String = if (v % 1.0 == 0.0) v.toLong().toString() else v.toString()

@Composable
fun profitColor(v: Double?): Color? = when {
    v == null -> null
    v > 0 -> Snkrs.colors.positive
    v < 0 -> Snkrs.colors.negative
    else -> null
}

@Composable
private fun InventoryCard(
    item: InventoryItem,
    sold: Boolean,
    onOpen: () -> Unit,
    onFavorite: () -> Unit,
    onNote: () -> Unit,
    onPaid: () -> Unit,
    onSold: () -> Unit,
    onUnsold: () -> Unit,
    onRemove: () -> Unit,
) {
    val c = Snkrs.colors
    Panel(Modifier.fillMaxWidth(), padding = 14.dp) {
        Row(verticalAlignment = Alignment.Top) {
            Box(Modifier.clickable(onClick = onOpen)) { Thumb(item.imageUrl, 52.dp) }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    item.displayTitle, color = c.fg, fontWeight = FontWeight.Medium, fontSize = 15.sp,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.clickable(onClick = onOpen),
                )
                Text("${item.sku} · ${item.size}", color = c.gray500, fontSize = 12.sp, fontFamily = Mono)
                Spacer(Modifier.height(4.dp))
                ConditionTags(item.condition, item.boxCondition)
            }
            Text(
                if (item.favorite) "★" else "☆",
                color = if (item.favorite) c.star else c.gray500, fontSize = 22.sp,
                modifier = Modifier.clickable(onClick = onFavorite).padding(start = 8.dp, bottom = 8.dp),
            )
        }

        Text(
            if (item.notes.isNullOrBlank()) "+ Add note" else "✎ ${item.notes}",
            color = if (item.notes.isNullOrBlank()) c.gray500 else c.gray300, fontSize = 12.sp,
            maxLines = 1, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.fillMaxWidth().clickable(onClick = onNote).padding(vertical = 8.dp),
        )

        HorizontalDivider(color = c.ink700)
        Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val net = when {
                item.netPayoutNow != null -> usd(item.netPayoutNow)
                item.synced && !item.stockxEligible -> "Not on StockX"
                item.synced -> "–"
                else -> "Not synced"
            }
            Metric("Net now", net, item.highestBid?.let { "bid ${usd(it)}" }, Modifier.weight(1.2f), strong = item.netPayoutNow != null)
            Metric("Lowest ask", usd(item.lowestAsk), item.lowestAskNetPayout?.let { "${usd(it)} net" }, Modifier.weight(1f))
            Metric("Avg · 6M", usd(item.avgSale6m), if (item.synced) "${item.unitsSold6m ?: 0} sold" else null, Modifier.weight(1f).fillMaxHeight())
            Metric("Last sale", usd(item.lastSale), fmtShort(parseLocal(item.lastSaleDate)).ifBlank { null }, Modifier.weight(1f).fillMaxHeight())
        }
        HorizontalDivider(color = c.ink700)

        Row(Modifier.fillMaxWidth().padding(top = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Profit", color = c.gray400, fontSize = 11.sp)
                Text(usd(item.profitNow), color = profitColor(item.profitNow) ?: c.gray200, fontSize = 13.sp, style = Tnum)
            }
            if (sold) {
                Text(
                    usd(item.soldPrice) + (item.soldPlatform?.let { " · $it" } ?: ""),
                    color = c.gray400, fontSize = 12.sp, modifier = Modifier.padding(end = 4.dp),
                )
            }
            Action("Paid", onPaid)
            if (sold) Action("Undo", onUnsold) else Action("Sold", onSold)
            Action("Remove", onRemove, color = c.gray500)
        }
    }
}

@Composable
private fun Metric(label: String, value: String, sub: String?, modifier: Modifier, strong: Boolean = false) {
    val c = Snkrs.colors
    Column(modifier) {
        Text(label, color = c.gray400, fontSize = 11.sp, maxLines = 1)
        Text(
            value, color = if (strong) c.fg else c.gray200, fontSize = if (value.startsWith("$") || value == "–") 14.sp else 11.sp,
            fontWeight = if (strong) FontWeight.SemiBold else FontWeight.Normal, style = Tnum, maxLines = 1,
        )
        if (sub != null) Text(sub, color = c.gray500, fontSize = 11.sp, style = Tnum, maxLines = 1)
    }
}

@Composable
private fun Action(text: String, onClick: () -> Unit, color: Color = Snkrs.colors.gray400) {
    Text(text, color = color, fontSize = 13.sp, modifier = Modifier.clickable(onClick = onClick).padding(horizontal = 8.dp, vertical = 6.dp))
}

/** "+ Add pair" form; prefilled when adding the pair shown on Check value. */
@Composable
fun AddPairDialog(prefill: NewPair?, onDismiss: () -> Unit, onAdd: (NewPair, (Boolean) -> Unit) -> Unit) {
    var sku by remember { mutableStateOf(prefill?.sku ?: "") }
    var name by remember { mutableStateOf(prefill?.modelName ?: "") }
    var size by remember { mutableStateOf(prefill?.size ?: "") }
    var condition by remember { mutableStateOf(prefill?.condition ?: "deadstock") }
    var box by remember { mutableStateOf(prefill?.boxCondition ?: "original_good") }
    var paid by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val valid = sku.isNotBlank() && size.isNotBlank() && (paid.isBlank() || paid.toDoubleOrNull() != null)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add pair", fontSize = 18.sp) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Field(sku, { sku = it }, "Style code", placeholder = "FD2596-700", mono = true, uppercase = true, modifier = Modifier.fillMaxWidth())
                Field(name, { name = it }, "Name", placeholder = "Jordan 1 High Reverse Laney", modifier = Modifier.fillMaxWidth())
                Field(size, { size = it }, "Size", placeholder = "US W 11.5", modifier = Modifier.fillMaxWidth())
                Picker("Condition", Grades.conditions, condition, { condition = it }, Modifier.fillMaxWidth())
                Picker("Box", Grades.boxes, box, { box = it }, Modifier.fillMaxWidth())
                Field(paid, { paid = it }, "Paid ($)", placeholder = "optional", number = true, modifier = Modifier.fillMaxWidth())
                Field(notes, { notes = it }, "Note", placeholder = "optional, e.g. small scuff on left toe", maxLength = Grades.NOTE_MAX, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(enabled = valid && !busy, onClick = {
                busy = true
                onAdd(NewPair(sku.trim(), size.trim(), name.trim().ifBlank { null }, condition, box, paid.toDoubleOrNull(), notes.trim())) { ok -> if (!ok) busy = false }
            }) { Text("Add to inventory") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        containerColor = Snkrs.colors.ink800,
    )
}
