"""Measured quality checks for source art, playable level bundles and reward videos.

Every check measures the files a child will actually receive and returns a
report: {'verdict': 'PASS'|'FAIL', 'failures': [...], 'warnings': [...],
'metrics': {...}}. Nothing here approves how a picture *looks*; that is the
separate visual review gate in factory.py. These checks exist so a picture
that would play badly can never reach the app, whoever reviewed it.

The limits in LIMITS were calibrated against the 58 shipped levels (see
`factory.py audit`), then tightened where shipped levels had known faults.
"""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

cv2.setNumThreads(2)

BACKGROUND_ID = 255
LINE_ID = 254
SIZE = 1024
# GameCanvas.tsx draws the picture (screen width - 16) wide. 360dp is the
# narrowest phone we support, so legibility is judged at 344 screen pixels.
PHONE_CANVAS = 344
SCREEN = PHONE_CANVAS / SIZE
# GameCanvas.tsx: 10px bold digits drawn with the baseline at (x - 4, y + 3).
GLYPH_ADVANCE = 5.8
GLYPH_HEIGHT = 7.3
GLYPH_LEFT = -4.0
GLYPH_BASELINE = 3.0
# process.py groups same-colour regions closer than this under one number.
NEIGHBOR_GAP = 20
# finish.py's smallest number (font px), for areas too small to hold a digit.
SMALLEST_LABEL = 4
# GameCanvas.tsx tint for unpainted pixels.
UNPAINTED_RGB = (230, 230, 240)

LIMITS = {
    'image': {
        'border_white_min': 244,        # mean of the outer 12px ring, 0-255
        'border_dark_max_fraction': 0.002,
        'margin_min_px': 24,            # subject bounding box to image edge
        'subject_min_fraction': 0.22,   # of the canvas bounding-box area
        'subject_max_fraction': 0.92,
        'ink_min_fraction': 0.015,      # black outline pixels; the fine-line style measures 0.018
        'colorful_min_fraction': 0.12,  # saturated pixels
        'frame_max_coverage': 0.6,      # share of the subject's bounding box edge that is ink
        'outlined_min_fraction': 0.5,   # of the silhouette with ink beside it; shipped pictures 0.63 or more
        'pieces_max': 8,                # separate drawn pieces; shipped pictures have at most 6
        'piece_min_fraction': 0.002,    # of the canvas, so droplets and sparkles do not count
    },
    'level': {
        'lost_part_min_px': 1500,       # a part of the art (white sail, cream tummy) that the map calls background
        'palette_min': 5,
        'palette_max': 12,
        'labels_min': 8,
        'labels_max': 50,
        'meaningful_colors_min': 5,
        'palette_delta_e_min': 11.0,    # two numbers must not look the same
        'color_share_min': 0.0003,      # each number paints a real area (small details are painted, not printed)
        'label_clearance_min_screen_px': 3.0,
        'label_inside_min_fraction': 0.6,
        'tight_labels_max_fraction': 0.25,  # labels with < 4 screen px clearance
        'precolored_max_fraction': 0.0,     # the canvas starts blank; nothing is printed in colour or white
        'overflow_labels_max_fraction': 0.4,  # numbers at the smallest size, allowed to sit over the lines
        'unnumbered_max_fraction': 0.006,   # paintable pixels no number points at
        'unnumbered_region_max_px': 900,
        'paintable_min_fraction': 0.14,
        'background_min_fraction': 0.2,
        'margin_min_px': 16,
        'line_halfwidth_max_px': 45,    # larger means a whole feature collapsed into a black blob
        'color_fidelity_max_delta_e': 12.0,  # each palette colour vs the art it paints
        'white_delta_e_min': 4.0,       # white must differ from the unpainted tint
        'fidelity_max_delta_e': 9.0,    # flattened picture vs source, away from outlines
    },
    'video': {
        'codecs': ('h264',),
        'pixel_formats': ('yuv420p',),
        'size_px': 640,
        'duration_min_s': 4.0,
        'duration_max_s': 6.5,
        'fps_min': 15.0,
        'fps_max': 30.0,
        'bytes_max': 1_600_000,
        'first_frame_max_diff': 14.0,   # mean abs diff vs source, 0-255
        'motion_min': 0.55,             # mean abs diff between sampled frames
        'cut_max': 38.0,                # one consecutive-frame jump this big is a cut or a morph
        'border_white_min': 236,
        'border_dark_frames_max_fraction': 0.12,
        'color_drift_max': 0.3,         # hue histogram distance, first vs any sampled frame
        'ink_ratio_min': 0.5,           # outlines must survive (no melt into a painting)
        'ink_ratio_max': 1.9,
        'loop_gap_warn': 22.0,          # first vs last frame; the app loops the clip
    },
}


def report(metrics, failures, warnings=()):
    return {'verdict': 'FAIL' if failures else 'PASS', 'failures': list(failures),
            'warnings': list(warnings), 'metrics': metrics}


def _lab(rgb):
    array = np.asarray(rgb, dtype=np.float32).reshape(-1, 1, 3) / 255
    return cv2.cvtColor(array, cv2.COLOR_RGB2LAB).reshape(-1, 3)


def _hex_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _border_ring(height, width, depth=12):
    ring = np.zeros((height, width), bool)
    ring[:depth] = ring[-depth:] = True
    ring[:, :depth] = ring[:, -depth:] = True
    return ring


def _bbox_margin(mask):
    ys, xs = np.where(mask)
    if not len(ys):
        return None, 0.0
    height, width = mask.shape
    margin = int(min(xs.min(), ys.min(), width - 1 - xs.max(), height - 1 - ys.max()))
    area = float((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)) / (height * width)
    return margin, area


# --------------------------------------------------------------------------
# Source image
# --------------------------------------------------------------------------

def check_image(path):
    limit = LIMITS['image']
    failures, warnings = [], []
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return report({}, [f'Cannot decode image: {path}'])
    height, width = image.shape[:2]
    metrics = {'width': width, 'height': height}
    if (width, height) != (SIZE, SIZE):
        failures.append(f'Image is {width}x{height}; the game needs a square {SIZE}x{SIZE} source')
        return report(metrics, failures)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    ring = _border_ring(height, width)
    border_white = float(rgb[ring].min(axis=1).mean())
    border_dark = float((gray[ring] < 200).mean())
    subject = (rgb.min(axis=2) < 232)
    subject = cv2.morphologyEx(np.uint8(subject), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    margin, bbox_fraction = _bbox_margin(subject)
    ink = float((gray < 60).mean())
    colorful = float(((hsv[..., 1] > 90) & (hsv[..., 2] > 90)).mean())
    metrics.update(border_white=round(border_white, 1), border_dark_fraction=round(border_dark, 4),
                   subject_margin_px=margin, subject_bbox_fraction=round(bbox_fraction, 3),
                   ink_fraction=round(ink, 4), colorful_fraction=round(colorful, 3))
    if border_white < limit['border_white_min'] or border_dark > limit['border_dark_max_fraction']:
        failures.append('Background is not clean white at the edges, or the subject touches the edge '
                        f'(border whiteness {border_white:.0f}, dark edge pixels {border_dark:.2%})')
    if margin is None:
        failures.append('No subject found on the white background')
    else:
        if margin < limit['margin_min_px']:
            failures.append(f'Subject is cropped or too close to the edge ({margin}px margin)')
        if bbox_fraction < limit['subject_min_fraction']:
            failures.append(f'Subject is too small on the canvas ({bbox_fraction:.0%} of the area)')
        if bbox_fraction > limit['subject_max_fraction']:
            failures.append(f'Subject fills the canvas with no white margin ({bbox_fraction:.0%})')
    if margin is not None:
        # A drawn frame or card border puts ink along the whole bounding box; a subject touches it at a few points.
        ys, xs = np.where(subject)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        dark = gray < 110
        band = 14
        edges = [dark[y0:y0 + band, x0:x1].any(axis=0), dark[y1 - band:y1, x0:x1].any(axis=0),
                 dark[y0:y1, x0:x0 + band].any(axis=1), dark[y0:y1, x1 - band:x1].any(axis=1)]
        coverage = float(np.concatenate(edges).mean())
        metrics['frame_coverage'] = round(coverage, 2)
        if coverage > limit['frame_max_coverage']:
            failures.append(f'A frame or border is drawn around the picture ({coverage:.0%} of its edge is ink)')
    # The model sometimes surrounds the subject with paint swatches or confetti that sit clear of the edges.
    _, _, stats, _ = cv2.connectedComponentsWithStats(np.uint8(subject), 8)
    pieces = int((stats[1:, cv2.CC_STAT_AREA] >= limit['piece_min_fraction'] * width * height).sum())
    metrics['pieces'] = pieces
    if pieces > limit['pieces_max']:
        failures.append(f'Picture is {pieces} separate pieces; loose swatches, blobs or confetti around the subject')
    # Shapes drawn without outlines number badly: neighbours bleed together and stripes vanish.
    silhouette = (np.uint8(subject) - cv2.erode(np.uint8(subject), np.ones((3, 3), np.uint8))) > 0
    spread = rgb.max(axis=2).astype(int) - rgb.min(axis=2)
    blackish = (gray < 120) & (spread < 60)     # ink, not a dark blue or purple fill
    strokes = cv2.morphologyEx(np.uint8(blackish), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))  # 1 px hairlines are not outlines
    beside_ink = cv2.dilate(strokes, np.ones((15, 15), np.uint8)) > 0
    outlined = float(beside_ink[silhouette].mean()) if silhouette.any() else 0.0
    metrics['outlined_fraction'] = round(outlined, 2)
    if outlined < limit['outlined_min_fraction']:
        failures.append(f'Shapes are drawn without black outlines ({outlined:.0%} of the silhouette is outlined)')
    if ink < limit['ink_min_fraction']:
        failures.append(f'Too little black outline for a colouring picture ({ink:.1%} ink)')
    if colorful < limit['colorful_min_fraction']:
        failures.append(f'Too little bright colour ({colorful:.0%} saturated pixels)')
    return report(metrics, failures, warnings)


# --------------------------------------------------------------------------
# Playable level bundle
# --------------------------------------------------------------------------

def _label_scale(label):
    """A number in a narrow band is drawn smaller: 'size' is its font px, 10 when absent."""
    return float(label.get('size', 10)) / 10


def _glyph_box(label):
    """Map-pixel rectangle the number covers on the narrowest phone."""
    digits = len(str(label['number']))
    scale = _label_scale(label)
    left = label['x'] + GLYPH_LEFT * scale / SCREEN
    right = left + digits * GLYPH_ADVANCE * scale / SCREEN
    bottom = label['y'] + GLYPH_BASELINE * scale / SCREEN
    top = bottom - GLYPH_HEIGHT * scale / SCREEN
    return [int(round(v)) for v in (left, top, right, bottom)]


def measure_level(folder, source=None):
    """Return (metrics, structural_failures). Structural failures stop judging."""
    folder = Path(folder)
    failures = []
    for name in ('data.json', 'map.png', 'lines.png', 'original.png'):
        if not (folder / name).is_file() or (folder / name).stat().st_size == 0:
            failures.append(f'Missing or empty {name}')
    if failures:
        return {}, failures
    data = json.loads((folder / 'data.json').read_text())
    level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
    lines = cv2.imread(str(folder / 'lines.png'), cv2.IMREAD_UNCHANGED)
    original = cv2.imread(str(folder / 'original.png'), cv2.IMREAD_COLOR)
    if level_map is None or lines is None or original is None:
        return {}, ['A level PNG cannot be decoded']
    if level_map.ndim != 2 or level_map.dtype != np.uint8:
        failures.append('map.png must be single-channel 8-bit; the game reads colour indexes from it')
    if lines.ndim != 3 or lines.shape[2] != 4:
        failures.append('lines.png must be RGBA')
    if failures:
        return {}, failures
    height, width = level_map.shape
    if (width, height) != (SIZE, SIZE) or lines.shape[:2] != (height, width) or original.shape[:2] != (height, width):
        failures.append('Level images must all be 1024x1024')
    if data.get('dimensions') != {'w': width, 'h': height}:
        failures.append('data.json dimensions do not match map.png')
    if data.get('background_id', BACKGROUND_ID) != BACKGROUND_ID or data.get('line_id', LINE_ID) != LINE_ID:
        failures.append('Background/line ids differ from the ones GameCanvas.tsx hard-codes')
    palette = data.get('palette', [])
    labels = data.get('numbers', [])
    if not all(isinstance(c, str) and len(c) == 7 and c[0] == '#' for c in palette):
        failures.append('Palette entries must be #rrggbb')
    ids = set(map(int, np.unique(level_map)))
    if not ids <= set(range(len(palette))) | {LINE_ID, BACKGROUND_ID}:
        failures.append('map.png contains colour indexes outside the palette')
    for label in labels:
        ok = (isinstance(label.get('x'), int) and isinstance(label.get('y'), int)
              and 0 <= label['x'] < width and 0 <= label['y'] < height
              and isinstance(label.get('color_index'), int) and 0 <= label['color_index'] < len(palette)
              and label.get('number') == label['color_index'] + 1)
        if not ok:
            failures.append(f'Malformed number label: {label}')
        elif level_map[label['y'], label['x']] != label['color_index']:
            failures.append(f"Number {label['number']} at ({label['x']},{label['y']}) sits on a different colour")
    if failures:
        return {}, failures

    paintable = level_map < LINE_ID
    paintable_pixels = int(paintable.sum())
    background = level_map == BACKGROUND_ID
    ink = lines[..., 3] > 0
    bridge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (NEIGHBOR_GAP, NEIGHBOR_GAP))
    structure = np.ones((3, 3), int)  # 8-connected, as the game's bucket fill

    colors, regions = [], []
    unnumbered_pixels, unnumbered_largest = 0, 0
    for index, color in enumerate(palette):
        mask = level_map == index
        area = int(mask.sum())
        own = [label for label in labels if label['color_index'] == index]
        entry = {'number': index + 1, 'hex': color, 'pixels': area,
                 'share': round(area / paintable_pixels, 4) if paintable_pixels else 0.0,
                 'labels': len(own), 'regions': 0, 'max_radius_screen_px': 0.0}
        if area:
            components, count = ndimage.label(mask, structure=structure)
            distance = cv2.distanceTransform(np.uint8(mask), cv2.DIST_L2, 5)
            wanted = np.arange(1, count + 1)
            areas = ndimage.sum(mask, components, wanted)
            radii = ndimage.maximum(distance, components, wanted)
            groups, _ = ndimage.label(cv2.dilate(np.uint8(mask), bridge) > 0, structure=structure)
            numbered = {int(components[label['y'], label['x']]) for label in own}
            numbered_groups = {int(groups[label['y'], label['x']]) for label in own}
            first_pixel = ndimage.find_objects(components)
            entry['regions'] = int(count)
            entry['max_radius_screen_px'] = round(float(radii.max()) * SCREEN, 1)
            for component in wanted:
                size, radius = int(areas[component - 1]), float(radii[component - 1])
                has_number = int(component) in numbered
                box = first_pixel[component - 1]
                inside = components[box] == component
                y, x = np.argwhere(inside)[0]
                covered = int(groups[box][y, x]) in numbered_groups
                if not covered:
                    unnumbered_pixels += size
                    unnumbered_largest = max(unnumbered_largest, size)
                regions.append({'number': index + 1, 'pixels': size,
                                'radius_screen_px': round(radius * SCREEN, 2),
                                'numbered': has_number, 'covered': covered})
            for label in own:
                left, top, right, bottom = _glyph_box(label)
                l, t, r, b = max(left, 0), max(top, 0), min(right, width), min(bottom, height)
                box_area = max((right - left) * (bottom - top), 1)
                # Measured against the size the digit is drawn at, so one limit serves both sizes.
                cy, cx = min(max((top + bottom) // 2, 0), height - 1), min(max((left + right) // 2, 0), width - 1)
                # Room around the middle of the digits (x, y is the text anchor, a few px off centre).
                label['_clearance'] = float(max(distance[cy, cx], distance[label['y'], label['x']])) * SCREEN / _label_scale(label)
                label['_inside'] = float(mask[t:b, l:r].sum()) / box_area
                label['_box'] = (left, top, right, bottom)
        colors.append(entry)

    overlaps = 0
    for i, first in enumerate(labels):
        for second in labels[i + 1:]:
            a, b = first['_box'], second['_box']
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                overlaps += 1
    # A number at the smallest size marks an area too small to hold it; it may sit over the lines.
    fitted = [label for label in labels if label.get('size', 10) > SMALLEST_LABEL]
    clearances = [label['_clearance'] for label in fitted]
    insides = [label['_inside'] for label in fitted]
    worst = sorted(fitted, key=lambda label: label['_inside'])[:5]

    used = [c for c in colors if c['pixels']]
    lab = _lab([_hex_rgb(c['hex']) for c in used]) if used else np.zeros((0, 3))
    closest = None
    for i in range(len(used)):
        for j in range(i + 1, len(used)):
            delta = float(np.linalg.norm(lab[i] - lab[j]))
            if closest is None or delta < closest[0]:
                closest = (delta, used[i]['number'], used[j]['number'])
    tint = _lab([UNPAINTED_RGB])[0]
    lightest = min((float(np.linalg.norm(row - tint)) for row in lab), default=99.0)
    # Meaningful colours: enough area, wide enough to paint, and visibly different.
    meaningful = []
    for color, value in sorted(zip(used, lab), key=lambda pair: -pair[0]['pixels']):
        if color['share'] < 0.008 or color['max_radius_screen_px'] < 3.4:
            continue
        if all(np.linalg.norm(value - other) >= 20 for other in meaningful):
            meaningful.append(value)

    pockets, pocket_count = ndimage.label(background, structure=structure)
    edge = set(np.unique(np.concatenate([pockets[0], pockets[-1], pockets[:, 0], pockets[:, -1]])))
    pocket_pixels = int(sum(ndimage.sum(background, pockets, [i for i in range(1, pocket_count + 1) if i not in edge]))) if pocket_count else 0
    margin, _ = _bbox_margin(~background)
    line_halfwidth = float(cv2.distanceTransform(np.uint8(level_map == LINE_ID), cv2.DIST_L2, 5).max())
    corners = [int(level_map[y, x]) for y in (0, height - 1) for x in (0, width - 1)]
    # Details printed in colour (not black) on the line layer: pre-coloured, not paintable.
    printed = ink & (lines[..., :3].max(axis=2) > 70)
    subject_pixels = max(int((~background).sum()), 1)

    metrics = {
        'palette_size': len(palette), 'labels': len(labels),
        'meaningful_colors': len(meaningful),
        'paintable_fraction': round(paintable_pixels / level_map.size, 3),
        'background_fraction': round(float(background.mean()), 3),
        'line_fraction': round(float((level_map == LINE_ID).mean()), 3),
        'corners_are_background': all(c == BACKGROUND_ID for c in corners),
        'subject_margin_px': margin,
        'dead_colors': [c['number'] for c in colors if not c['labels'] or not c['pixels']],
        'smallest_color_share': min((c['share'] for c in colors), default=0.0),
        'closest_colors': None if closest is None else {'delta_e': round(closest[0], 1), 'numbers': closest[1:]},
        'lightest_vs_unpainted_delta_e': round(lightest, 1),
        'label_clearance_min_screen_px': round(min(clearances), 2) if clearances else 0.0,
        'label_inside_min_fraction': round(min(insides), 2) if insides else 0.0,
        'tight_labels': sum(c < 4.0 for c in clearances),
        'overflow_labels': len(labels) - len(fitted),
        'label_overlaps': overlaps,
        'worst_labels': [{'number': l['number'], 'x': l['x'], 'y': l['y'], 'inside': round(l['_inside'], 2),
                          'clearance_screen_px': round(l['_clearance'], 2)} for l in worst],
        'unnumbered_fraction': round(unnumbered_pixels / paintable_pixels, 4) if paintable_pixels else 1.0,
        'unnumbered_largest_px': unnumbered_largest,
        'regions': len(regions),
        'regions_without_own_number': sum(not r['numbered'] for r in regions),
        'enclosed_background_px': pocket_pixels,
        'line_halfwidth_max_px': round(line_halfwidth, 1),
        'precolored_fraction_of_subject': round(float(printed.sum()) / subject_pixels, 4),
        'colors': colors,
    }
    for label in labels:
        for key in ('_clearance', '_inside', '_box'):
            label.pop(key, None)

    if source is not None:
        reference = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if reference is not None:
            reference = cv2.resize(reference, (width, height), interpolation=cv2.INTER_AREA)
            away = cv2.erode(np.uint8(paintable), np.ones((9, 9), np.uint8)) > 0
            if away.any():
                a = cv2.cvtColor(np.float32(reference) / 255, cv2.COLOR_BGR2LAB)[away]
                b = cv2.cvtColor(np.float32(original) / 255, cv2.COLOR_BGR2LAB)[away]
                delta = np.linalg.norm(a - b, axis=1)
                metrics['fidelity_mean_delta_e'] = round(float(delta.mean()), 2)
                metrics['fidelity_p95_delta_e'] = round(float(np.percentile(delta, 95)), 2)
            worst = None
            art_lab = cv2.cvtColor(np.float32(reference) / 255, cv2.COLOR_BGR2LAB)
            for color in colors:
                # Region by region: one palette colour must suit every area it paints.
                parts, count = ndimage.label(level_map == color['number'] - 1, structure=structure)
                wanted = _lab([_hex_rgb(color['hex'])])[0]
                for part in range(1, count + 1):
                    inner = cv2.erode(np.uint8(parts == part), np.ones((7, 7), np.uint8)) > 0
                    if inner.sum() < 200:
                        continue
                    drift = float(np.linalg.norm(np.median(art_lab[inner], axis=0) - wanted))
                    color['art_delta_e'] = max(color.get('art_delta_e', 0.0), round(drift, 1))
                    if worst is None or drift > worst[0]:
                        worst = (drift, color['number'])
            metrics['parts_lost_px'] = int(lost_parts(reference, level_map).sum())
            if worst:
                metrics['worst_color_fidelity'] = {'delta_e': round(worst[0], 1), 'number': worst[1]}
    return metrics, []


def judge_level(metrics):
    limit = LIMITS['level']
    failures, warnings = [], []
    m = metrics
    if not limit['palette_min'] <= m['palette_size'] <= limit['palette_max']:
        failures.append(f"{m['palette_size']} colours in the palette; ages 4+ need {limit['palette_min']}-{limit['palette_max']}")
    if m['meaningful_colors'] < limit['meaningful_colors_min']:
        failures.append(f"Only {m['meaningful_colors']} colours with a real area to paint; need {limit['meaningful_colors_min']}+")
    if not limit['labels_min'] <= m['labels'] <= limit['labels_max']:
        failures.append(f"{m['labels']} numbered areas; need {limit['labels_min']}-{limit['labels_max']}")
    if m['dead_colors']:
        failures.append(f"Palette numbers with nothing to paint: {m['dead_colors']} (the child sees a swatch that does nothing)")
    if m['smallest_color_share'] < limit['color_share_min']:
        small = [c['number'] for c in m['colors'] if c['share'] < limit['color_share_min']]
        failures.append(f'Colours {small} cover under {limit["color_share_min"]:.1%} of the picture; a number for a speck')
    closest = m['closest_colors']
    if closest and closest['delta_e'] < limit['palette_delta_e_min']:
        failures.append(f"Colours {closest['numbers'][0]} and {closest['numbers'][1]} look the same (delta E {closest['delta_e']})")
    if m['lightest_vs_unpainted_delta_e'] < limit['white_delta_e_min']:
        failures.append('A palette colour is indistinguishable from the unpainted canvas tint')
    if m['label_clearance_min_screen_px'] < limit['label_clearance_min_screen_px']:
        failures.append(f"A number sits {m['label_clearance_min_screen_px']} screen px from its region edge; it will collide with the outline: {m['worst_labels'][:3]}")
    if m['label_inside_min_fraction'] < limit['label_inside_min_fraction']:
        failures.append(f"A number spills out of its region ({m['label_inside_min_fraction']:.0%} inside): {m['worst_labels'][:3]}")
    if m['labels'] and m['tight_labels'] / m['labels'] > limit['tight_labels_max_fraction']:
        failures.append(f"{m['tight_labels']} of {m['labels']} numbers are in cramped regions; too fiddly for small fingers")
    if m['labels'] and m['overflow_labels'] / m['labels'] > limit['overflow_labels_max_fraction']:
        failures.append(f"{m['overflow_labels']} of {m['labels']} numbers mark areas too small to hold them; the art is too fiddly")
    if m['label_overlaps']:
        failures.append(f"{m['label_overlaps']} pairs of numbers are drawn on top of each other")
    if m['unnumbered_fraction'] > limit['unnumbered_max_fraction']:
        failures.append(f"{m['unnumbered_fraction']:.1%} of the paintable area has no number near it; the picture cannot be finished by following numbers")
    if m['unnumbered_largest_px'] > limit['unnumbered_region_max_px']:
        failures.append(f"A {m['unnumbered_largest_px']}px region has no number")
    if m['paintable_fraction'] < limit['paintable_min_fraction']:
        failures.append(f"Only {m['paintable_fraction']:.0%} of the canvas is paintable")
    if m['background_fraction'] < limit['background_min_fraction'] or not m['corners_are_background']:
        failures.append('Background was not separated from the subject (corners must be background)')
    if m['subject_margin_px'] is None or m['subject_margin_px'] < limit['margin_min_px']:
        failures.append(f"Subject is cropped or touches the edge ({m['subject_margin_px']}px margin)")
    if m['enclosed_background_px'] > 0:
        failures.append(f"{m['enclosed_background_px']}px of enclosed background can never be painted")
    if m['precolored_fraction_of_subject'] > limit['precolored_max_fraction']:
        failures.append(f"{m['precolored_fraction_of_subject']:.0%} of the picture is pre-coloured detail too small to paint; the art is too fiddly")
    if m['line_halfwidth_max_px'] > limit['line_halfwidth_max_px']:
        failures.append(f"A black blob {2 * m['line_halfwidth_max_px']:.0f}px wide: a detail collapsed into solid ink")
    fidelity = m.get('fidelity_mean_delta_e')
    if fidelity is not None and fidelity > limit['fidelity_max_delta_e']:
        failures.append(f'Flattened colours drift from the source art (mean delta E {fidelity}); the source has gradients or shading')
    drift = m.get('worst_color_fidelity')
    if drift and drift['delta_e'] > limit['color_fidelity_max_delta_e']:
        failures.append(f"Colour {drift['number']} paints an area that is a different colour in the art (delta E {drift['delta_e']})")
    if m.get('parts_lost_px', 0) > limit['lost_part_min_px']:
        failures.append(f"A part of the picture ({m['parts_lost_px']}px) has become background; it cannot be painted and leaves a hole in the subject")
    if m['regions_without_own_number'] > m['labels']:
        warnings.append(f"{m['regions_without_own_number']} small regions share a neighbour's number")
    return report(metrics, failures, warnings)


def page_of(source_bgr):
    """The white paper around the subject: near-white art connected to the picture's edge."""
    white = np.uint8(source_bgr.min(axis=2) > 225)
    _, labels = cv2.connectedComponents(white, connectivity=4)
    edge = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    return np.isin(labels, edge[edge > 0])


def lost_parts(source_bgr, level_map, min_px=1500):
    """Parts of the subject that the map calls background: a white sail, a cream tummy.

    process.py floods the background through fine outlines and takes pale colours
    for paper, so these can end up unpaintable. Anything the art's page does not
    reach is part of the subject. Fringes and small gaps between shapes are ignored.
    """
    background = level_map == BACKGROUND_ID
    lost = background & ~page_of(source_bgr)
    core = cv2.morphologyEx(np.uint8(lost), cv2.MORPH_OPEN, np.ones((17, 17), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(core, 8)
    big = np.zeros(count, bool)
    height, width = level_map.shape
    left, top = stats[:, cv2.CC_STAT_LEFT], stats[:, cv2.CC_STAT_TOP]
    at_border = ((left <= 1) | (top <= 1) | (left + stats[:, cv2.CC_STAT_WIDTH] >= width - 1)
                 | (top + stats[:, cv2.CC_STAT_HEIGHT] >= height - 1))
    # Tinted or shaded paper reaches the border; a lost part sits inside the subject.
    big[1:] = (stats[1:, cv2.CC_STAT_AREA] >= min_px) & ~at_border[1:]
    found = big[labels]
    if found.sum() > 0.5 * background.sum():
        return np.zeros_like(found)  # the paper itself is tinted; nothing is lost
    return found


def check_level(folder, source=None, level_id=None, require_reward=False):
    folder = Path(folder)
    metrics, failures = measure_level(folder, source)
    if failures:
        return report(metrics, failures)
    result = judge_level(metrics)
    data = json.loads((folder / 'data.json').read_text())
    if level_id is not None and str(data.get('id')) != str(level_id):
        result['failures'].append(f"data.json id {data.get('id')!r} is not level {level_id}")
    if require_reward:
        if data.get('has_reward') is not True or not (folder / 'reward.mp4').is_file():
            result['failures'].append('Level has no reward video')
    result['verdict'] = 'FAIL' if result['failures'] else 'PASS'
    return result


# --------------------------------------------------------------------------
# Reward video
# --------------------------------------------------------------------------

def probe_video(path):
    output = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
        capture_output=True, text=True, timeout=60)
    if output.returncode != 0:
        raise ValueError(f'ffprobe failed: {output.stderr.strip()[:200]}')
    return json.loads(output.stdout)


def read_frames(path, size=320):
    capture = cv2.VideoCapture(str(path))
    frames = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA))
    capture.release()
    return frames


def _hue_histogram(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    vivid = (hsv[..., 1] > 80) & (hsv[..., 2] > 80)
    histogram = np.bincount(hsv[..., 0][vivid] // 10, minlength=18).astype(float)
    # Spread each bin onto its neighbours (hue is circular). A colour sitting on a bin edge, like the
    # whale's blue at hue 100, otherwise reads as a recolour when re-encoding nudges it across.
    histogram = (np.roll(histogram, 1) + 2 * histogram + np.roll(histogram, -1)) / 4
    return histogram / frame.shape[0] / frame.shape[1]


def check_video(path, source):
    limit = LIMITS['video']
    failures, warnings = [], []
    path = Path(path)
    try:
        probe = probe_video(path)
    except (ValueError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        return report({}, [f'Video cannot be read: {error}'])
    videos = [s for s in probe.get('streams', []) if s.get('codec_type') == 'video']
    if len(videos) != 1:
        return report({}, [f'Expected one video stream, found {len(videos)}'])
    stream = videos[0]
    rate = stream.get('avg_frame_rate', '0/1').split('/')
    fps = float(rate[0]) / float(rate[1]) if len(rate) == 2 and float(rate[1]) else 0.0
    duration = float(stream.get('duration') or probe.get('format', {}).get('duration') or 0)
    metrics = {'codec': stream.get('codec_name'), 'pixel_format': stream.get('pix_fmt'),
               'width': stream.get('width'), 'height': stream.get('height'),
               'fps': round(fps, 2), 'duration_s': round(duration, 2), 'bytes': path.stat().st_size,
               'audio_streams': sum(s.get('codec_type') == 'audio' for s in probe.get('streams', []))}
    if metrics['codec'] not in limit['codecs'] or metrics['pixel_format'] not in limit['pixel_formats']:
        failures.append(f"Video is {metrics['codec']}/{metrics['pixel_format']}; phones need H.264 yuv420p")
    if metrics['width'] != metrics['height']:
        failures.append(f"Video is {metrics['width']}x{metrics['height']}; the picture is square")
    elif metrics['width'] != limit['size_px']:
        warnings.append(f"Video is {metrics['width']}px, not {limit['size_px']}px")
    if not limit['duration_min_s'] <= duration <= limit['duration_max_s']:
        failures.append(f'Video lasts {duration:.1f}s; rewards run {limit["duration_min_s"]}-{limit["duration_max_s"]}s')
    if not limit['fps_min'] <= fps <= limit['fps_max']:
        failures.append(f'Video is {fps:.1f} fps')
    if metrics['bytes'] > limit['bytes_max']:
        failures.append(f"Video is {metrics['bytes'] / 1e6:.1f} MB; over the {limit['bytes_max'] / 1e6:.1f} MB bundle budget")
    if metrics['audio_streams']:
        warnings.append('Video has an audio track; the app plays rewards with its own sounds')

    frames = read_frames(path)
    metrics['frames'] = len(frames)
    if len(frames) < 30:
        failures.append(f'Only {len(frames)} frames decode')
        return report(metrics, failures, warnings)
    reference = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if reference is None:
        failures.append(f'Cannot read the source picture {source}')
        return report(metrics, failures, warnings)
    reference = cv2.resize(reference, frames[0].shape[1::-1], interpolation=cv2.INTER_AREA)
    as_float = [frame.astype(np.float32) for frame in frames]
    first_diff = float(np.abs(as_float[0] - reference).mean())
    steps = [float(np.abs(b - a).mean()) for a, b in zip(as_float, as_float[1:])]
    from_first = [float(np.abs(frame - as_float[0]).mean()) for frame in as_float]
    ring = _border_ring(*frames[0].shape[:2], depth=5)
    border_white = [float(frame[ring].min(axis=1).mean()) for frame in frames]
    border_dark = [float((frame[ring].min(axis=1) < 150).mean()) for frame in frames]
    touching = sum(value > 0.01 for value in border_dark) / len(frames)
    base_hue = _hue_histogram(frames[0])
    drift = max(float(np.abs(_hue_histogram(frame) - base_hue).sum()) / max(base_hue.sum(), 1e-6)
                for frame in frames[::4])
    ink = [float((cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) < 60).mean()) for frame in frames[::4]]
    ink_ratio = [value / max(ink[0], 1e-6) for value in ink]
    metrics.update(first_frame_diff=round(first_diff, 2), motion_mean=round(float(np.mean(steps)), 2),
                   motion_peak=round(max(steps), 2), displacement_peak=round(max(from_first), 2),
                   loop_gap=round(from_first[-1], 2), border_white_min=round(min(border_white), 1),
                   frames_touching_edge_fraction=round(touching, 3), color_drift=round(drift, 3),
                   ink_ratio_min=round(min(ink_ratio), 2), ink_ratio_max=round(max(ink_ratio), 2))
    if first_diff > limit['first_frame_max_diff']:
        failures.append(f'First frame does not match the finished picture (difference {first_diff:.1f})')
    if max(from_first) < limit['motion_min'] * 4 or np.mean(steps) < limit['motion_min']:
        failures.append(f'Hardly anything moves (mean frame change {np.mean(steps):.2f})')
    if max(steps) > limit['cut_max']:
        failures.append(f'A sudden jump between frames ({max(steps):.1f}): a cut, flash or morph')
    if min(border_white) < limit['border_white_min']:
        failures.append(f'Background does not stay white, or the camera moves (edge whiteness falls to {min(border_white):.0f})')
    if touching > limit['border_dark_frames_max_fraction']:
        failures.append(f'Subject leaves the frame in {touching:.0%} of frames')
    elif touching:
        warnings.append(f'Subject brushes the frame edge in {touching:.0%} of frames')
    if drift > limit['color_drift_max']:
        failures.append(f'Colours change during the clip (hue drift {drift:.2f}); new objects or a recolour')
    if min(ink_ratio) < limit['ink_ratio_min'] or max(ink_ratio) > limit['ink_ratio_max']:
        failures.append(f'Black outlines change by {min(ink_ratio):.2f}x-{max(ink_ratio):.2f}x; the drawing style is not preserved')
    if from_first[-1] > limit['loop_gap_warn']:
        warnings.append(f'Clip ends far from where it starts (gap {from_first[-1]:.1f}); the loop will jump')
    return report(metrics, failures, warnings)
