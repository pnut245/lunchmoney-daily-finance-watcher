"""Render a local budget JSON snapshot into a simple lockscreen PNG."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1290
HEIGHT = 2796
PADDING_X = 88
PADDING_Y = 120
CARD_WIDTH = WIDTH - (PADDING_X * 2)
LINE_SPACING = 14
BACKGROUND_TOP = "#081018"
BACKGROUND_BOTTOM = "#0B1721"
CARD_FILL = (11, 19, 28, 235)
CARD_OUTLINE = "#355267"
TEXT_PRIMARY = "#F4F7FB"
TEXT_SECONDARY = "#B3C4D3"
TEXT_MUTED = "#7F97AA"
ACCENT = "#76E0C5"


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 2:
        print("Usage: python -m src.lockscreen INPUT_JSON OUTPUT_PNG", file=sys.stderr)
        return 2

    input_path = Path(args[0]).expanduser().resolve()
    output_path = Path(args[1]).expanduser().resolve()

    if not input_path.exists():
        print(f"Missing input JSON: {input_path}", file=sys.stderr)
        return 1

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    image = render_lockscreen(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    print(f"Rendered lockscreen to {output_path}")
    return 0


def render_lockscreen(payload: dict[str, Any]) -> Image.Image:
    v1_snapshot = _coerce_v1_snapshot(payload)
    if v1_snapshot:
        image = Image.new("RGBA", (WIDTH, HEIGHT), v1_snapshot["background"])
        draw = ImageDraw.Draw(image, "RGBA")
        _render_v1_lockscreen(draw, v1_snapshot)
        return image

    adhd_snapshot = _coerce_adhd_snapshot(payload)
    if adhd_snapshot:
        image = _build_background(adhd_snapshot["theme"])
        draw = ImageDraw.Draw(image, "RGBA")
        _render_adhd_lockscreen(draw, adhd_snapshot)
        return image

    image = _build_background(_default_theme())
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_card(draw)

    title_font = _load_font(58, bold=True)
    subtitle_font = _load_font(28)
    section_font = _load_font(26, bold=True)
    body_font = _load_font(24)
    metric_font = _load_font(34, bold=True)
    metric_label_font = _load_font(22)
    cursor_x = PADDING_X + 44
    cursor_y = PADDING_Y + 46
    content_width = CARD_WIDTH - 88

    title = str(payload.get("title") or "Budget Snapshot")
    summary = str(payload.get("summary") or "Local budget state")

    draw.text((cursor_x, cursor_y), title, font=title_font, fill=TEXT_PRIMARY)
    cursor_y += _line_height(title_font) + 12
    cursor_y = _draw_wrapped_text(draw, summary, cursor_x, cursor_y, content_width, subtitle_font, TEXT_SECONDARY)
    cursor_y += 26

    metrics = _coerce_metrics(payload.get("metrics"))
    if metrics:
        cursor_y = _draw_metrics(draw, metrics, cursor_x, cursor_y, content_width, metric_font, metric_label_font)
        cursor_y += 24

    notes = _coerce_notes(payload.get("notes"))
    if notes:
        draw.text((cursor_x, cursor_y), "Focus", font=section_font, fill=ACCENT)
        cursor_y += _line_height(section_font) + 10
        for note in notes[:6]:
            cursor_y = _draw_bullet(draw, note, cursor_x, cursor_y, content_width, body_font, TEXT_PRIMARY)
            cursor_y += 6

    fallback_lines = _fallback_lines(payload)
    if not metrics and not notes and fallback_lines:
        draw.text((cursor_x, cursor_y), "State", font=section_font, fill=ACCENT)
        cursor_y += _line_height(section_font) + 10
        for line in fallback_lines[:10]:
            cursor_y = _draw_wrapped_text(draw, line, cursor_x, cursor_y, content_width, body_font, TEXT_PRIMARY)
            cursor_y += 8
    return image


def _render_v1_lockscreen(draw: ImageDraw.ImageDraw, snapshot: dict[str, Any]) -> None:
    center_x = WIDTH / 2
    label_font = _load_font(40, bold=True, family="apple_ui")
    number_font = _load_font(720, bold=True, family="apple_display")

    _draw_tracked_text_centered(
        draw,
        center_x,
        176,
        "SAFE TO SPEND",
        label_font,
        snapshot["muted_text"],
        tracking=9,
    )

    text = snapshot["display_number"]
    bbox = draw.textbbox((0, 0), text, font=number_font, anchor="lt")
    text_width = bbox[2] - bbox[0]
    max_width = WIDTH - 96
    while text_width > max_width and getattr(number_font, "size", 0) > 360:
        number_font = _load_font(number_font.size - 24, bold=True, family="apple_display")
        bbox = draw.textbbox((0, 0), text, font=number_font, anchor="lt")
        text_width = bbox[2] - bbox[0]

    draw.text(
        (center_x, HEIGHT * 0.52),
        text,
        font=number_font,
        fill=snapshot["text"],
        anchor="mm",
    )


def _render_adhd_lockscreen(draw: ImageDraw.ImageDraw, snapshot: dict[str, str]) -> None:
    theme = snapshot["theme"]
    center_x = WIDTH / 2
    eyebrow_font = _load_font(38, family="apple_ui")
    object_font = _load_font(76, bold=True, family="brand")
    safe_font = _load_font(320, bold=True, family="apple_display")
    state_font = _load_font(86, bold=True, family="display")
    secondary_label_font = _load_font(34, family="apple_ui")
    secondary_value_font = _load_font(102, bold=True, family="apple_display")

    _draw_tracked_text_centered(draw, center_x, 160, "SAFE TO SPEND", eyebrow_font, theme["muted_text"], tracking=8)
    _draw_centered_pill(draw, center_x, 285, snapshot["money_object"], object_font, theme)

    draw.text((center_x, 980), snapshot["safe_to_spend"], font=safe_font, fill=theme["headline_text"], anchor="ma")
    _draw_tracked_text_centered(draw, center_x, 1300, snapshot["spending_state"], state_font, theme["text"], tracking=5)

    week_center_x = WIDTH * 0.29
    dopamine_center_x = WIDTH * 0.71
    _draw_tracked_text_centered(draw, week_center_x, 2230, "WEEK", secondary_label_font, theme["muted_text"], tracking=4)
    draw.text((week_center_x, 2310), snapshot["week"], font=secondary_value_font, fill=theme["text"], anchor="ma")
    _draw_tracked_text_centered(draw, dopamine_center_x, 2230, "DOPAMINE", secondary_label_font, theme["muted_text"], tracking=3)
    draw.text((dopamine_center_x, 2310), snapshot["dopamine"], font=secondary_value_font, fill=theme["text"], anchor="ma")


def _draw_centered_pill(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.ImageFont,
    theme: dict[str, Any],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    pad_x = 38
    pad_y = 20
    left = center_x - (text_width / 2) - pad_x
    right = center_x + (text_width / 2) + pad_x
    top = y - pad_y
    bottom = y + text_height + pad_y
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=40,
        fill=theme["pill_fill"],
        outline=theme["pill_outline"],
        width=3,
    )
    draw.text((center_x, y), text, font=font, fill=theme["headline_text"], anchor="ma")


def _build_background(theme: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT))
    top = _hex_to_rgb(theme["background_top"])
    bottom = _hex_to_rgb(theme["background_bottom"])
    pixels = image.load()
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        for x in range(WIDTH):
            pixels[x, y] = (*row, 255)
    return image


def _draw_card(draw: ImageDraw.ImageDraw) -> None:
    left = PADDING_X
    top = PADDING_Y
    right = left + CARD_WIDTH
    bottom = HEIGHT - PADDING_Y
    draw.rounded_rectangle((left, top, right, bottom), radius=36, fill=CARD_FILL, outline=CARD_OUTLINE, width=2)


def _draw_metrics(
    draw: ImageDraw.ImageDraw,
    metrics: list[dict[str, str]],
    x: int,
    y: int,
    width: int,
    value_font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
) -> int:
    cols = 3
    gap = 20
    card_w = (width - gap * (cols - 1)) // cols
    card_h = 120
    text_y_max = y
    for index, metric in enumerate(metrics[:6]):
        row = index // cols
        col = index % cols
        left = x + col * (card_w + gap)
        top = y + row * (card_h + 18)
        right = left + card_w
        bottom = top + card_h
        draw.rounded_rectangle((left, top, right, bottom), radius=24, fill=(19, 38, 54, 190), outline=(87, 132, 160, 180), width=1)
        draw.text((left + 18, top + 20), metric["label"], font=label_font, fill=TEXT_MUTED)
        draw.text((left + 18, top + 58), metric["value"], font=value_font, fill=TEXT_PRIMARY)
        text_y_max = max(text_y_max, bottom)
    return text_y_max


def _draw_bullet(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    width: int,
    font: ImageFont.ImageFont,
    fill: str,
) -> int:
    bullet = "•"
    draw.text((x, y), bullet, font=font, fill=ACCENT)
    return _draw_wrapped_text(draw, text, x + 26, y, width - 26, font, fill)


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    width: int,
    font: ImageFont.ImageFont,
    fill: str,
) -> int:
    current_y = y
    for raw_line in text.splitlines() or [""]:
        for line in _wrap_text(draw, raw_line, width, font):
            draw.text((x, current_y), line, font=font, fill=fill)
            current_y += _line_height(font) + LINE_SPACING
    return current_y


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, width: int, font: ImageFont.ImageFont) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _line_height(font: ImageFont.ImageFont) -> int:
    bbox = font.getbbox("Ag")
    return bbox[3] - bbox[1]


def _draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    *,
    tracking: int,
) -> None:
    x, y = position
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + tracking


def _draw_tracked_text_centered(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    *,
    tracking: int,
) -> None:
    total_width = 0.0
    for index, char in enumerate(text):
        total_width += draw.textlength(char, font=font)
        if index < len(text) - 1:
            total_width += tracking
    _draw_tracked_text(draw, (center_x - total_width / 2, y), text, font, fill, tracking=tracking)


def _load_font(size: int, *, bold: bool = False, family: str = "default") -> ImageFont.ImageFont:
    candidates: list[str]
    if family == "flaunt":
        candidates = [
            "/System/Library/Fonts/Supplemental/Didot.ttc",
            "/System/Library/Fonts/Supplemental/Baskerville.ttc",
            "/System/Library/Fonts/Supplemental/Seravek.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif family == "apple_display":
        candidates = [
            "/System/Library/Fonts/Supplemental/SF Pro Display Bold.otf" if bold else "/System/Library/Fonts/Supplemental/SF Pro Display Regular.otf",
            "/System/Library/Fonts/Supplemental/Seravek.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif family == "apple_ui":
        candidates = [
            "/System/Library/Fonts/Supplemental/SF Pro Display Regular.otf",
            "/System/Library/Fonts/Supplemental/Seravek.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif family == "display":
        candidates = [
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif family == "brand":
        candidates = [
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/System/Library/Fonts/Supplemental/GillSans.ttc",
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial Narrow.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif family == "black":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif family == "narrow":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial Narrow.ttf",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/Supplemental/SF Pro Display Bold.otf" if bold else "/System/Library/Fonts/Supplemental/SF Pro Display Regular.otf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _coerce_metrics(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    metrics: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            label = str(item.get("label") or "").strip()
            metric_value = str(item.get("value") or "").strip()
            if label and metric_value:
                metrics.append({"label": label, "value": metric_value})
    return metrics


def _coerce_notes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_adhd_snapshot(payload: dict[str, Any]) -> dict[str, str] | None:
    metrics = _coerce_metrics(payload.get("metrics"))
    metric_lookup = {item["label"].strip().lower(): item["value"] for item in metrics}

    state = _first_non_empty(
        payload.get("spending_state"),
        payload.get("state"),
        payload.get("safe_to_spend_state"),
        payload.get("vault_state"),
    )
    today = _first_non_empty(
        payload.get("today"),
        payload.get("today_balance"),
        payload.get("daily_safe_to_spend"),
        metric_lookup.get("today"),
    )
    week = _first_non_empty(
        payload.get("week"),
        payload.get("this_week"),
        payload.get("week_balance"),
        payload.get("weekly_safe_to_spend"),
        metric_lookup.get("week"),
        metric_lookup.get("this week"),
    )
    dopamine = _first_non_empty(
        payload.get("dopamine"),
        payload.get("dopamine_balance"),
        metric_lookup.get("dopamine"),
    )
    safe_to_spend = _first_non_empty(
        payload.get("safe_to_spend"),
        payload.get("today"),
        payload.get("today_balance"),
        payload.get("daily_safe_to_spend"),
        metric_lookup.get("today"),
    )
    money_object = _first_non_empty(
        payload.get("money_object"),
        payload.get("object"),
        payload.get("safe_to_spend_object"),
    )

    if not all([state, safe_to_spend, week, dopamine]):
        return None

    return {
        "spending_state": state.upper(),
        "safe_to_spend": safe_to_spend,
        "today": today or safe_to_spend,
        "week": week,
        "dopamine": dopamine,
        "money_object": money_object or _object_for_money_text(safe_to_spend),
        "theme": _theme_for_state(state),
    }


def _coerce_v1_snapshot(payload: dict[str, Any]) -> dict[str, Any] | None:
    remaining = _first_number(
        payload.get("remaining_today"),
        payload.get("meta", {}).get("remaining_today") if isinstance(payload.get("meta"), dict) else None,
    )
    if remaining is None:
        return None

    is_negative = bool(payload.get("is_negative", remaining < 0))
    return {
        "display_number": _format_v1_number(remaining),
        "background": "#D71920" if is_negative else "#FFFFFF",
        "text": "#FFFFFF" if is_negative else "#000000",
        "muted_text": (255, 255, 255, 165) if is_negative else (0, 0, 0, 120),
    }


def _first_number(*values: Any) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            continue
    return None


def _format_v1_number(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 0.005:
        return f"{rounded:,.0f}"
    return f"{value:,.2f}"


def _fallback_lines(payload: dict[str, Any]) -> list[str]:
    ignore = {"title", "summary", "updated_at", "metrics", "notes"}
    lines: list[str] = []
    for key, value in payload.items():
        if key in ignore:
            continue
        pretty_value = json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
        lines.append(f"{key}: {pretty_value}")
    return lines


def _format_timestamp(value: Any) -> str:
    if value is None or value == "":
        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    text = str(value)
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _wrap_centered_state(text: str) -> str:
    if len(text) <= 14:
        return text
    parts = text.split()
    if len(parts) <= 2:
        return text
    midpoint = len(parts) // 2
    return " ".join(parts[:midpoint]) + "\n" + " ".join(parts[midpoint:])


def _default_theme() -> dict[str, Any]:
    return {
        "background_top": "#F4EDE4",
        "background_bottom": "#F4EDE4",
        "headline_text": "#111111",
        "text": "#111111",
        "muted_text": "#545454",
        "pill_fill": "#FFFFFFCC",
        "pill_outline": "#11111122",
    }


def _theme_for_state(state: str) -> dict[str, Any]:
    normalized = state.strip().upper()
    if "OVERDRAWN" in normalized:
        return {
            "background_top": "#B91C1C",
            "background_bottom": "#7F1D1D",
            "headline_text": "#FFF7F5",
            "text": "#FFF7F5",
            "muted_text": "#FFD9D2",
            "pill_fill": "#00000022",
            "pill_outline": "#FFFFFF33",
        }
    if "DANGER" in normalized or "STOP" in normalized or "PAUSE" in normalized:
        return {
            "background_top": "#F0B6A8",
            "background_bottom": "#E37D68",
            "headline_text": "#2A120D",
            "text": "#2A120D",
            "muted_text": "#5B2920",
            "pill_fill": "#FFFFFF88",
            "pill_outline": "#2A120D22",
        }
    if "TIGHT" in normalized:
        return {
            "background_top": "#E7B85A",
            "background_bottom": "#D7923D",
            "headline_text": "#24150A",
            "text": "#24150A",
            "muted_text": "#5D3A18",
            "pill_fill": "#FFFFFF88",
            "pill_outline": "#24150A22",
        }
    if "WATCH" in normalized or "CAUTION" in normalized or "CAREFUL" in normalized:
        return {
            "background_top": "#F2D481",
            "background_bottom": "#E8BF59",
            "headline_text": "#241B08",
            "text": "#241B08",
            "muted_text": "#5C4813",
            "pill_fill": "#FFF8E199",
            "pill_outline": "#241B0822",
        }
    if "COMFORTABLE" in normalized:
        return {
            "background_top": "#D7E8B4",
            "background_bottom": "#BDD986",
            "headline_text": "#16210B",
            "text": "#16210B",
            "muted_text": "#445726",
            "pill_fill": "#F7FFE099",
            "pill_outline": "#16210B22",
        }
    return {
        "background_top": "#B9E6D1",
        "background_bottom": "#89D6B4",
        "headline_text": "#0F1E17",
        "text": "#0F1E17",
        "muted_text": "#355145",
        "pill_fill": "#F3FFF799",
        "pill_outline": "#0F1E1722",
    }


def _object_for_money_text(text: str) -> str:
    value = _money_text_to_float(text)
    if value is None:
        return "Coffee"
    if value <= 0:
        return "No Spend"
    if value < 8:
        return "Coffee"
    if value < 18:
        return "Lunch"
    if value < 35:
        return "Groceries"
    if value < 60:
        return "Dinner"
    if value < 120:
        return "Errands"
    if value < 250:
        return "Day Out"
    return "Big Spend"


def _money_text_to_float(text: str) -> float | None:
    cleaned = text.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    raise SystemExit(main())
