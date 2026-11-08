package app.mysnkrs.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNamingStrategy
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class ApiException(message: String) : Exception(message)

/**
 * Client for the mySNKRS server running on your Mac. Every call goes to [baseUrl]; nothing here
 * talks to StockX or any marketplace directly.
 */
class Api(private val baseUrl: () -> String) {

    @OptIn(ExperimentalSerializationApi::class)
    private val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        namingStrategy = JsonNamingStrategy.SnakeCase
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        // Check value asks every marketplace, which can take a while
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private val jsonType = "application/json".toMediaType()

    fun url(path: String, query: Map<String, String> = emptyMap()): HttpUrl {
        val base = normalize(baseUrl()).toHttpUrlOrNull()
            ?: throw ApiException("Set your Mac's server address in Settings.")
        return base.newBuilder().apply {
            path.trimStart('/').split('/').forEach { addPathSegment(it) }
            query.forEach { (k, v) -> addQueryParameter(k, v) }
        }.build()
    }

    private suspend fun call(request: Request): String = withContext(Dispatchers.IO) {
        try {
            client.newCall(request).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) throw ApiException(errorDetail(body) ?: "Server error ${res.code}")
                body
            }
        } catch (e: IOException) {
            throw ApiException("Can't reach your mySNKRS server at ${baseUrl()}. Is it running and is Tailscale on? (${e.message})")
        }
    }

    private fun errorDetail(body: String): String? = runCatching {
        val detail = json.parseToJsonElement(body).jsonObject["detail"]
        (detail as? JsonPrimitive)?.content ?: detail?.toString()
    }.getOrNull()

    suspend fun ping() {
        call(Request.Builder().url(url("api/popular")).build())
    }

    suspend fun inventory(status: String, favoritesOnly: Boolean): InventoryResponse {
        val q = buildMap {
            put("status", status)
            if (favoritesOnly) put("favorites", "true")
        }
        return json.decodeFromString(call(Request.Builder().url(url("api/inventory", q)).build()))
    }

    suspend fun addPair(p: NewPair): Int {
        val body = buildJsonObject {
            put("sku", p.sku)
            put("size", p.size)
            p.modelName?.takeIf { it.isNotBlank() }?.let { put("model_name", it) }
            put("condition", p.condition)
            put("box_condition", p.boxCondition)
            put("purchase_price", p.purchasePrice?.let(::JsonPrimitive) ?: JsonNull)
            put("notes", p.notes)
        }
        val res = call(Request.Builder().url(url("api/inventory")).post(body.toString().toRequestBody(jsonType)).build())
        return json.parseToJsonElement(res).jsonObject["id"]?.jsonPrimitive?.content?.toIntOrNull() ?: 0
    }

    /** PATCH /api/inventory/{id}. A null value clears that field (e.g. the purchase price). */
    suspend fun updatePair(id: Int, fields: Map<String, Any?>) {
        val body = JsonObject(fields.mapValues { (_, v) -> toJson(v) })
        call(Request.Builder().url(url("api/inventory/$id")).patch(body.toString().toRequestBody(jsonType)).build())
    }

    suspend fun deletePair(id: Int) {
        call(Request.Builder().url(url("api/inventory/$id")).delete().build())
    }

    suspend fun evaluate(sku: String, size: String, condition: String, box: String): Evaluation {
        val form = FormBody.Builder()
            .add("sku", sku)
            .add("size", size)
            .add("condition", condition)
            .add("box_condition", box)
            .build()
        return json.decodeFromString(call(Request.Builder().url(url("api/evaluate")).post(form).build()))
    }

    suspend fun history(sku: String, size: String, range: String): SalesHistory =
        json.decodeFromString(
            call(Request.Builder().url(url("api/stockx/history", mapOf("sku" to sku, "size" to size, "range" to range))).build())
        )

    /** Download link for the Excel/PDF export, opened in the phone's browser. */
    fun exportUrl(fmt: String, status: String, favoritesOnly: Boolean): String =
        url("api/inventory/export.$fmt", buildMap {
            put("status", status)
            if (favoritesOnly) put("favorites", "true")
        }).toString()

    private fun toJson(v: Any?): JsonElement = when (v) {
        null -> JsonNull
        is String -> JsonPrimitive(v)
        is Number -> JsonPrimitive(v)
        is Boolean -> JsonPrimitive(v)
        else -> JsonPrimitive(v.toString())
    }

    companion object {
        /** "100.89.1.2:8000" → "http://100.89.1.2:8000/", keeps https:// addresses as they are. */
        fun normalize(raw: String): String {
            val s = raw.trim().trimEnd('/')
            if (s.isEmpty()) return ""
            val withScheme = if (s.startsWith("http://") || s.startsWith("https://")) s else "http://$s"
            return "$withScheme/"
        }
    }
}
