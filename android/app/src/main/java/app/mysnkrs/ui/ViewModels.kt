package app.mysnkrs.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.mysnkrs.SnkrsApp
import app.mysnkrs.data.Evaluation
import app.mysnkrs.data.Grades
import app.mysnkrs.data.InventoryItem
import app.mysnkrs.data.InventoryResponse
import app.mysnkrs.data.NewPair
import app.mysnkrs.data.SalesHistory
import kotlinx.coroutines.async
import kotlinx.coroutines.launch

private val api get() = SnkrsApp.instance.api
private val prefs get() = SnkrsApp.instance.prefs

class InventoryViewModel : ViewModel() {
    var status by mutableStateOf("for_sale")
        private set
    val favoritesOnly: Boolean get() = prefs.favoritesOnly
    var data by mutableStateOf<InventoryResponse?>(null)
        private set
    var loading by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var search by mutableStateOf("")
    /** Short-lived message for the snackbar (failed edits). */
    var message by mutableStateOf<String?>(null)

    fun load() {
        viewModelScope.launch {
            loading = true
            try {
                data = api.inventory(status, favoritesOnly)
                error = null
            } catch (e: Exception) {
                error = e.message
            } finally {
                loading = false
            }
        }
    }

    fun selectStatus(s: String) {
        if (s == status) return
        status = s
        data = null
        load()
    }

    fun toggleFavoritesOnly() {
        prefs.updateFavoritesOnly(!favoritesOnly)
        load()
    }

    /** Same order as the web: highest sell-now payout first, then synced pairs. */
    fun visibleItems(): List<InventoryItem> {
        val q = search.trim().lowercase()
        return data?.items.orEmpty()
            .filter { q.isEmpty() || "${it.displayTitle} ${it.sku} ${it.size} ${it.notes.orEmpty()}".lowercase().contains(q) }
            .sortedWith(compareByDescending<InventoryItem> { it.netPayoutNow ?: -1.0 }.thenByDescending { it.synced })
    }

    private fun edit(id: Int, fields: Map<String, Any?>) {
        viewModelScope.launch {
            try {
                api.updatePair(id, fields)
            } catch (e: Exception) {
                message = e.message
            }
            load()
        }
    }

    fun toggleFavorite(item: InventoryItem) = edit(item.id, mapOf("favorite" to !item.favorite))
    fun setNote(item: InventoryItem, notes: String) { if (notes != item.notes.orEmpty()) edit(item.id, mapOf("notes" to notes)) }
    fun setPaid(item: InventoryItem, price: Double?) = edit(item.id, mapOf("purchase_price" to price))
    fun markSold(item: InventoryItem, price: Double?, platform: String?) =
        edit(item.id, mapOf("status" to "sold", "sold_price" to price, "sold_platform" to platform))
    fun markUnsold(item: InventoryItem) = edit(item.id, mapOf("status" to "for_sale"))

    fun delete(item: InventoryItem) {
        viewModelScope.launch {
            try {
                api.deletePair(item.id)
            } catch (e: Exception) {
                message = e.message
            }
            load()
        }
    }

    fun add(p: NewPair, onDone: (Boolean) -> Unit) {
        viewModelScope.launch {
            try {
                api.addPair(p)
                onDone(true)
                load()
            } catch (e: Exception) {
                message = "Could not add: ${e.message}"
                onDone(false)
            }
        }
    }

    fun exportUrl(fmt: String): String? = runCatching { api.exportUrl(fmt, status, favoritesOnly) }.getOrNull()
}

class CheckValueViewModel : ViewModel() {
    var sku by mutableStateOf("")
    var size by mutableStateOf("US W 11.5")
    var condition by mutableStateOf("deadstock")
    var box by mutableStateOf("original_good")

    var loading by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var result by mutableStateOf<Evaluation?>(null)
        private set
    /** Size the shown result was checked for (the form can change afterwards). */
    var checkedSize by mutableStateOf("")
        private set

    var range by mutableStateOf("6m")
        private set
    var history by mutableStateOf<SalesHistory?>(null)
        private set

    var owned by mutableStateOf<InventoryItem?>(null)
        private set
    private var openedItemId: Int? = null

    // What the other-marketplace Open links search for
    var mktOwnSize by mutableStateOf(true)
    var mktBy by mutableStateOf("code")

    var message by mutableStateOf<String?>(null)

    /** Opening a pair from the inventory fills the form and checks it right away. */
    fun open(item: InventoryItem) {
        sku = item.sku
        size = item.size
        condition = item.condition
        box = item.boxCondition
        openedItemId = item.id
        check()
    }

    fun check() {
        val s = sku.trim().uppercase()
        if (s.isEmpty() || size.isBlank()) {
            error = "Enter a style code and a size."
            return
        }
        viewModelScope.launch {
            loading = true
            error = null
            try {
                val r = api.evaluate(s, size.trim(), condition, box)
                checkedSize = size.trim()
                result = r
                history = null
                if (r.platforms["stockx"]?.isSynced == true) loadHistory()
                loadOwnership(r.sku, checkedSize)
            } catch (e: Exception) {
                error = e.message
            } finally {
                loading = false
            }
        }
    }

    fun selectRange(r: String) {
        range = r
        loadHistory()
    }

    private fun loadHistory() {
        val r = result ?: return
        val wanted = range
        viewModelScope.launch {
            try {
                val h = api.history(r.sku, checkedSize, wanted)
                if (wanted == range) history = h
            } catch (e: Exception) {
                message = e.message
            }
        }
    }

    /** If this pair is in your inventory, show its tags, note and favorite star. */
    private suspend fun loadOwnership(sku: String, size: String) {
        try {
            val forSale = viewModelScope.async { api.inventory("for_sale", false) }
            val sold = viewModelScope.async { api.inventory("sold", false) }
            val fs = forSale.await().items
            val all = fs + sold.await().items
            val key = Grades.sizeKey(size)
            fun same(i: InventoryItem) = i.sku == sku.uppercase() && Grades.sizeKey(i.size) == key
            owned = all.firstOrNull { it.id == openedItemId && same(it) } ?: fs.firstOrNull { same(it) }
        } catch (e: Exception) {
            owned = null
        }
    }

    private fun editOwned(fields: Map<String, Any?>, apply: (InventoryItem) -> InventoryItem) {
        val item = owned ?: return
        viewModelScope.launch {
            try {
                api.updatePair(item.id, fields)
                owned = apply(item)
            } catch (e: Exception) {
                message = e.message
            }
        }
    }

    fun toggleFavorite() {
        val item = owned ?: return
        editOwned(mapOf("favorite" to !item.favorite)) { it.copy(favorite = !item.favorite) }
    }

    fun saveNote(notes: String) {
        val item = owned ?: return
        if (notes == item.notes.orEmpty()) return
        editOwned(mapOf("notes" to notes)) { it.copy(notes = notes) }
    }

    /** After adding the shown pair to the inventory, show it as owned. */
    fun refreshOwnership() {
        val r = result ?: return
        viewModelScope.launch { loadOwnership(r.sku, checkedSize) }
    }
}
