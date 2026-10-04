"""Approximate the 360px-wide phone canvas for visual QA (not a native screenshot)."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent

def render(folder, width=344):
    data = json.loads((folder / 'data.json').read_text())
    scale = width / data['dimensions']['w']
    height = round(data['dimensions']['h'] * scale)
    picture = Image.new('RGBA', (width, height), (230, 230, 240, 255))
    overlay = Image.open(folder / 'lines.png').convert('RGBA').resize((width, height), Image.Resampling.LANCZOS)
    picture.alpha_composite(overlay)
    draw = ImageDraw.Draw(picture)
    font = ImageFont.truetype('/usr/share/fonts/noto/NotoSans-Bold.ttf', 10)
    for number in data['numbers']:
        # Match GameCanvas.tsx's screen-space font and baseline offsets.
        draw.text((number['x'] * scale - 4, number['y'] * scale + 3),
                  str(number['number']), fill='#666666', font=font, anchor='ls')
    output = folder / 'phone-preview.png'
    picture.convert('RGB').save(output)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='+')
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    base = ROOT.parent / 'app_assets' if args.final else ROOT / 'paintability-candidates' / 'processed'
    for level_id in args.ids:
        print(render(base / level_id))
