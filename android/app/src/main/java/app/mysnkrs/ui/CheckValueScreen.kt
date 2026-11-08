package app.mysnkrs.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.mysnkrs.data.Evaluation
import app.mysnkrs.data.Grades
import app.mysnkrs.data.LinkOption
import app.mysnkrs.data.MarketLink
import app.mysnkrs.data.NewPair
import app.mysnkrs.data.PlatformResult
import app.mysnkrs.ui.theme.Snkrs
import java.net.URLEncoder

@Composable
fun CheckValueScreen(vm: CheckValueViewModel, onAddToInventory: (NewPair) -> Unit, onShowInInventory: (String) -> Unit) {
    val c = Snkrs.colors
    var editingNote by remember { mutableStateOf(false) }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        // Search
        Field(vm.sku, { vm.sku = it }, "Style code", placeholder = "FD2596-700", mono = true, uppercase = true, modifier = Modifier.fillMaxWidth())
        Field(vm.size, { vm.size = it }, "Size", placeholder = "US W 11.5 / EU 44", modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Picker("Condition", Grades.conditions, vm.condition, { vm.condition = it }, Modifier.weight(1f))
            Picker("Box", Grades.boxes, vm.box, { vm.box = it }, Modifier.weight(1f))
        }
        PrimaryButton(if (vm.loading) "Checking…" else "Check value", vm::check, Modifier.fillMaxWidth(), enabled = !vm.loading)

        vm.error?.let { ErrorBanner(it) }

        val r = vm.result ?: return@Column
        val sx = r.platforms["stockx"] ?: PlatformResult(platformName = "StockX")

        // Product
        Row(verticalAlignment = Alignment.CenterVertically) {
            Thumb(r.imageUrl, 64.dp)
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(r.modelName ?: r.sku, color = c.fg, fontSize = 17.sp, fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(
                    "${r.sku} · ${sx.sizeLabel ?: vm.checkedSize}" + (r.retailPrice?.let { " · Retail ${usd(it)}" } ?: ""),
                    color = c.gray400, fontSize = 13.sp, fontFamily = Mono,
                )
                vm.owned?.let { o ->
                    Spacer(Modifier.height(6.dp))
                    ConditionTags(o.condition, o.boxCondition)
                }
            }
        }
        val owned = vm.owned
        if (owned != null) {
            Text(
                if (owned.notes.isNullOrBlank()) "+ Add note" else "✎ ${owned.notes}",
                color = if (owned.notes.isNullOrBlank()) c.gray500 else c.gray300, fontSize = 12.sp,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth().clickable { editingNote = true },
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlineButton(if (owned.favorite) "★ Favorite" else "☆ Favorite", vm::toggleFavorite)
                OutlineButton(if (owned.status == "sold") "✓ Sold" else "✓ In inventory", { onShowInInventory(owned.sku) }, filled = true)
            }
        } else {
            OutlineButton("+ Add to inventory", {
                onAddToInventory(NewPair(r.sku, vm.checkedSize, r.modelName, vm.condition, vm.box, null, ""))
            })
        }

        StockXPanel(vm, r, sx)
        OtherMarketplaces(vm, r)
        Spacer(Modifier.height(16.dp))
    }

    if (editingNote) {
        vm.owned?.let { o ->
            NoteDialog(o.notes.orEmpty(), o.displayTitle, { editingNote = false }) { vm.saveNote(it); editingNote = false }
        }
    }
}

@Composable
private fun StockXPanel(vm: CheckValueViewModel, r: Evaluation, sx: PlatformResult) {
    val c = Snkrs.colors
    val context = LocalContext.current
    Panel(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("StockX", color = c.fg, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, modifier = Modifier.weight(1f))
            val url = r.marketplaceLinks["stockx"]?.url ?: sx.productUrl
                ?: "https://stockx.com/search?s=" + URLEncoder.encode(r.sku, "UTF-8")
            Text("Open on StockX ↗", color = c.gray400, fontSize = 12.sp, modifier = Modifier.clickable { openUrl(context, url) })
        }
        Spacer(Modifier.height(14.dp))

        if (!sx.isSynced) {
            Panel(Modifier.fillMaxWidth(), background = c.ink800) {
                Text("No StockX data for this size yet.", color = c.fg, fontWeight = FontWeight.Medium, fontSize = 14.sp)
                Spacer(Modifier.height(8.dp))
                listOf(
                    "On your Mac, open this sneaker on StockX in Chrome and pick your size.",
                    "Open Market Data › Sales and click the ⇅ Sync bookmark.",
                    "Then tap Check value again here.",
                ).forEachIndexed { i, s -> Text("${i + 1}. $s", color = c.gray400, fontSize = 13.sp, modifier = Modifier.padding(top = 2.dp)) }
            }
            return@Panel
        }

        // Top stats
        var showBreakdown by remember { mutableStateOf(false) }
        Panel(Modifier.fillMaxWidth(), background = c.ink700, padding = 14.dp) {
            Text("Net payout if you sell now", color = c.gray400, fontSize = 12.sp)
            Text(usd(sx.estimatedNetPayout), color = c.fg, fontSize = 28.sp, fontWeight = FontWeight.Bold, style = Tnum)
            Text(
                (if (showBreakdown) "▾ " else "▸ ") + "Highest bid " + usd(sx.highestBid),
                color = c.gray400, fontSize = 12.sp,
                modifier = Modifier.padding(top = 6.dp).clickable { showBreakdown = !showBreakdown },
            )
            val b = sx.payoutBreakdown
            AnimatedVisibility(showBreakdown && b != null) {
                if (b != null) Column(Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    BreakdownRow("Your ask (bid)", usd(b.price))
                    BreakdownRow("Transaction fee (9%)", "−" + usd(b.transactionFee))
                    BreakdownRow("Payment proc. (3%)", "−" + usd(b.processingFee))
                    BreakdownRow("Shipping", "−" + usd(b.shipping))
                    HorizontalDivider(color = c.ink600)
                    BreakdownRow("Total payout", usd(b.payout), strong = true)
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            val last = sx.recentSales.firstOrNull()
            Panel(Modifier.weight(1f), background = c.ink700, padding = 14.dp) {
                Text("Lowest ask", color = c.gray400, fontSize = 12.sp)
                Text(usd(sx.lowestAsk), color = c.fg, fontSize = 22.sp, fontWeight = FontWeight.Bold, style = Tnum)
                sx.lowestAskNetPayout?.let { Text("${usd(it)} net if you match it", color = c.gray400, fontSize = 11.sp) }
            }
            Panel(Modifier.weight(1f), background = c.ink700, padding = 14.dp) {
                Text("Last sale", color = c.gray400, fontSize = 12.sp)
                Text(usd(last?.price), color = c.fg, fontSize = 22.sp, fontWeight = FontWeight.Bold, style = Tnum)
                if (last != null) Text(fmtLong(parseLocal(last.date)), color = c.gray400, fontSize = 11.sp)
            }
        }

        // History
        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("1m" to "1M", "3m" to "3M", "6m" to "6M", "3y" to "3Y").forEach { (k, label) ->
                Pill(label, vm.range == k, { vm.selectRange(k) })
            }
        }
        val h = vm.history
        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            HistoryStat("Avg sale price", usd(h?.avgPrice), Modifier.weight(1f))
            HistoryStat("Units sold", h?.unitsSold?.toString() ?: "–", Modifier.weight(0.8f))
            HistoryStat("Low – High", if (h != null && h.unitsSold > 0) "${usd(h.low)} – ${usd(h.high)}" else "–", Modifier.weight(1.4f))
        }
        Spacer(Modifier.height(10.dp))
        if (h != null) {
            SalesChart(h.points, h.range)
            h.oldestSale?.let {
                Text(
                    "${h.salesOnFile} sales on file, back to ${fmtLong(parseLocal(it))}. StockX only shows the latest 50 sales per size, " +
                        "so older history builds up as you keep syncing.",
                    color = c.gray500, fontSize = 11.sp, lineHeight = 15.sp, modifier = Modifier.padding(top = 6.dp),
                )
            }

            // Sales list
            Spacer(Modifier.height(10.dp))
            HorizontalDivider(color = c.ink700)
            SaleRow("Date", "Time", "Size", "Sale price", header = true)
            if (h.points.isEmpty()) {
                Text("No sales in this period", color = c.gray500, fontSize = 13.sp, modifier = Modifier.padding(vertical = 12.dp))
            }
            h.points.asReversed().forEach { s ->
                val d = parseLocal(s.date)
                HorizontalDivider(color = c.ink700)
                SaleRow(fmtLong(d), fmtTime(d), s.size.orEmpty(), usd(s.price))
            }
        }
        sx.syncedAt?.let {
            Text(
                "Synced from your StockX session on ${fmtLong(parseUtc(it))}. Sync again on your Mac for fresh prices.",
                color = c.gray500, fontSize = 11.sp, modifier = Modifier.padding(top = 10.dp),
            )
        }
    }
}

@Composable
private fun BreakdownRow(label: String, value: String, strong: Boolean = false) {
    val c = Snkrs.colors
    Row(Modifier.fillMaxWidth()) {
        Text(label, color = if (strong) c.gray100 else c.gray400, fontSize = 12.sp, fontWeight = if (strong) FontWeight.SemiBold else null, modifier = Modifier.weight(1f))
        Text(value, color = if (strong) c.gray100 else c.gray400, fontSize = 12.sp, fontWeight = if (strong) FontWeight.SemiBold else null, style = Tnum)
    }
}

@Composable
private fun HistoryStat(label: String, value: String, modifier: Modifier) {
    val c = Snkrs.colors
    Column(modifier) {
        Text(label, color = c.gray400, fontSize = 11.sp, maxLines = 1)
        Text(value, color = c.fg, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, style = Tnum, maxLines = 1)
    }
}

@Composable
private fun SaleRow(date: String, time: String, size: String, price: String, header: Boolean = false) {
    val c = Snkrs.colors
    val fs = if (header) 11.sp else 13.sp
    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Text(date, color = if (header) c.gray400 else c.gray200, fontSize = fs, modifier = Modifier.weight(1.3f), style = Tnum)
        Text(time, color = c.gray400, fontSize = fs, modifier = Modifier.weight(1f), style = Tnum)
        Text(size, color = c.gray400, fontSize = fs, modifier = Modifier.weight(1f), maxLines = 1, style = Tnum)
        Text(price, color = if (header) c.gray400 else c.fg, fontSize = fs, modifier = Modifier.weight(0.9f), style = Tnum, textAlign = androidx.compose.ui.text.style.TextAlign.End)
    }
}

/** Same choice as the web: your size or all sizes, by style code, full name or model. */
private fun pickLink(l: MarketLink, ownSize: Boolean, by: String): LinkOption =
    l.options.firstOrNull { it.by == by && (it.sizeLabel != null) == ownSize }
        ?: l.options.firstOrNull { it.by == by } // e.g. GOAT search has no size filter
        ?: l.options.firstOrNull()
        ?: LinkOption("code", null, l.url.orEmpty())

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun OtherMarketplaces(vm: CheckValueViewModel, r: Evaluation) {
    val c = Snkrs.colors
    val context = LocalContext.current
    val links = r.marketplaceLinks
    val allOptions = links.values.flatMap { it.options }
    val sizeLabel = allOptions.firstOrNull { it.sizeLabel != null }?.sizeLabel
    fun any(by: String) = allOptions.any { it.by == by }
    // A pair without a known size or name falls back for now, without changing your choice
    val ownSize = vm.mktOwnSize && sizeLabel != null
    val by = if (any(vm.mktBy)) vm.mktBy else "code"

    // StockX Used (its second-hand Listings) has no data in the app; sellers pay no fees there for now
    val rows = buildList {
        add("stockx_used" to PlatformResult(platformName = "StockX Used"))
        r.platforms.forEach { (id, p) -> if (id != "stockx") add(id to p) }
    }.filter { (id, _) -> links[id] != null }

    Panel(Modifier.fillMaxWidth()) {
        Text("Other marketplaces", color = c.fg, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
        Spacer(Modifier.height(10.dp))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            if (sizeLabel != null) {
                Pill(sizeLabel, ownSize, { vm.mktOwnSize = true })
                Pill("All sizes", !ownSize, { vm.mktOwnSize = false })
            }
        }
        Spacer(Modifier.height(6.dp))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Pill("Style code", by == "code", { vm.mktBy = "code" })
            if (any("name")) Pill("Full name", by == "name", { vm.mktBy = "name" })
            if (any("model")) Pill("Model", by == "model", { vm.mktBy = "model" })
        }
        Spacer(Modifier.height(8.dp))
        rows.forEach { (id, p) ->
            HorizontalDivider(color = c.ink700)
            val link = pickLink(links.getValue(id), ownSize, by)
            val fee = when {
                id == "stockx_used" -> "0% fee · Launch offer"
                p.sellerFeePercentage > 0 -> "${trimNum(p.sellerFeePercentage)}% + ${usd(p.sellerFixedFee)} fee"
                else -> "0% fee"
            } + if (ownSize && link.sizeLabel == null) " · shows all sizes" else ""
            Row(Modifier.fillMaxWidth().padding(vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(p.platformName, color = c.fg, fontSize = 14.sp)
                    Text(fee, color = c.gray500, fontSize = 11.sp)
                }
                if (p.lowestAsk != null) {
                    Column(horizontalAlignment = Alignment.End, modifier = Modifier.padding(end = 10.dp)) {
                        Text(usd(p.lowestAsk), color = c.fg, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, style = Tnum)
                        p.estimatedNetPayout?.let { Text("${usd(it)} net", color = c.gray500, fontSize = 11.sp, style = Tnum) }
                    }
                }
                OutlineButton("Open ↗", { openUrl(context, link.url) })
            }
        }
        HorizontalDivider(color = c.ink700)
        Text(
            buildAnnotatedString {
                append("Open searches StockX Used, GOAT, eBay or Vinted for this pair. Not every seller lists the style code or the full name: ")
                withStyle(SpanStyle(color = c.gray300)) { append("Model") }
                append(" searches just the model, which finds the most listings, so check the results match your pair.")
            },
            color = c.gray500, fontSize = 11.sp, lineHeight = 15.sp, modifier = Modifier.padding(top = 10.dp),
        )
    }
}

private fun trimNum(v: Double): String = if (v % 1.0 == 0.0) v.toLong().toString() else v.toString()
