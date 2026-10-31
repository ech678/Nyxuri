"""Pure geometry helpers kept independent from GTK for cheap tests."""

from typing import NamedTuple


class PanelPlacement(NamedTuple):
    """Panel position relative to the invocation pointer.

    ``y`` is the edge nearest to the pointer: the top edge when the panel
    opens below it, the bottom edge when it opens above. ``max_height`` is the
    room on that side, so the panel grows away from the pointer without
    covering the selection or leaving the surface.
    """

    x: int
    y: int
    above: bool
    max_height: int


def place_panel(
    pointer_x: int,
    pointer_y: int,
    surface_width: int,
    surface_height: int,
    panel_width: int,
    comfortable_height: int,
    gap: int = 16,
    edge_margin: int = 12,
    lead: int = 20,
) -> PanelPlacement:
    """Open a panel just below the last selection pointer, like a context popup.

    The left edge starts ``lead`` pixels before the pointer so the cursor sits
    over the panel's leading corner, clamped to an edge inset. The panel opens
    below the pointer unless less than ``comfortable_height`` fits there and
    more room exists above; then its bottom edge is anchored above the pointer.
    """
    x = _clamp_axis(pointer_x - lead, panel_width, surface_width, edge_margin)
    below_room = surface_height - edge_margin - (pointer_y + gap)
    above_room = pointer_y - gap - edge_margin
    if below_room >= comfortable_height or below_room >= above_room:
        return PanelPlacement(x, max(0, pointer_y + gap), False, max(0, below_room))
    return PanelPlacement(x, max(0, pointer_y - gap), True, max(0, above_room))


def center_panel(
    surface_width: int,
    surface_height: int,
    panel_width: int,
    panel_height: int,
    edge_margin: int = 12,
) -> PanelPlacement:
    """Fallback placement when no pointer position was ever observed."""
    x, y = clamp_panel(
        (surface_width - panel_width) // 2,
        surface_height // 4,
        panel_width,
        panel_height,
        surface_width,
        surface_height,
        edge_margin,
    )
    return PanelPlacement(x, y, False, max(0, surface_height - edge_margin - y))


def clamp_panel(
    x: int,
    y: int,
    panel_width: int,
    panel_height: int,
    surface_width: int,
    surface_height: int,
    edge_margin: int,
) -> tuple[int, int]:
    return (
        _clamp_axis(x, panel_width, surface_width, edge_margin),
        _clamp_axis(y, panel_height, surface_height, edge_margin),
    )


def _clamp_axis(value: int, size: int, extent: int, edge_margin: int) -> int:
    maximum = max(0, extent - size - edge_margin)
    return max(min(edge_margin, maximum), min(value, maximum))
