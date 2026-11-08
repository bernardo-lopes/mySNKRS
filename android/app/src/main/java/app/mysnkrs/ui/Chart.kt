package app.mysnkrs.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.mysnkrs.data.Sale
import app.mysnkrs.ui.theme.Snkrs
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.max
import kotlin.math.roundToInt

val RangeDays = mapOf("1m" to 30, "3m" to 91, "6m" to 182, "3y" to 1095)

/** Step chart of sale prices over the selected period, same as the web's SVG chart. */
@Composable
fun SalesChart(points: List<Sale>, range: String, modifier: Modifier = Modifier) {
    val c = Snkrs.colors
    if (points.isEmpty()) {
        Box(modifier.fillMaxWidth().height(110.dp), contentAlignment = Alignment.Center) {
            Text("No sales in this period", color = c.gray500, fontSize = 13.sp)
        }
        return
    }
    val measurer = rememberTextMeasurer()
    val labelStyle = TextStyle(color = c.gray500, fontSize = 10.sp)
    val days = RangeDays[range] ?: 182
    val end = System.currentTimeMillis()
    val start = end - days * 86_400_000L
    val pts = points.mapNotNull { s -> parseLocal(s.date)?.let { epochMillis(it) to s.price } }.sortedBy { it.first }
    val prices = pts.map { it.second }
    var lo = prices.minOrNull() ?: 0.0
    var hi = prices.maxOrNull() ?: 0.0
    val pad = max(5.0, (hi - lo) * 0.15)
    lo = max(0.0, lo - pad); hi += pad
    val fmt = DateTimeFormatter.ofPattern(if (range == "3y") "MMM yy" else "MMM d", Locale.US)

    Canvas(modifier.fillMaxWidth().height(200.dp)) {
        if (pts.isEmpty()) return@Canvas
        val l = 40.dp.toPx(); val r = 6.dp.toPx(); val t = 8.dp.toPx(); val b = 22.dp.toPx()
        val w = size.width; val h = size.height
        fun x(ms: Long) = l + (ms - start).toFloat() / (end - start) * (w - l - r)
        fun y(v: Double) = t + (1 - ((v - lo) / (hi - lo)).toFloat()) * (h - t - b)

        for (i in 0..3) {
            val v = lo + (hi - lo) * i / 3
            drawLine(c.ink700, Offset(l, y(v)), Offset(w - r, y(v)), strokeWidth = 1.dp.toPx())
            val label = measurer.measure("$${v.roundToInt()}", labelStyle)
            drawText(label, topLeft = Offset(l - 6.dp.toPx() - label.size.width, y(v) - label.size.height / 2))
        }
        for (i in 0..4) {
            val ms = start + (end - start) * i / 4
            val label = measurer.measure(Instant.ofEpochMilli(ms).atZone(ZoneId.systemDefault()).format(fmt), labelStyle)
            val lx = when (i) { 0 -> x(ms); 4 -> x(ms) - label.size.width; else -> x(ms) - label.size.width / 2 }
            drawText(label, topLeft = Offset(lx, h - label.size.height))
        }

        val line = Path().apply {
            moveTo(x(pts[0].first), y(pts[0].second))
            for (i in 1 until pts.size) {
                lineTo(x(pts[i].first), y(pts[i - 1].second))
                lineTo(x(pts[i].first), y(pts[i].second))
            }
            lineTo(x(end), y(pts.last().second))
        }
        val area = Path().apply {
            addPath(line)
            lineTo(x(end), h - b)
            lineTo(x(pts[0].first), h - b)
            close()
        }
        drawPath(area, c.up.copy(alpha = 0.18f))
        drawPath(line, c.gray200, style = Stroke(width = 2.dp.toPx()))
        pts.forEach { (ms, v) -> drawCircle(c.gray200, radius = 3.dp.toPx(), center = Offset(x(ms), y(v))) }
    }
}
