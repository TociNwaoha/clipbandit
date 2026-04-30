from app.models.export import CaptionStyle
from app.services.rendering import _ass_style_line, _caption_layout


def test_caption_style_enum_includes_new_values():
    values = {item.value for item in CaptionStyle}
    assert "kinetic_bold" in values
    assert "cinema_outline" in values
    assert "clean_highlight" in values


def test_ass_style_line_supported_for_all_caption_styles():
    layout = _caption_layout("9:16", "clean_minimal", 1080, 1920, None, None)
    lines = {style.value: _ass_style_line(style.value, layout) for style in CaptionStyle}

    for value, line in lines.items():
        assert line.startswith("Style: Default,Arial,")
        assert "100,100,0,0" in line
        assert len(line) > 40, f"style line too short for {value}"

    # Ensure new styles are not silently falling back to identical clean_minimal settings.
    assert lines["kinetic_bold"] != lines["clean_minimal"]
    assert lines["cinema_outline"] != lines["clean_minimal"]
    assert lines["clean_highlight"] != lines["clean_minimal"]


def test_caption_layout_varies_for_new_styles():
    kinetic = _caption_layout("9:16", "kinetic_bold", 1080, 1920, None, None)
    clean = _caption_layout("9:16", "clean_minimal", 1080, 1920, None, None)
    cinema = _caption_layout("9:16", "cinema_outline", 1080, 1920, None, None)

    assert kinetic.font_size > clean.font_size
    assert cinema.font_size > clean.font_size
