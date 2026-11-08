package app.mysnkrs.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// JSON shapes of the mySNKRS FastAPI server (snkrs/web/app.py). Field names are mapped from
// snake_case by the JSON config in Api.kt; unknown fields are ignored.

@Serializable
data class InventoryResponse(
    val items: List<InventoryItem> = emptyList(),
    val totals: Totals = Totals(),
)

@Serializable
data class Totals(
    val pairs: Int = 0,
    val synced: Int = 0,
    val stockxEligible: Int = 0,
    val priced: Int = 0,
    val netPayoutNow: Double? = null,
    val paid: Double? = null,
    val profitNow: Double? = null,
)

@Serializable
data class InventoryItem(
    val id: Int,
    val sku: String,
    val modelName: String? = null,
    val size: String,
    val condition: String = "deadstock",
    val boxCondition: String = "original_good",
    val purchasePrice: Double? = null,
    val status: String = "for_sale",
    val soldPrice: Double? = null,
    val soldPlatform: String? = null,
    val notes: String? = null,
    val favorite: Boolean = false,
    val title: String = "",
    val imageUrl: String? = null,
    val stockxUrl: String? = null,
    val retailPrice: Double? = null,
    val synced: Boolean = false,
    val syncedAt: String? = null,
    val stockxEligible: Boolean = false,
    val highestBid: Double? = null,
    val lowestAsk: Double? = null,
    val lowestAskNetPayout: Double? = null,
    @SerialName("avg_sale_6m") val avgSale6m: Double? = null,
    @SerialName("units_sold_6m") val unitsSold6m: Int? = null,
    val lastSale: Double? = null,
    val lastSaleDate: String? = null,
    val netPayoutNow: Double? = null,
    val profitNow: Double? = null,
) {
    val displayTitle: String get() = title.ifBlank { modelName ?: sku }
}

@Serializable
data class Evaluation(
    val sku: String,
    val modelName: String? = null,
    val retailPrice: Double? = null,
    val imageUrl: String? = null,
    val platforms: Map<String, PlatformResult> = emptyMap(),
    val marketplaceLinks: Map<String, MarketLink> = emptyMap(),
)

@Serializable
data class PlatformResult(
    val platformName: String = "",
    val platformId: String? = null,
    val dataSource: String? = null,
    val lowestAsk: Double? = null,
    val highestBid: Double? = null,
    val lastSalePrice: Double? = null,
    val recentSales: List<Sale> = emptyList(),
    val sellerFeePercentage: Double = 0.0,
    val sellerFixedFee: Double = 0.0,
    val estimatedNetPayout: Double? = null,
    val notes: String? = null,
    val productUrl: String? = null,
    val sizeLabel: String? = null,
    val syncedAt: String? = null,
    val lowestAskNetPayout: Double? = null,
    val payoutBreakdown: PayoutBreakdown? = null,
) {
    val isSynced: Boolean get() = dataSource == "browser_sync"
}

@Serializable
data class PayoutBreakdown(
    val price: Double,
    val transactionFee: Double,
    val processingFee: Double,
    val shipping: Double,
    val payout: Double,
)

@Serializable
data class Sale(
    val date: String,
    val price: Double,
    val size: String? = null,
)

@Serializable
data class MarketLink(
    val url: String? = null,
    val sizeLabel: String? = null,
    val options: List<LinkOption> = emptyList(),
)

@Serializable
data class LinkOption(
    val by: String,
    val sizeLabel: String? = null,
    val url: String,
)

@Serializable
data class SalesHistory(
    val range: String = "6m",
    val points: List<Sale> = emptyList(),
    val unitsSold: Int = 0,
    val avgPrice: Double? = null,
    val high: Double? = null,
    val low: Double? = null,
    val oldestSale: String? = null,
    val salesOnFile: Int = 0,
)

/** Fields for a new inventory pair (POST /api/inventory). */
data class NewPair(
    val sku: String,
    val size: String,
    val modelName: String?,
    val condition: String,
    val boxCondition: String,
    val purchasePrice: Double?,
    val notes: String,
)

/** Same condition and box values as the web forms. */
object Grades {
    val conditions = listOf(
        "deadstock" to "DS",
        "vnds" to "Not DS",
        "used_like_new" to "Used · like new",
        "used_good" to "Used",
        "used_fair" to "Used · fair",
        "used_beat" to "Beat",
    )
    val boxes = listOf(
        "original_good" to "Original",
        "original_damaged" to "Damaged",
        "replacement" to "Not original",
        "no_box" to "No box",
    )

    /** Box tag shown next to the condition chip; none for an original box in good shape. */
    fun boxTag(box: String): String? = when (box) {
        "original_damaged" -> "Damaged box"
        "replacement" -> "Not original box"
        "no_box" -> "No box"
        else -> null
    }

    /** "US M 10", "US 10" and "10" are the same size; women's sizes keep their W. */
    fun sizeKey(size: String): String =
        size.uppercase().replace(Regex("\\s+"), "").removePrefix("US").replace(Regex("^M(?=\\d)"), "")

    const val NOTE_MAX = 140
}
