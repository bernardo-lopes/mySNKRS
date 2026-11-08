package app.mysnkrs.ui

import java.text.NumberFormat
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs

/** "$1,188.96", "$70", "−$12" or "–" for no value, like the web app. */
fun usd(v: Double?): String {
    if (v == null) return "–"
    val f = NumberFormat.getNumberInstance(Locale.US).apply {
        minimumFractionDigits = if (v % 1.0 != 0.0) 2 else 0
        maximumFractionDigits = 2
    }
    return (if (v < 0) "−" else "") + "$" + f.format(abs(v))
}

/**
 * Sale dates ("2026-11-01T16:13") are local times as StockX showed them; sync times
 * ("2026-11-08 03:25:29") are UTC from SQLite.
 */
fun parseLocal(s: String?): LocalDateTime? {
    if (s.isNullOrBlank()) return null
    val t = s.trim().replace(' ', 'T')
    return runCatching { OffsetDateTime.parse(t).atZoneSameInstant(ZoneId.systemDefault()).toLocalDateTime() }.getOrNull()
        ?: runCatching { Instant.parse(t).atZone(ZoneId.systemDefault()).toLocalDateTime() }.getOrNull()
        ?: runCatching { LocalDateTime.parse(t) }.getOrNull()
        ?: runCatching { LocalDate.parse(t.take(10)).atStartOfDay() }.getOrNull()
}

fun parseUtc(s: String?): LocalDateTime? {
    if (s.isNullOrBlank()) return null
    val t = s.trim().replace(' ', 'T')
    return runCatching { LocalDateTime.parse(t).atOffset(ZoneOffset.UTC).atZoneSameInstant(ZoneId.systemDefault()).toLocalDateTime() }
        .getOrNull() ?: parseLocal(s)
}

private val shortDate = DateTimeFormatter.ofPattern("MMM d", Locale.US)
private val longDate = DateTimeFormatter.ofPattern("MMM d, yyyy", Locale.US)
private val timeFmt = DateTimeFormatter.ofPattern("hh:mm a", Locale.US)

fun fmtShort(d: LocalDateTime?): String = d?.format(shortDate) ?: ""
fun fmtLong(d: LocalDateTime?): String = d?.format(longDate) ?: ""
fun fmtTime(d: LocalDateTime?): String = d?.format(timeFmt) ?: ""

fun epochMillis(d: LocalDateTime): Long = d.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
