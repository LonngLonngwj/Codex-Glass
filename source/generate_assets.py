"""Build-time only: bake soft shadows and tint SVG icons without GPU shaders.

Run with Pillow installed. The portable app does not depend on Pillow.
The same superellipse contour is used by the QML surface and hit testing.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from geometry import contour


def generate():
    root = Path(__file__).parent
    assets = root / 'assets'
    assets.mkdir(exist_ok=True)
    scale = 3
    for name, size, radius, offset, blur in (
            ('card-shadow', 240, 34, 12, 12),
            ('bubble-shadow', 72, 23, 8, 9)):
        canvas = ((size + 56)*scale, (size + 68)*scale)
        mask = Image.new('L', canvas)
        points = [((x+28)*scale, (y+28+offset)*scale)
                  for x, y in contour(size=size, radius=radius)]
        ImageDraw.Draw(mask).polygon(points, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(blur*scale))
        # Fade to exactly transparent at the canvas edge: no rectangular seam.
        edge = Image.new('L', canvas)
        edge_pixels = edge.load()
        for y in range(canvas[1]):
            for x in range(canvas[0]):
                edge_pixels[x, y] = round(255 * min(1, min(x, y, canvas[0]-1-x, canvas[1]-1-y)/(4*scale)))
        from PIL import ImageChops
        mask = ImageChops.multiply(mask, edge)
        shadow = Image.new('RGBA', canvas, (0, 0, 0, 0))
        shadow.putalpha(mask)
        shadow.save(assets / (name + '.png'), optimize=True)
    for name in ('refresh-cw', 'terminal'):
        original = (root/'icons'/(name+'.svg')).read_text(encoding='utf-8')
        for variant, color in (('muted', '#4e666b'), ('light', '#eff5f6')):
            (assets/f'{name}-{variant}.svg').write_text(
                original.replace('currentColor', color), encoding='utf-8')


if __name__ == '__main__':
    generate()
