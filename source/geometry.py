"""A rounded-square with superellipse corners, exponent > 2.

The analytic curve has zero curvature at its joins with the straight edges.
Rendering uses dense adaptive-angle samples, rather than pretending a circular
border-radius is an exact Apple contour. No Apple proprietary path is used.
"""
import math

CARD = 200
CARD_SIZES = (180, 200, 220, 240)
DESIGN_CARD = 240
DESIGN_RADIUS = 34
MARGIN = 28
BOTTOM = 40
RADIUS = DESIGN_RADIUS * CARD / DESIGN_CARD
EXPONENT = 2.6
# Keep the native compositor surface safely inside the antialiased outline.
# Some Windows builds composite a system backdrop by its rectangular bounds
# even when a custom window region is present.
BUBBLE = 72


def contour(size=CARD, radius=RADIUS, inset=.5, steps=72):
    lo, hi = inset, size - inset
    r = radius - inset
    centers = [(hi-r, lo+r), (hi-r, hi-r), (lo+r, hi-r), (lo+r, lo+r)]
    pts = []
    for corner, (cx, cy) in enumerate(centers):
        start = -math.pi / 2 + corner * math.pi / 2
        for i in range(steps + 1):
            angle = start + math.pi / 2 * i / steps
            c, s = math.cos(angle), math.sin(angle)
            pts.append((cx + r * math.copysign(abs(c) ** (2 / EXPONENT), c),
                        cy + r * math.copysign(abs(s) ** (2 / EXPONENT), s)))
    return pts


def svg_path(size=CARD, radius=RADIUS):
    pts = contour(size=size, radius=radius)
    return "M " + " L ".join(f"{x:.4f} {y:.4f}" for x, y in pts) + " Z"


def inside_card(x, y, inset=0, size=CARD, radius=RADIUS):
    if not inset <= x <= size-inset or not inset <= y <= size-inset:
        return False
    dx, dy = max(radius-x, x-(size-radius), 0), max(radius-y, y-(size-radius), 0)
    return (dx / radius) ** EXPONENT + (dy / radius) ** EXPONENT <= 1


def settle_offset(vx, vy):
    """A restrained 160 ms easing tail, bounded to 10 logical pixels."""
    x, y = vx * .020, vy * .020
    length = math.hypot(x, y)
    if length > 10:
        x, y = x * 10 / length, y * 10 / length
    return round(x), round(y)
