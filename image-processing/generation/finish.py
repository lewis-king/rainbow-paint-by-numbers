"""Turn process.py's output into a level a four-year-old can actually finish.

process.py is kept exactly as Lewis wrote it; it decides the colours, the
outlines and the look. Its raw output has three faults that every level it
produced shares, and this pass removes them without redrawing anything:

1. Slivers. Anti-aliased edges and tiny details become their own regions,
   each with a number nobody can read or tap. A region too narrow to hold a
   digit is absorbed into the region it borders when it is a fringe. A real
   detail (a stripe, a spot, a tassel) stays an area to paint with a smaller
   number. Nothing is printed in colour: the child starts from a blank canvas.
   The white sparkle in an eye is the one printed detail.
2. Dead swatches. The palette keeps colours that have nothing left to paint.
   The palette is compacted so every swatch number appears in the picture.
3. Look-alike colours. Two shades a child cannot tell apart become one.

When the source picture is given, two things process.py loses are put back:
palette colours are re-read from the art (its colour merge keeps the darkest
shade, which turns cream grey), regions it merged across two different art
colours are separated again (turquoise water joined to a blue whale), and dark outline pixels it handed to a light
region are inked again (it erodes round eyes into squares).

Then every region gets its own number, centred where the digit fits best.

The pass is deterministic: the same process.py output always gives the same
bytes. Fixed details live in lines.png (which the game draws on top) with
map.png set to the line id, so the app needs no change.
"""
import json
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage

from checks import (BACKGROUND_ID, LINE_ID, SCREEN, GLYPH_ADVANCE, GLYPH_LEFT,
                    GLYPH_BASELINE, GLYPH_HEIGHT, NEIGHBOR_GAP, _lab, _hex_rgb, lost_parts, page_of)

REVISION = 11
# A region must hold a circle this wide (map px) to carry a legible number:
# 3.9 screen px radius on the narrowest phone, so a digit sits clear of the outline.
MIN_RADIUS = 11.5
MIN_AREA = 420
MERGE_DELTA_E = 11.0           # the level check wants colours at least this far apart
MIN_COLOR_SHARE = 0.005
SPECK_COLOR_SHARE = 0.0004  # a whole palette colour for less than this is not worth a swatch
INK_LUMINANCE = 70          # source pixels darker than this are outline
LIGHT_LUMINANCE = 110       # ...when the region they fell into is lighter than this
BLACK_FILL_RADIUS = 26      # black wider than this is an area to paint; narrower is ink (eyes, noses)
DASH_RADIUS = 3.5           # ink thinner than this (map px half-width)...
DASH_AREA = 400             # ...and smaller than this is a broken outline fragment, not a detail
STROKE_MIN_AREA = 40        # smaller dark specks inside a colour are noise, not drawing
LINE_WEIGHT = 5             # map px added to every region boundary: about 2 px on a phone
FRAME_MARGIN = 56           # white margin frame_picture leaves around the subject
# The child should paint as much of the picture as possible: they can pinch to zoom, and the
# rainbow brush is there when an area is fiddly. So a small area keeps its number, drawn smaller.
SMALL_RADIUS = 5.0          # an area this wide (map px half-width: a tassel, a thin border)...
SMALL_AREA = 400            # ...and this big is still painted by the child...
SMALL_SIZE_MIN = 4          # ...with a number shrunk to fit, down to this font px; normal is 10
DECOR_RADIUS = 2.5          # a sliver at least this wide (map px half-width)...
DECOR_AREA = 60             # ...and this big...
DECOR_DELTA_E = 18.0        # ...and this different from the area beside it is a detail to paint, not a fringe
SHADE_DELTA_E = 20.0        # touching regions of one hue closer than this are light and shadow on one thing
SHADE_HUE = 18.0            # degrees of hue two shades may differ by
SHADE_CHROMA = 12.0         # greys and whites are never shades of each other: a white tummy is its own part
TRUE_DELTA_E = 12.0         # an area may not paint a colour further than this from the art under it
MAX_ROUNDS = 40             # absorb_slivers settles in a handful; this stops two slivers trading colours forever
MIXED_DELTA_E = 22.0        # a patch this far from the rest of its region is another colour of the art...
MIXED_AREA = 600            # ...when it is at least this big...
MIXED_SPREAD = 7.0          # ...and this even in itself (delta E, 75th percentile)
LOST_PART_AREA = 300        # a piece of the subject this big that became background is given back
EIGHT = np.ones((3, 3), int)


def _components(mask):
    labels, count = ndimage.label(mask, structure=EIGHT)
    if not count:
        return labels, [], [], None
    index = np.arange(1, count + 1)
    distance = cv2.distanceTransform(np.uint8(mask), cv2.DIST_L2, 5)
    return labels, ndimage.sum(mask, labels, index), ndimage.maximum(distance, labels, index), distance


def merge_lookalikes(level_map, palette):
    """Map each colour to the largest colour it cannot be told apart from."""
    lab = _lab([_hex_rgb(c) for c in palette])
    areas = [int((level_map == i).sum()) for i in range(len(palette))]
    keepers, target = [], {}
    for index in sorted(range(len(palette)), key=lambda i: (-areas[i], i)):
        if not areas[index]:
            continue
        match = next((k for k in keepers if np.linalg.norm(lab[index] - lab[k]) < MERGE_DELTA_E), None)
        if match is None:
            keepers.append(index)
        else:
            target[index] = match
    for source, destination in target.items():
        level_map[level_map == source] = destination
    return len(target)


def merge_shades(level_map, palette):
    """Shadow and highlight painted on an object become part of it.

    Shaded art gives an egg a darker green crescent with no line round it; numbered, that is
    a second green nobody can tell from the first. A region that mostly touches a bigger
    region of the same hue, with no outline between them, joins it. Different hues, greys,
    and anything the artist separated with a line are left alone.
    """
    lab = _lab([_hex_rgb(c) for c in palette])
    chroma = np.hypot(lab[:, 1], lab[:, 2]) if len(palette) else np.array([])
    hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) if len(palette) else np.array([])
    totals = np.bincount(level_map.ravel(), minlength=256)
    merged = 0
    for index in sorted(range(len(palette)), key=lambda i: (totals[i], i)):
        if not totals[index] or chroma[index] < SHADE_CHROMA:
            continue
        labels, areas, _, _ = _components(level_map == index)
        boxes = ndimage.find_objects(labels)
        for number, area in enumerate(areas, 1):
            box = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in boxes[number - 1])
            inside = labels[box] == number
            ring = (cv2.dilate(np.uint8(inside), np.ones((3, 3), np.uint8)) > 0) & ~inside
            values = level_map[box][ring]
            touching = values[values < LINE_ID]
            if len(touching) < 0.3 * len(values):
                continue  # mostly outlined: the artist drew it as its own part
            home = int(np.argmax(np.bincount(touching, minlength=256)))
            turn = abs((hue[home] - hue[index] + 180) % 360 - 180)
            if (home == index or chroma[home] < SHADE_CHROMA or turn > SHADE_HUE
                    or np.linalg.norm(lab[home] - lab[index]) >= SHADE_DELTA_E or totals[home] < 2 * area):
                continue
            level_map[box][inside] = home
            merged += 1
    return merged


def keep_true_colors(level_map, palette, source_bgr):
    """Every area paints the colour the picture shows there. Nothing above may change that.

    The merges work colour by colour and can carry one area along with a colour it only
    resembles. Each area is checked against the art under it; one that has drifted takes the
    palette colour that does match, or a new colour read from the art.
    """
    lab = [tuple(v) for v in _lab([_hex_rgb(c) for c in palette])]
    live = [bool((level_map == i).any()) for i in range(len(palette))]
    fixed = 0
    for index in range(len(palette)):
        labels, areas, _, _ = _components(level_map == index)
        for number in range(1, len(areas) + 1):
            part = labels == number
            inner = cv2.erode(np.uint8(part), np.ones((7, 7), np.uint8)) > 0
            if inner.sum() < 150:
                continue  # too thin to measure: a sliver, handled next
            b, g, r = (int(v) for v in np.median(source_bgr[inner], axis=0))
            seen = _lab([(r, g, b)])[0]
            if np.linalg.norm(seen - lab[index]) <= TRUE_DELTA_E:
                continue
            # Only colours still in the picture: one a merge retired must not come back as a look-alike.
            gaps = [float(np.linalg.norm(seen - np.array(v))) if live[i] else 1e9 for i, v in enumerate(lab)]
            match = int(np.argmin(gaps))
            if gaps[match] > MERGE_DELTA_E:
                if len(palette) >= LINE_ID:
                    continue
                palette.append('#{:02x}{:02x}{:02x}'.format(r, g, b))
                lab.append(tuple(_lab([(r, g, b)])[0]))
                live.append(True)
                match = len(palette) - 1
            level_map[part] = match
            fixed += 1
    return fixed


def _same_hue(lab, first, second):
    chroma = lambda v: float(np.hypot(v[1], v[2]))
    if chroma(lab[first]) < SHADE_CHROMA or chroma(lab[second]) < SHADE_CHROMA:
        return False
    hue = lambda v: float(np.degrees(np.arctan2(v[2], v[1])))
    return abs((hue(lab[first]) - hue(lab[second]) + 180) % 360 - 180) <= SHADE_HUE


def absorb_slivers(level_map, palette):
    """Remove fringes, keep detail. Returns (sparkles, absorbed).

    The canvas starts blank: nothing is printed in colour for the child. So a small area is
    one of three things. A fringe (anti-aliasing, a shadow's edge) joins the area beside it.
    A detail (a stripe on an egg, a spot, a tassel) stays an area to paint and gets a small
    number. A speck with nowhere to go becomes outline, unless it is the white sparkle in an
    eye, which is the one thing still printed (`sparkles`).
    """
    palette_size = len(palette)
    lab = _lab([_hex_rgb(c) for c in palette]) if palette else []
    ring_kernel = np.ones((5, 5), np.uint8)
    keep = np.zeros(level_map.shape, bool)
    is_detail = lambda area, radius: radius >= DECOR_RADIUS and area >= DECOR_AREA
    absorbed = 0
    rounds = 0
    while True:
        rounds += 1
        slivers = []
        sliver_mask = np.zeros(level_map.shape, bool)
        for index in range(palette_size):
            mask = level_map == index
            if not mask.any():
                continue
            labels, areas, radii, _ = _components(mask)
            kept = ndimage.maximum(keep, labels, np.arange(1, len(areas) + 1))
            boxes = ndimage.find_objects(labels)
            for number, (area, radius) in enumerate(zip(areas, radii), 1):
                if (radius < SMALL_RADIUS or area < SMALL_AREA) and not kept[number - 1]:
                    box = boxes[number - 1]
                    grown = tuple(slice(max(s.start - 3, 0), s.stop + 3) for s in box)
                    slivers.append((int(area), index, grown, labels[grown] == number, float(radius)))
                    sliver_mask[grown] |= labels[grown] == number
        changed = False
        # Smallest first, so a fringe joins its fill before the fill is judged.
        slivers.sort(key=lambda s: (s[0], s[1], s[2][0].start, s[2][1].start))
        for area, index, box, inside, radius in slivers:
            ring = (cv2.dilate(np.uint8(inside), ring_kernel) > 0) & ~inside
            values = level_map[box][ring & ~sliver_mask[box]]
            # Its own colour across a thin line is no home: joining it leaves the sliver a sliver.
            values = values[(values != LINE_ID) & (values != index)]
            if not len(values):
                continue
            home = int(np.argmax(np.bincount(values, minlength=256)))
            changed = True
            sliver_mask[box][inside] = False
            if (home < palette_size and is_detail(area, radius) and not (radius < 4 and _same_hue(lab, index, home))
                    and np.linalg.norm(lab[index] - lab[home]) >= DECOR_DELTA_E):
                keep[box][inside] = True   # a detail in its own colour: the child paints it
                continue
            level_map[box][inside] = home
            absorbed += 1
        if not slivers or not changed or rounds >= MAX_ROUNDS:
            break
    # What is left has no area to join: it is ringed by outline or by other slivers.
    sparkles = np.zeros(level_map.shape, bool)
    for area, index, box, inside, radius in slivers:
        if not sliver_mask[box][inside].all():
            continue
        r, g, b = _hex_rgb(palette[index])
        if min(r, g, b) > 225 and area < MIN_AREA:
            sparkles[box][inside] = True
        elif not is_detail(area, radius):
            level_map[box][inside] = LINE_ID
    return sparkles, absorbed


def group_leaders(mask, labels, areas, radii):
    """One number for a cluster of same-coloured neighbours, as process.py always did.

    A flower with one petal marked 12 tells the child the petals beside it are 12 too; a number
    in every petal is clutter and takes the small puzzle away. Areas of one colour closer than
    NEIGHBOR_GAP form a group, and the roomiest one carries the number.
    """
    if not len(areas):
        return []
    bridge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (NEIGHBOR_GAP, NEIGHBOR_GAP))
    groups, _ = ndimage.label(cv2.dilate(np.uint8(mask), bridge) > 0, structure=EIGHT)
    best = {}
    for number in range(1, len(areas) + 1):
        group = int(groups[labels == number][0])
        rank = (float(radii[number - 1]), float(areas[number - 1]), -number)
        if group not in best or rank > best[group][0]:
            best[group] = (rank, number)
    return sorted(number for _, number in best.values())


def place_label(distance, component, box, number, scale=1.0):
    """Centre the digits on the widest point, as GameCanvas.tsx will draw them."""
    local = np.where(component, distance[box], 0)
    y, x = np.unravel_index(int(np.argmax(local)), local.shape)
    y, x = y + box[0].start, x + box[1].start
    width = len(str(number)) * GLYPH_ADVANCE * scale
    shifted_x = int(round(x - (GLYPH_LEFT * scale + width / 2) / SCREEN))
    shifted_y = int(round(y - (GLYPH_BASELINE - GLYPH_HEIGHT / 2) * scale / SCREEN))
    height, full_width = distance.shape
    if (0 <= shifted_x < full_width and 0 <= shifted_y < height
            and box[0].start <= shifted_y < box[0].stop and box[1].start <= shifted_x < box[1].stop
            and component[shifted_y - box[0].start, shifted_x - box[1].start]):
        return shifted_x, shifted_y
    return int(x), int(y)


def _luminance(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def true_colors(level_map, palette, source_bgr):
    """Each palette colour becomes the median of the art inside its regions."""
    result = list(palette)
    for index in range(len(palette)):
        inner = cv2.erode(np.uint8(level_map == index), np.ones((7, 7), np.uint8)) > 0
        if inner.sum() < 200:
            continue
        b, g, r = np.median(source_bgr[inner], axis=0)
        result[index] = '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))
    return result


def split_overmerged(level_map, palette, source_bgr):
    """Give regions their own colour when process.py merged two different art colours.

    Its merge works on RGB distance and happily joins turquoise to blue. Regions of
    one palette entry whose art colours differ visibly become separate entries.
    """
    art_lab = cv2.cvtColor(np.float32(source_bgr) / 255, cv2.COLOR_BGR2LAB)
    added = 0
    for index in range(len(palette)):
        labels, areas, _, _ = _components(level_map == index)
        groups = []  # [lab, [component numbers]]
        for number in sorted(range(1, len(areas) + 1), key=lambda n: (-areas[n - 1], n)):
            inner = cv2.erode(np.uint8(labels == number), np.ones((7, 7), np.uint8)) > 0
            if inner.sum() < 150:
                continue  # too thin to measure; stays with the entry and is handled as a sliver
            color = np.median(art_lab[inner], axis=0)
            match = next((g for g in groups if np.linalg.norm(color - g[0]) < MERGE_DELTA_E), None)
            if match is None:
                groups.append([color, [number]])
            else:
                match[1].append(number)
        for _, members in groups[1:]:
            if len(palette) >= LINE_ID:
                break
            level_map[np.isin(labels, members)] = len(palette)
            palette.append(palette[index])  # true_colors() sets the real colour next
            added += 1
    return added


def split_mixed(level_map, palette, source_bgr):
    """Divide a region that holds two flat colours of the art with no line between them.

    process.py joins pink flippers to a grey seal and paints both one colour. A patch
    that differs clearly from the rest of its region, is big enough to paint and is
    itself one even colour becomes its own area. Soft shading is uneven and stays.
    """
    smooth = cv2.medianBlur(source_bgr, 9)
    art_lab = cv2.cvtColor(np.float32(smooth) / 255, cv2.COLOR_BGR2LAB)
    bright = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY) > INK_LUMINANCE
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    added = 0
    for index in range(len(palette)):
        labels, areas, _, _ = _components(level_map == index)
        boxes = ndimage.find_objects(labels)
        for number, area in enumerate(areas, 1):
            if area < 2 * MIXED_AREA:
                continue
            box = boxes[number - 1]
            inside = labels[box] == number
            lab = art_lab[box]
            home = np.median(lab[inside], axis=0)
            odd = inside & bright[box] & (np.linalg.norm(lab - home, axis=2) > MIXED_DELTA_E)
            odd = cv2.morphologyEx(np.uint8(odd), cv2.MORPH_OPEN, kernel)
            count, parts = cv2.connectedComponents(odd, connectivity=8)
            for part in range(1, count):
                patch = parts == part
                if patch.sum() < MIXED_AREA or cv2.distanceTransform(np.uint8(patch), cv2.DIST_L2, 3).max() < MIN_RADIUS:
                    continue  # a streak or sprinkle, not a part with room for a number
                color = np.median(lab[patch], axis=0)
                spread = np.percentile(np.linalg.norm(lab[patch] - color, axis=1), 75)
                if spread > MIXED_SPREAD or np.linalg.norm(color - home) < MIXED_DELTA_E:
                    continue
                if _same_hue([color, home], 0, 1):
                    continue  # lighter or darker of the same hue is shading, however strong
                b, g, r = (int(v) for v in np.median(source_bgr[box][patch], axis=0))
                known = _lab([(r, g, b)] + [_hex_rgb(c) for c in palette])
                gaps = np.linalg.norm(known[1:] - known[0], axis=1)
                target = int(np.argmin(gaps))
                if gaps[target] >= MERGE_DELTA_E:
                    if len(palette) >= LINE_ID:
                        continue
                    palette.append('#%02x%02x%02x' % (r, g, b))
                    target = len(palette) - 1
                level_map[box][patch] = target
                added += 1
    return added


def restore_ink(level_map, palette, source_bgr):
    """Dark art pixels that ended up inside a light region are outline again."""
    gray = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2GRAY)
    light = np.zeros(256, bool)
    for index, color in enumerate(palette):
        light[index] = _luminance(_hex_rgb(color)) > LIGHT_LUMINANCE
    light[BACKGROUND_ID] = True
    ink = (gray < INK_LUMINANCE) & light[level_map]
    ink = cv2.morphologyEx(np.uint8(ink), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    level_map[ink] = LINE_ID
    return int(ink.sum())


def reclaim_parts(level_map, palette, source_bgr):
    """A part of the subject that became background (a white sail, a cream tummy
    behind a hairline outline) is an area to paint, in the art's colour."""
    # A few rounds: what is left of a big part after one round can still be a piece worth keeping.
    return sum(_reclaim_round(level_map, palette, source_bgr) for _ in range(4))


def _reclaim_round(level_map, palette, source_bgr):
    cores = lost_parts(source_bgr, level_map, min_px=LOST_PART_AREA)
    if not cores.any():
        return 0
    # Undo the opening lost_parts uses, without following the fringe around the outline.
    candidates = (level_map == BACKGROUND_ID) & ~page_of(source_bgr)
    count, labels = cv2.connectedComponents(np.uint8(cores), connectivity=8)
    total = 0
    for part in range(1, count):
        core = labels == part
        grown = (cv2.dilate(np.uint8(core), np.ones((21, 21), np.uint8)) > 0) & candidates
        b, g, r = (int(v) for v in np.median(source_bgr[core], axis=0))
        rgb = (255, 255, 255) if min(r, g, b) > 225 else (r, g, b)
        index = None
        if palette:
            lab = _lab([rgb] + [_hex_rgb(c) for c in palette])
            gaps = np.linalg.norm(lab[1:] - lab[0], axis=1)
            if gaps.min() < MERGE_DELTA_E:
                index = int(np.argmin(gaps))
        if index is None:
            if len(palette) >= LINE_ID:
                continue
            palette.append('#%02x%02x%02x' % rgb)
            index = len(palette) - 1
        level_map[grown] = index
        total += int(grown.sum())
    return total


def _is_black(rgb):
    return _luminance(rgb) < 60 and max(rgb) - min(rgb) < 45


def redraw_black(level_map, palette, source_bgr=None):
    """Decide afresh which black is outline and which is a black area to paint.

    process.py opens dark areas with a 30px square, which leaves a numbered
    square inside every round eye and spot. Here all black (ink plus any
    near-black colour) is pooled; only parts wide enough to be a real area
    (a ladybird's spot, a toucan's body) are paintable, in their true shape.
    """
    dark = [i for i, color in enumerate(palette) if _is_black(_hex_rgb(color))]
    pool = (level_map == LINE_ID) | np.isin(level_map, dark)
    size = 2 * BLACK_FILL_RADIUS + 1
    core = cv2.morphologyEx(np.uint8(pool), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
    grow = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BLACK_FILL_RADIUS + 1, BLACK_FILL_RADIUS + 1))
    fill = pool & (cv2.dilate(core, grow) > 0)
    level_map[pool] = LINE_ID
    if not fill.any():
        return 0
    if dark:
        index = dark[0]
    elif len(palette) < LINE_ID:
        palette.append('#000000')
        index = len(palette) - 1
    else:
        return 0
    level_map[fill] = index
    if source_bgr is not None:
        # A wide dark area that is a colour in the art (a navy tent door) is that colour, not black.
        labels, areas, _, _ = _components(fill)
        for number in range(1, len(areas) + 1):
            part = labels == number
            inner = cv2.erode(np.uint8(part), np.ones((7, 7), np.uint8)) > 0
            if inner.sum() < 150:
                continue
            b, g, r = (int(v) for v in np.median(source_bgr[inner], axis=0))
            if _is_black((r, g, b)):
                continue
            lab = _lab([(r, g, b)] + [_hex_rgb(c) for c in palette])
            gaps = np.linalg.norm(lab[1:] - lab[0], axis=1)
            match = int(np.argmin(gaps))
            if gaps[match] >= MERGE_DELTA_E or match == index:
                if len(palette) >= LINE_ID:
                    continue
                palette.append('#{:02x}{:02x}{:02x}'.format(r, g, b))
                match = len(palette) - 1
            level_map[part] = match
    return int(fill.sum())


def drop_dashes(level_map):
    """Hand broken outline fragments back to the region they sit in.

    Thin-lined art comes out of process.py with its outlines in pieces: short
    dashes along a boundary and stray strokes inside a region. Compact marks
    (pupils, noses) and long continuous lines are kept. Where two regions then
    meet without ink, finish_level draws one clean boundary line.
    """
    ink = level_map == LINE_ID
    labels, areas, radii, _ = _components(ink)
    if not len(areas):
        return 0
    dash = np.zeros(len(areas) + 1, bool)
    dash[1:] = (np.asarray(areas) < DASH_AREA) & (np.asarray(radii) < DASH_RADIUS)
    dashes = dash[labels]
    if not dashes.any() or ink.all():
        return 0
    _, nearest = ndimage.distance_transform_edt(ink, return_indices=True)
    level_map[dashes] = level_map[nearest[0][dashes], nearest[1][dashes]]
    return int(dashes.sum())


def even_lines(boundaries, ink, printed):
    """The black outline mask. Region boundaries get one steady weight and a smooth edge, so a
    picture drawn with fine lines does not come out part hairline, part heavy."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (LINE_WEIGHT, LINE_WEIGHT))
    # A line the artist already drew at full weight is left alone: thickening it again
    # closes up narrow bands (a carpet border) until there is nothing left to paint.
    heavy = cv2.morphologyEx(np.uint8(ink), cv2.MORPH_OPEN, kernel)
    light = boundaries & ~(cv2.dilate(heavy, np.ones((5, 5), np.uint8)) > 0)
    black = (cv2.dilate(np.uint8(light), kernel) > 0) | ink
    black = cv2.GaussianBlur(np.float32(black), (0, 0), 1.6) > 0.5
    # Printed colour details keep their colour; only their true edge is inked.
    return (black & ~printed) | boundaries | ink


def detail_strokes(level_map, palette, source_bgr):
    """Fine black strokes the artist drew inside a colour: a mouth, whiskers, strands of wool.

    They are printed over the paint and never touch the map, so they add no regions and no
    numbers. Only strokes much darker than the colour they sit on count, and only thin ones.
    """
    gray = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2GRAY).astype(int)
    spread = source_bgr.max(axis=2).astype(int) - source_bgr.min(axis=2)
    region = np.zeros(256, int)
    for index, color in enumerate(palette):
        region[index] = _luminance(_hex_rgb(color))
    paint = level_map < LINE_ID
    dark = (gray < 110) & (spread < 60) & paint & (region[level_map] - gray > 50)
    wide = cv2.morphologyEx(np.uint8(dark), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)) > 0
    thin = cv2.morphologyEx(np.uint8(dark & ~wide), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    labels, areas, _, _ = _components(thin)
    keep = np.zeros(len(areas) + 1, bool)
    keep[1:] = np.asarray(areas) >= STROKE_MIN_AREA
    return keep[labels] & paint


def frame_picture(image_bgr):
    """Shrink and centre a subject drawn too close to the edge. None if it cannot help.

    Only a picture on clean white, not touching the edge, is reframed; a cropped
    subject stays as it is so the image check rejects it.
    """
    height, width = image_bgr.shape[:2]
    subject = cv2.morphologyEx(np.uint8(image_bgr.min(axis=2) < 232), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    ys, xs = np.where(subject > 0)
    if not len(ys):
        return None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    margin = min(x0, y0, width - x1, height - y1)
    if margin < 3 or margin >= FRAME_MARGIN:
        return None
    pad = 3
    crop = image_bgr[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
    room = min(width, height) - 2 * FRAME_MARGIN
    scale = min(1.0, room / max(crop.shape[:2]))
    if scale < 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    canvas = np.full_like(image_bgr, 255)
    top, left = (height - crop.shape[0]) // 2, (width - crop.shape[1]) // 2
    canvas[top:top + crop.shape[0], left:left + crop.shape[1]] = crop
    return canvas


def finish_level(folder, source=None):
    """Rewrite data.json, map.png, lines.png and original.png in place."""
    folder = Path(folder)
    data = json.loads((folder / 'data.json').read_text())
    level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
    original = cv2.imread(str(folder / 'original.png'), cv2.IMREAD_COLOR)
    if level_map is None or level_map.ndim != 2 or original is None:
        raise ValueError(f'Not a process.py output folder: {folder}')
    palette = list(data['palette'])
    if (level_map == BACKGROUND_ID).sum() == 0:
        raise ValueError('process.py found no background; the picture has no white margin')
    background_bgr = original[level_map == BACKGROUND_ID][0].copy()
    true_lines = level_map == LINE_ID
    before = level_map.copy()

    inked = split = whites = mixed = 0
    art = None
    if source is not None:
        art = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if art is None:
            raise ValueError(f'Cannot read source picture: {source}')
        art = cv2.resize(art, level_map.shape[::-1], interpolation=cv2.INTER_AREA)
        split = split_overmerged(level_map, palette, art)
        palette = true_colors(level_map, palette, art)
        mixed = split_mixed(level_map, palette, art)
        inked = restore_ink(level_map, palette, art)
        whites = reclaim_parts(level_map, palette, art)
    black = redraw_black(level_map, palette, art)
    dashes = drop_dashes(level_map)
    true_lines = level_map == LINE_ID

    shades = merge_shades(level_map, palette)
    merged = merge_lookalikes(level_map, palette)
    trued = keep_true_colors(level_map, palette, art) if art is not None else 0
    sparkles, absorbed = absorb_slivers(level_map, palette)
    if art is not None:
        trued += keep_true_colors(level_map, palette, art)  # absorbing can tip an area's colour too

    # A colour is never repainted as another colour, so the palette may pass the usual limit.
    # Only a colour with next to nothing to paint is dropped: its speck joins the area beside it.
    paintable = max(int((level_map < LINE_ID).sum()), 1)
    for index in range(len(palette)):
        mask = level_map == index
        if not 0 < mask.sum() < SPECK_COLOR_SHARE * paintable:
            continue
        around = np.where(mask | (level_map >= LINE_ID), 0, 1).astype(np.uint8)
        if around.any():
            _, nearest = ndimage.distance_transform_edt(around == 0, return_indices=True)
            level_map[mask] = level_map[nearest[0][mask], nearest[1][mask]]

    # The canvas starts blank. Only the white sparkle in an eye is printed.
    fixed_rgba = np.zeros((*level_map.shape, 4), np.uint8)
    earlier = cv2.imread(str(folder / 'lines.png'), cv2.IMREAD_UNCHANGED)
    if earlier is not None and earlier.ndim == 3 and earlier.shape[2] == 4:
        kept = true_lines & (earlier[..., 3] > 0) & (earlier[..., :3].min(axis=2) > 225)
        fixed_rgba[kept] = earlier[kept]
    enclosed = sparkles
    fixed_rgba[enclosed] = (255, 255, 255, 255)
    level_map[enclosed] = LINE_ID
    # Background a merge has cut off from the outside could never be painted: ink it.
    outside, _ = ndimage.label(level_map == BACKGROUND_ID, structure=EIGHT)
    reachable = np.unique(np.concatenate([outside[0], outside[-1], outside[:, 0], outside[:, -1]]))
    cut_off = (level_map == BACKGROUND_ID) & ~np.isin(outside, reachable[reachable > 0])
    level_map[cut_off] = LINE_ID
    true_lines |= cut_off

    used = [i for i in range(len(palette)) if (level_map == i).any()]
    remap = np.arange(256, dtype=np.uint8)
    for new, old in enumerate(used):
        remap[old] = new
    level_map = remap[level_map]
    new_palette = [palette[i] for i in used]

    if art is not None:
        strokes = detail_strokes(level_map, new_palette, art)
    else:
        # No source picture: keep the strokes an earlier pass printed.
        strokes = np.zeros(level_map.shape, bool)
        if earlier is not None and earlier.ndim == 3 and earlier.shape[2] == 4:
            strokes = (earlier[..., 3] > 0) & (earlier[..., :3].max(axis=2) == 0) & (level_map < LINE_ID)
            strokes &= ~(cv2.dilate(np.uint8(level_map >= LINE_ID), np.ones((9, 9), np.uint8)) > 0)
    stroke_zone = cv2.dilate(np.uint8(strokes), np.ones((5, 5), np.uint8)) > 0

    numbers = []
    for index in range(len(new_palette)):
        mask = level_map == index
        labels, areas, radii, distance = _components(mask)
        # Numbers keep clear of printed strokes where the region has room.
        clear = cv2.distanceTransform(np.uint8(mask & ~stroke_zone), cv2.DIST_L2, 5)
        distance = np.where(ndimage.maximum(clear, labels, np.arange(1, len(areas) + 1))[labels - 1] >= MIN_RADIUS, clear, distance) if len(areas) else distance
        boxes = ndimage.find_objects(labels)
        found = []
        for number in group_leaders(mask, labels, areas, radii):
            box = boxes[number - 1]
            # A narrow region's number shrinks in step with the room it has.
            size = min(10, max(SMALL_SIZE_MIN, int(10 * radii[number - 1] / MIN_RADIUS)))
            x, y = place_label(distance, labels[box] == number, box, index + 1, size / 10)
            label = {'number': index + 1, 'x': x, 'y': y, 'color_index': index}
            if size < 10:
                label['size'] = size
            found.append(label)
        numbers.extend(sorted(found, key=lambda label: (label['y'], label['x'])))

    gradient = cv2.morphologyEx(level_map, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    lines = fixed_rgba.copy()
    lines[even_lines(gradient, true_lines & (fixed_rgba[..., 3] == 0), fixed_rgba[..., 3] > 0)] = (0, 0, 0, 255)
    lines[strokes] = (0, 0, 0, 255)

    picture = original.copy()
    for index, color in enumerate(new_palette):
        r, g, b = _hex_rgb(color)
        picture[level_map == index] = (b, g, r)
    picture[level_map == BACKGROUND_ID] = background_bgr
    printed = lines[..., 3] > 0
    picture[printed] = lines[printed][:, :3]

    preview = picture.copy()
    for label in numbers:
        for color, weight in (((255, 255, 255), 2), ((0, 0, 0), 1)):
            cv2.putText(preview, str(label['number']), (label['x'] - 5, label['y'] + 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, weight)

    data.update(palette=new_palette, numbers=numbers)
    cv2.imwrite(str(folder / 'map.png'), level_map)
    cv2.imwrite(str(folder / 'lines.png'), lines)
    cv2.imwrite(str(folder / 'original.png'), picture)
    cv2.imwrite(str(folder / 'debug_preview.png'), preview)
    (folder / 'data.json').write_text(json.dumps(data, indent=2))
    subject = int((level_map != BACKGROUND_ID).sum())
    return {
        'finish_revision': REVISION,
        'palette_before': len(palette), 'palette_after': len(new_palette),
        'lookalike_colors_merged': merged, 'shade_regions_merged': shades, 'areas_returned_to_art_colour': trued, 'slivers_absorbed': absorbed, 'ink_pixels_restored': inked, 'black_fill_pixels': black, 'dash_pixels_dropped': dashes, 'lost_part_pixels_reclaimed': whites, 'overmerged_colors_split': split, 'mixed_regions_divided': mixed,
        'fixed_detail_pixels': int(enclosed.sum()), 'small_numbers': sum('size' in n for n in numbers),
        'fixed_detail_fraction_of_subject': round(float(enclosed.sum()) / subject, 4) if subject else 0.0,
        'pixels_changed_fraction': round(float((remap[before] != level_map).mean()), 4),
        'numbers': len(numbers),
    }
