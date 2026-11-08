package app.mysnkrs.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.mysnkrs.data.Grades
import app.mysnkrs.ui.theme.Snkrs
import coil.compose.AsyncImage

val Tnum = TextStyle(fontFeatureSettings = "tnum")
val Mono = FontFamily.Monospace

fun openUrl(context: Context, url: String?) {
    if (url.isNullOrBlank()) return
    try {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    } catch (e: ActivityNotFoundException) {
        Toast.makeText(context, "No app can open this link", Toast.LENGTH_SHORT).show()
    }
}

/** Rounded panel like the web's bg-ink-800 border-ink-700 cards. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    padding: Dp = 16.dp,
    background: Color = Snkrs.colors.ink800,
    content: @Composable ColumnScope.() -> Unit,
) {
    val c = Snkrs.colors
    Column(
        modifier
            .clip(RoundedCornerShape(16.dp))
            .background(background)
            .border(1.dp, c.ink700, RoundedCornerShape(16.dp))
            .padding(padding),
        content = content,
    )
}

@Composable
fun Chip(text: String, fg: Color, bg: Color) {
    Text(
        text,
        color = fg,
        fontSize = 11.sp,
        maxLines = 1,
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 2.dp),
    )
}

/** DS (green), Not DS (amber) or Used (rose), plus a box tag when the box isn't original. */
@Composable
fun ConditionTags(condition: String, box: String, vertical: Boolean = false) {
    val c = Snkrs.colors
    val chips: @Composable () -> Unit = {
        when (condition) {
            "deadstock" -> Chip("DS", c.positive, Color(0xFF10B981).copy(alpha = 0.15f))
            "vnds" -> Chip("Not DS", c.warning, Color(0xFFF59E0B).copy(alpha = 0.15f))
            else -> Chip("Used", c.negative, Color(0xFFF43F5E).copy(alpha = 0.15f))
        }
        Grades.boxTag(box)?.let { Chip(it, c.gray300, c.ink700) }
    }
    if (vertical) Column(verticalArrangement = Arrangement.spacedBy(4.dp)) { chips() }
    else Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) { chips() }
}

/** Rounded toggle pill (range picker, In stock / Sold tabs, marketplace search options). */
@Composable
fun Pill(
    text: String,
    active: Boolean,
    onClick: () -> Unit,
    activeBg: Color = Snkrs.colors.fg,
    activeFg: Color = Snkrs.colors.fgInverse,
) {
    val c = Snkrs.colors
    Text(
        text,
        color = if (active) activeFg else c.gray300,
        fontSize = 13.sp,
        fontWeight = FontWeight.Medium,
        maxLines = 1,
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .background(if (active) activeBg else c.ink700)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 6.dp),
    )
}

@Composable
fun PrimaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    val c = Snkrs.colors
    Box(
        modifier
            .clip(RoundedCornerShape(10.dp))
            .background(if (enabled) c.fg else c.gray500)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 12.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = c.fgInverse, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
    }
}

@Composable
fun OutlineButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, filled: Boolean = false) {
    val c = Snkrs.colors
    Box(
        modifier
            .clip(RoundedCornerShape(8.dp))
            .background(if (filled) c.ink700 else Color.Transparent)
            .border(1.dp, if (filled) c.ink700 else c.ink600, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 7.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = c.gray200, fontSize = 12.sp, maxLines = 1)
    }
}

/** White square behind product shots, which StockX renders on white. */
@Composable
fun Thumb(url: String?, size: Dp) {
    val c = Snkrs.colors
    Box(
        Modifier
            .size(size)
            .clip(RoundedCornerShape(10.dp))
            .background(Color.White)
            .then(if (c.isLight) Modifier.border(1.dp, c.ink600, RoundedCornerShape(10.dp)) else Modifier),
        contentAlignment = Alignment.Center,
    ) {
        if (url.isNullOrBlank()) Text("👟", fontSize = (size.value * 0.45f).sp)
        else AsyncImage(model = url, contentDescription = null, contentScale = ContentScale.Fit, modifier = Modifier.size(size))
    }
}

@Composable
fun StatCard(label: String, value: String, sub: String?, modifier: Modifier = Modifier, valueColor: Color? = null) {
    val c = Snkrs.colors
    Panel(modifier, padding = 14.dp) {
        Text(label, color = c.gray400, fontSize = 12.sp, maxLines = 2)
        Text(value, color = valueColor ?: c.fg, fontSize = 22.sp, fontWeight = FontWeight.Bold, style = Tnum, modifier = Modifier.padding(top = 2.dp))
        if (!sub.isNullOrBlank()) Text(sub, color = c.gray500, fontSize = 11.sp, modifier = Modifier.padding(top = 2.dp))
    }
}

@Composable
fun fieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Snkrs.colors.gray500,
    unfocusedBorderColor = Snkrs.colors.ink600,
    focusedContainerColor = Snkrs.colors.ink900,
    unfocusedContainerColor = Snkrs.colors.ink900,
    focusedTextColor = Snkrs.colors.fg,
    unfocusedTextColor = Snkrs.colors.fg,
    focusedLabelColor = Snkrs.colors.gray400,
    unfocusedLabelColor = Snkrs.colors.gray400,
    cursorColor = Snkrs.colors.fg,
)

@Composable
fun Field(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    mono: Boolean = false,
    uppercase: Boolean = false,
    number: Boolean = false,
    maxLength: Int? = null,
    focusRequester: FocusRequester? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = { v ->
            var s = v.replace('\n', ' ')
            if (uppercase) s = s.uppercase()
            if (maxLength != null) s = s.take(maxLength)
            onChange(s)
        },
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it, color = Snkrs.colors.gray500) } },
        singleLine = true,
        textStyle = TextStyle(fontFamily = if (mono) Mono else null, fontSize = 14.sp),
        keyboardOptions = KeyboardOptions(
            capitalization = if (uppercase) KeyboardCapitalization.Characters else KeyboardCapitalization.Sentences,
            keyboardType = if (number) KeyboardType.Decimal else KeyboardType.Text,
        ),
        colors = fieldColors(),
        shape = RoundedCornerShape(10.dp),
        modifier = modifier.then(if (focusRequester != null) Modifier.focusRequester(focusRequester) else Modifier),
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Picker(label: String, options: List<Pair<String, String>>, value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier) {
    var open by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = open, onExpandedChange = { open = it }, modifier = modifier) {
        OutlinedTextField(
            value = options.firstOrNull { it.first == value }?.second ?: value,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            singleLine = true,
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = open) },
            textStyle = TextStyle(fontSize = 14.sp),
            colors = fieldColors(),
            shape = RoundedCornerShape(10.dp),
            modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable).fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            options.forEach { (v, text) ->
                DropdownMenuItem(text = { Text(text) }, onClick = { onChange(v); open = false })
            }
        }
    }
}

/** One-line note editor (max 140 characters, line breaks become spaces), like the web's inline note. */
@Composable
fun NoteDialog(initial: String, title: String, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var text by remember { mutableStateOf(initial) }
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Note", fontSize = 18.sp) },
        text = {
            Column {
                Text(title, color = Snkrs.colors.gray400, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(8.dp))
                Field(text, { text = it }, "One-line note", maxLength = Grades.NOTE_MAX, focusRequester = focus, modifier = Modifier.fillMaxWidth())
                Text("${text.length}/${Grades.NOTE_MAX}", color = Snkrs.colors.gray500, fontSize = 11.sp, modifier = Modifier.padding(top = 4.dp))
            }
        },
        confirmButton = { TextButton(onClick = { onSave(text.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")) }) { Text("Save") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        containerColor = Snkrs.colors.ink800,
    )
}

/** Small dialog with one or two text fields (purchase price, sold price + platform). */
@Composable
fun PromptDialog(
    title: String,
    message: String?,
    fields: List<Triple<String, String, Boolean>>, // label, initial value, numeric
    confirm: String,
    onDismiss: () -> Unit,
    onConfirm: (List<String>) -> Unit,
) {
    val values = remember { fields.map { mutableStateOf(it.second) } }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title, fontSize = 18.sp) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (message != null) Text(message, color = Snkrs.colors.gray400, fontSize = 13.sp)
                fields.forEachIndexed { i, (label, _, numeric) ->
                    Field(values[i].value, { values[i].value = it }, label, number = numeric, modifier = Modifier.fillMaxWidth())
                }
            }
        },
        confirmButton = { TextButton(onClick = { onConfirm(values.map { it.value.trim() }) }) { Text(confirm) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        containerColor = Snkrs.colors.ink800,
    )
}

@Composable
fun ErrorBanner(message: String, onRetry: (() -> Unit)? = null) {
    val c = Snkrs.colors
    Panel(Modifier.fillMaxWidth(), background = c.ink800) {
        Text(message, color = c.negative, fontSize = 13.sp)
        if (onRetry != null) {
            Spacer(Modifier.height(8.dp))
            OutlineButton("Try again", onRetry)
        }
    }
}

val ScreenPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp)
