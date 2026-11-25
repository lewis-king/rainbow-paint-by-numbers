"""Prove each gate catches the fault it exists for.

    image-processing/venv/bin/python -m unittest discover -s image-processing/generation/tests -v

The checks are exercised on small synthetic pictures, levels and videos with one
deliberate fault each. The last test drives a picture through the whole factory
(real process.py, real finishing pass, real ffmpeg video) with ComfyUI replaced
by files on disk, then tampers with the result to show `verify` notices.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

GENERATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GENERATION))

import checks  # noqa: E402
import factory  # noqa: E402
import finish  # noqa: E402

PALETTE = {'red': (230, 40, 40), 'blue': (40, 90, 230), 'green': (60, 170, 60), 'yellow': (250, 215, 20),
           'purple': (150, 70, 200), 'orange': (245, 140, 20)}
SHAPES = [('red', 'circle', (300, 330, 150)), ('blue', 'rect', (520, 200, 820, 430)),
          ('green', 'circle', (680, 640, 140)), ('yellow', 'rect', (200, 560, 470, 800)),
          ('purple', 'circle', (500, 480, 70)), ('orange', 'rect', (540, 800, 820, 900)),
          ('red', 'rect', (850, 480, 960, 620)), ('blue', 'circle', (140, 900, 70))]


def draw_picture(shapes=SHAPES, background=255, outline=14):
    """A flat cartoon the way the image model is asked to draw one. Returns BGR."""
    picture = np.full((1024, 1024, 3), background, np.uint8)
    for name, kind, geometry in shapes:
        color = PALETTE[name][::-1]
        if kind == 'circle':
            x, y, r = geometry
            cv2.circle(picture, (x, y), r, color, -1, cv2.LINE_AA)
            cv2.circle(picture, (x, y), r, (0, 0, 0), outline, cv2.LINE_AA)
        else:
            x0, y0, x1, y1 = geometry
            cv2.rectangle(picture, (x0, y0), (x1, y1), color, -1)
            cv2.rectangle(picture, (x0, y0), (x1, y1), (0, 0, 0), outline)
    return picture


def write_level(folder, shapes=SHAPES, palette=None, numbers='auto'):
    """A level bundle built directly (no process.py), with every region numbered."""
    folder.mkdir(parents=True, exist_ok=True)
    names = palette or [name for name, _, _ in shapes]
    names = list(dict.fromkeys(names))
    level_map = np.full((1024, 1024), 255, np.uint8)
    for name, kind, geometry in shapes:
        index = names.index(name)
        if kind == 'circle':
            x, y, r = geometry
            cv2.circle(level_map, (x, y), r, 254, -1)
            cv2.circle(level_map, (x, y), max(r - 7, 1), index, -1)
        else:
            x0, y0, x1, y1 = geometry
            cv2.rectangle(level_map, (x0, y0), (x1, y1), 254, -1)
            if x1 - x0 > 14 and y1 - y0 > 14:
                cv2.rectangle(level_map, (x0 + 7, y0 + 7), (x1 - 7, y1 - 7), index, -1)
    cv2.imwrite(str(folder / 'map.png'), level_map)
    data = {'id': folder.name, 'palette': ['#%02x%02x%02x' % PALETTE[name] for name in names], 'numbers': [],
            'dimensions': {'w': 1024, 'h': 1024}, 'has_reward': False, 'background_id': 255, 'line_id': 254}
    (folder / 'data.json').write_text(json.dumps(data))
    cv2.imwrite(str(folder / 'original.png'), np.zeros((1024, 1024, 3), np.uint8))
    cv2.imwrite(str(folder / 'lines.png'), np.zeros((1024, 1024, 4), np.uint8))
    finish_numbers(folder)
    if numbers != 'auto':
        data = json.loads((folder / 'data.json').read_text())
        data['numbers'] = numbers(data['numbers'])
        (folder / 'data.json').write_text(json.dumps(data))
    return folder


def finish_numbers(folder):
    """Number every region and draw the line layer, without altering the map."""
    data = json.loads((folder / 'data.json').read_text())
    level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
    numbers = []
    for index in range(len(data['palette'])):
        labels, areas, _, distance = finish._components(level_map == index)
        for number in range(1, len(areas) + 1):
            ys, xs = np.where(labels == number)
            best = np.argmax(distance[ys, xs])
            numbers.append({'number': index + 1, 'x': int(xs[best]), 'y': int(ys[best]), 'color_index': index})
    lines = np.zeros((1024, 1024, 4), np.uint8)
    lines[level_map == 254] = (0, 0, 0, 255)
    cv2.imwrite(str(folder / 'lines.png'), lines)
    data['numbers'] = numbers
    (folder / 'data.json').write_text(json.dumps(data))


def write_video(path, picture, frames=81, fps=16, motion='sway', size=640):
    """Encode a clip of `picture` with ffmpeg. `motion` selects the fault to plant."""
    base = cv2.resize(picture, (size, size), interpolation=cv2.INTER_AREA)
    encoder = subprocess.Popen(
        ['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{size}x{size}',
         '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], stdin=subprocess.PIPE)
    for index in range(frames):
        frame = base
        phase = np.sin(2 * np.pi * index / frames)
        if motion in ('sway', 'cut', 'darken', 'exit'):
            reach = 150 if motion == 'exit' else 24
            shift = np.float32([[1, 0, reach * phase], [0, 1, 6 * phase]])
            frame = cv2.warpAffine(base, shift, (size, size), borderValue=(255, 255, 255))
        if motion == 'cut' and index > frames // 2:
            frame = cv2.flip(cv2.bitwise_not(frame), 0)
        if motion == 'darken':
            frame = (frame * (1 - 0.5 * index / frames)).astype(np.uint8)
        if motion == 'recolor':
            hsv = cv2.cvtColor(base, cv2.COLOR_BGR2HSV)
            hsv[..., 0] = (hsv[..., 0].astype(int) + index) % 180
            frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        encoder.stdin.write(np.ascontiguousarray(frame).tobytes())
    encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError('ffmpeg failed')


def failures(result):
    return ' | '.join(result['failures'])


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rainbow-factory-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def picture(self, name='picture.png', **kwargs):
        path = self.tmp / name
        cv2.imwrite(str(path), draw_picture(**kwargs))
        return path


class ImageChecks(Scratch):
    def test_clean_picture_passes(self):
        result = checks.check_image(self.picture())
        self.assertEqual(result['verdict'], 'PASS', failures(result))

    def test_wrong_size_fails(self):
        path = self.tmp / 'small.png'
        cv2.imwrite(str(path), cv2.resize(draw_picture(), (768, 768)))
        self.assertIn('1024x1024', failures(checks.check_image(path)))

    def test_grey_background_fails(self):
        self.assertIn('clean white', failures(checks.check_image(self.picture(background=205))))

    def test_cropped_subject_fails(self):
        shapes = SHAPES + [('red', 'circle', (1010, 500, 120))]
        self.assertEqual(checks.check_image(self.picture(shapes=shapes))['verdict'], 'FAIL')

    def test_tiny_subject_fails(self):
        self.assertIn('too small', failures(checks.check_image(self.picture(shapes=[('red', 'circle', (512, 512, 90))]))))

    def test_loose_swatches_around_the_subject_fail(self):
        swatches = [('green', 'circle', (x, y, 45)) for x in (120, 900) for y in (120, 320, 520, 720, 900)]
        self.assertIn('separate pieces', failures(checks.check_image(self.picture(shapes=SHAPES + swatches))))

    def test_shapes_without_outlines_fail(self):
        black = [('black', 'rect', (480, 440, 560, 520))] if 'black' in PALETTE else []
        result = checks.check_image(self.picture(shapes=SHAPES + black, outline=0))
        self.assertIn('without black outlines', failures(result))

    def test_unreadable_file_fails(self):
        path = self.tmp / 'broken.png'
        path.write_bytes(b'not a png')
        self.assertEqual(checks.check_image(path)['verdict'], 'FAIL')


class LevelChecks(Scratch):
    def level(self, **kwargs):
        return write_level(self.tmp / '900', **kwargs)

    def test_clean_level_passes(self):
        result = checks.check_level(self.level(), level_id='900')
        self.assertEqual(result['verdict'], 'PASS', failures(result))
        self.assertEqual(result['metrics']['labels'], 8)

    def test_swatch_with_nothing_to_paint_fails(self):
        folder = self.level(palette=[name for name, _, _ in SHAPES] + ['red'])
        data = json.loads((folder / 'data.json').read_text())
        data['palette'].append('#00ffff')
        (folder / 'data.json').write_text(json.dumps(data))
        self.assertIn('nothing to paint', failures(checks.check_level(folder)))

    def test_number_on_the_wrong_colour_fails(self):
        def move(numbers):
            other = next(n for n in numbers if n['color_index'] != numbers[0]['color_index'])
            numbers[0]['x'], numbers[0]['y'] = other['x'], other['y']
            return numbers
        self.assertIn('different colour', failures(checks.check_level(self.level(numbers=move))))

    def test_region_without_a_number_fails(self):
        result = checks.check_level(self.level(numbers=lambda numbers: numbers[1:] + [dict(numbers[1])]))
        self.assertIn('no number', failures(result))

    def test_number_in_a_sliver_fails(self):
        shapes = SHAPES + [('red', 'rect', (860, 300, 884, 700))]
        self.assertIn('region edge', failures(checks.check_level(self.level(shapes=shapes))))

    def test_lookalike_colours_fail(self):
        PALETTE['red2'] = (224, 46, 44)
        self.addCleanup(PALETTE.pop, 'red2')
        shapes = SHAPES + [('red2', 'circle', (880, 520, 60))]
        self.assertIn('look the same', failures(checks.check_level(self.level(shapes=shapes))))

    def test_too_few_colours_fail(self):
        self.assertIn('colours', failures(checks.check_level(self.level(shapes=SHAPES[:3] + [('red', 'circle', (500, 480, 70))] * 6))))

    def test_subject_touching_the_edge_fails(self):
        shapes = SHAPES + [('red', 'circle', (1000, 500, 100))]
        self.assertIn('touches the edge', failures(checks.check_level(self.level(shapes=shapes))))

    def test_enclosed_background_fails(self):
        folder = self.level()
        level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
        level_map[380:400, 230:250] = 255
        cv2.imwrite(str(folder / 'map.png'), level_map)
        self.assertIn('enclosed background', failures(checks.check_level(folder)))

    def test_numbers_drawn_on_top_of_each_other_fail(self):
        def stack(numbers):
            numbers.append(dict(numbers[0], x=numbers[0]['x'] + 4))
            return numbers
        self.assertIn('on top of each other', failures(checks.check_level(self.level(numbers=stack))))

    def test_index_outside_palette_fails(self):
        folder = self.level()
        level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
        level_map[300:320, 300:320] = 40
        cv2.imwrite(str(folder / 'map.png'), level_map)
        self.assertIn('outside the palette', failures(checks.check_level(folder)))

    def test_wrong_level_id_and_missing_reward_fail(self):
        result = checks.check_level(self.level(), level_id='901', require_reward=True)
        self.assertIn('is not level 901', failures(result))
        self.assertIn('no reward video', failures(result))

    def test_missing_file_fails(self):
        folder = self.level()
        (folder / 'lines.png').unlink()
        self.assertIn('lines.png', failures(checks.check_level(folder)))


class FinishingSteps(unittest.TestCase):
    """The finishing pass one step at a time, on small hand-drawn maps."""
    PALETTE = ['#2e9e3c', '#ffd21f', '#1f7a2e', '#e03a2e', '#3a6fe0', '#101010']
    GREEN, YELLOW, DARK_GREEN, RED, BLUE, BLACK = range(6)

    def egg(self):
        level_map = np.full((400, 400), 255, np.uint8)
        cv2.circle(level_map, (200, 200), 150, 254, -1)
        cv2.circle(level_map, (200, 200), 140, self.GREEN, -1)
        return level_map

    def test_thin_stripe_stays_an_area_to_paint(self):
        level_map = self.egg()
        level_map[190:198, 80:320] = self.YELLOW            # a stripe far too thin for a full-size number
        sparkles, absorbed = finish.absorb_slivers(level_map, self.PALETTE)
        self.assertEqual(absorbed, 0)
        self.assertEqual(level_map[194, 200], self.YELLOW)  # the child paints it; nothing is printed
        self.assertFalse(sparkles.any())

    def test_fringe_is_absorbed_without_a_trace(self):
        level_map = self.egg()
        ring = cv2.circle(np.zeros((400, 400), np.uint8), (200, 200), 138, 1, 3) > 0
        level_map[ring] = self.DARK_GREEN                   # anti-aliased edge, 3 px wide
        sparkles, _ = finish.absorb_slivers(level_map, self.PALETTE)
        self.assertFalse((level_map == self.DARK_GREEN).any())
        self.assertFalse(sparkles.any())

    def test_only_a_white_sparkle_is_printed(self):
        palette = self.PALETTE + ['#fafafa']
        level_map = self.egg()
        cv2.circle(level_map, (150, 200), 20, 254, -1)
        cv2.circle(level_map, (150, 200), 8, 6, -1)         # white sparkle in a black pupil
        cv2.circle(level_map, (250, 200), 20, 254, -1)
        cv2.circle(level_map, (250, 200), 8, self.RED, -1)  # a red dot ringed with ink
        sparkles, _ = finish.absorb_slivers(level_map, palette)
        self.assertTrue(sparkles[200, 150])
        self.assertFalse(sparkles[200, 250])
        self.assertEqual(level_map[200, 250], self.RED)     # still an area to paint

    def test_long_narrow_band_keeps_a_small_number(self):
        level_map = np.full((400, 400), 255, np.uint8)
        level_map[100:300, 40:360] = 254
        level_map[110:290, 50:350] = self.BLUE
        level_map[150:166, 50:350] = self.YELLOW            # 16 px band: 300 x 16 = 4800 px
        level_map[149, 50:350] = level_map[166, 50:350] = 254
        sparkles, absorbed = finish.absorb_slivers(level_map, self.PALETTE)
        self.assertEqual(absorbed, 0)
        self.assertFalse(sparkles.any())
        self.assertEqual(level_map[158, 200], self.YELLOW)

    def test_small_piece_is_painted_by_the_child_not_printed(self):
        level_map = np.full((400, 400), 255, np.uint8)
        level_map[100:300, 40:360] = 254
        level_map[110:290, 50:350] = self.BLUE
        level_map[150:166, 60:120] = self.YELLOW            # a tassel: 60 x 16
        level_map[200:204, 60:120] = self.RED               # 4 px: a fringe, too thin to be a detail
        finish.absorb_slivers(level_map, self.PALETTE)
        self.assertEqual(level_map[158, 90], self.YELLOW)
        self.assertEqual(level_map[202, 90], self.BLUE)

    def test_two_slivers_cannot_trade_colours_forever(self):
        level_map = np.full((200, 200), 255, np.uint8)
        level_map[40:160, 40:160] = 254
        level_map[50:60, 50:150] = self.GREEN
        level_map[62:72, 50:150] = self.GREEN               # its own colour across a thin line
        finish.absorb_slivers(level_map, self.PALETTE)  # must return

    def test_shadow_joins_the_object_it_falls_on(self):
        level_map = self.egg()
        cv2.ellipse(level_map, (200, 290), (90, 35), 0, 0, 360, self.DARK_GREEN, -1)
        self.assertEqual(finish.merge_shades(level_map, self.PALETTE), 1)
        self.assertFalse((level_map == self.DARK_GREEN).any())

    def test_other_hues_and_outlined_parts_are_not_shades(self):
        level_map = self.egg()
        cv2.circle(level_map, (200, 200), 50, self.YELLOW, -1)        # a different hue, no line
        cv2.circle(level_map, (200, 300), 30, 254, -1)
        cv2.circle(level_map, (200, 300), 24, self.DARK_GREEN, -1)    # same hue, but outlined
        self.assertEqual(finish.merge_shades(level_map, self.PALETTE), 0)

    def test_an_area_carried_to_the_wrong_colour_returns_to_the_art(self):
        level_map = np.full((400, 400), 255, np.uint8)
        level_map[40:360, 40:360] = 254
        level_map[50:190, 50:350] = self.GREEN
        level_map[210:350, 50:350] = self.GREEN             # a merge painted this one green too
        art = np.full((400, 400, 3), 255, np.uint8)
        art[50:190, 50:350] = (0x3c, 0x9e, 0x2e)            # BGR of the green
        art[210:350, 50:350] = (0x80, 0x30, 0xa0)           # the picture shows purple here
        palette = list(self.PALETTE)
        self.assertEqual(finish.keep_true_colors(level_map, palette, art), 1)
        self.assertEqual(level_map[100, 200], self.GREEN)
        self.assertEqual(palette[level_map[300, 200]], '#a03080')

    def test_two_flat_colours_in_one_region_are_divided(self):
        level_map = np.full((400, 400), 255, np.uint8)
        level_map[40:360, 40:360] = 254
        level_map[50:350, 50:350] = self.GREEN              # process.py made one region of it
        art = np.full((400, 400, 3), 255, np.uint8)
        art[50:350, 50:350] = (0x3c, 0x9e, 0x2e)
        art[250:350, 50:350] = (0xc8, 0x8c, 0xf0)           # the picture shows a pink part, with no line
        art[100:104, 60:340] = (0xc8, 0x8c, 0xf0)           # and a pink streak far too thin to matter
        palette = list(self.PALETTE)
        self.assertEqual(finish.split_mixed(level_map, palette, art), 1)
        self.assertEqual(level_map[150, 200], self.GREEN)
        self.assertEqual(level_map[102, 200], self.GREEN)
        self.assertEqual(palette[level_map[300, 200]], '#f08cc8')

    def test_soft_shading_does_not_divide_a_region(self):
        level_map = np.full((400, 400), 255, np.uint8)
        level_map[40:360, 40:360] = 254
        level_map[50:350, 50:350] = self.GREEN
        art = np.full((400, 400, 3), 255, np.uint8)
        ramp = np.linspace(0.5, 1.5, 300)[:, None, None] * np.array([0x3c, 0x9e, 0x2e])
        art[50:350, 50:350] = np.clip(np.broadcast_to(ramp, (300, 300, 3)), 0, 255)
        self.assertEqual(finish.split_mixed(level_map, list(self.PALETTE), art), 0)

    def test_a_pale_part_taken_for_paper_is_given_back(self):
        art = np.full((400, 400, 3), 255, np.uint8)
        cv2.circle(art, (200, 200), 150, (0x3c, 0x9e, 0x2e), -1)
        cv2.circle(art, (200, 260), 60, (0xcb, 0xf3, 0xfe), -1)    # a cream tummy, no outline to speak of
        level_map = np.full((400, 400), 255, np.uint8)
        cv2.circle(level_map, (200, 200), 150, self.GREEN, -1)
        cv2.circle(level_map, (200, 260), 60, 255, -1)             # process.py called it background
        self.assertGreater(checks.lost_parts(art, level_map).sum(), 1500)
        palette = list(self.PALETTE)
        self.assertGreater(finish.reclaim_parts(level_map, palette, art), 9000)
        self.assertEqual(palette[level_map[260, 200]], '#fef3cb')
        self.assertEqual(level_map[5, 5], 255)                     # the page itself is untouched
        self.assertFalse(checks.lost_parts(art, level_map).any())

    def test_tinted_paper_is_not_a_lost_part(self):
        art = np.full((400, 400, 3), (200, 225, 235), np.uint8)    # the whole page is cream
        cv2.circle(art, (200, 200), 100, (0x3c, 0x9e, 0x2e), -1)
        level_map = np.full((400, 400), 255, np.uint8)
        cv2.circle(level_map, (200, 200), 100, self.GREEN, -1)
        self.assertFalse(checks.lost_parts(art, level_map).any())

    def test_neighbours_of_one_colour_share_a_number(self):
        mask = np.zeros((300, 300), bool)
        mask[20:80, 20:80] = mask[20:80, 90:170] = True     # two petals a line apart
        mask[200:260, 200:260] = True                       # one far away
        labels, areas, radii, _ = finish._components(mask)
        leaders = finish.group_leaders(mask, labels, areas, radii)
        self.assertEqual(len(leaders), 2)
        self.assertIn(int(labels[50, 130]), leaders)        # the bigger petal carries the number
        self.assertNotIn(int(labels[50, 50]), leaders)

    def test_heavy_lines_are_not_thickened_again(self):
        ink = np.zeros((200, 200), bool)
        ink[95:105, 20:180] = True                          # a 10 px line the artist drew
        level_map = np.where(ink, 254, 0).astype(np.uint8)
        boundaries = cv2.morphologyEx(level_map, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        black = finish.even_lines(boundaries, ink, np.zeros_like(ink))
        self.assertLessEqual(int(black[:, 100].sum()), 12)

    def test_bare_boundaries_get_a_steady_line(self):
        level_map = np.zeros((200, 200), np.uint8)
        level_map[:, 100:] = 1                              # two colours meeting with no ink
        boundaries = cv2.morphologyEx(level_map, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        black = finish.even_lines(boundaries, np.zeros((200, 200), bool), np.zeros((200, 200), bool))
        self.assertGreaterEqual(int(black[100].sum()), finish.LINE_WEIGHT)

    def test_small_number_is_checked_at_its_own_size(self):
        big = {'number': 3, 'x': 100, 'y': 100}
        small = dict(big, size=5)
        wide = lambda box: box[2] - box[0]
        self.assertAlmostEqual(wide(checks._glyph_box(small)) / wide(checks._glyph_box(big)), 0.5, delta=0.1)
        self.assertEqual(checks._label_scale(big), 1.0)


class FinishingPass(Scratch):
    def raw_level(self):
        """What process.py tends to emit: fringes, a dead swatch, a look-alike, a tiny highlight."""
        PALETTE.update(fringe=(120, 30, 30), red2=(224, 46, 44), white=(250, 250, 250), unused=(10, 200, 200))
        self.addCleanup(lambda: [PALETTE.pop(k) for k in ('fringe', 'red2', 'white', 'unused')])
        names = ['unused'] + [name for name, _, _ in SHAPES] + ['fringe', 'red2', 'white']
        folder = write_level(self.tmp / '900', palette=names)
        level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
        red, fringe, red2, white = (names.index(n) for n in ('red', 'fringe', 'red2', 'white'))
        ring = cv2.circle(np.zeros_like(level_map), (300, 330), 141, 1, 5) > 0
        level_map[ring & (level_map == red)] = fringe          # anti-aliased edge inside the red circle
        level_map[330:420, 250:350][level_map[330:420, 250:350] == red] = red2  # shading patch
        cv2.circle(level_map, (680, 640), 16, 254, -1)          # outlined eye highlight
        cv2.circle(level_map, (680, 640), 9, white, -1)
        cv2.imwrite(str(folder / 'map.png'), level_map)
        data = json.loads((folder / 'data.json').read_text())
        data['palette'] = ['#%02x%02x%02x' % PALETTE[name] for name in names]
        (folder / 'data.json').write_text(json.dumps(data))
        finish_numbers(folder)
        return folder

    def test_raw_output_fails_then_finished_output_passes(self):
        folder = self.raw_level()
        before = checks.check_level(folder)
        self.assertEqual(before['verdict'], 'FAIL')
        stats = finish.finish_level(folder)
        after = checks.check_level(folder)
        self.assertEqual(after['verdict'], 'PASS', failures(after))
        self.assertEqual(stats['palette_after'], 6)
        self.assertEqual(after['metrics']['labels'], 8)
        self.assertEqual(after['metrics']['dead_colors'], [])

    def test_eye_sparkle_shows_the_canvas_and_is_never_printed(self):
        folder = self.raw_level()
        finish.finish_level(folder)
        level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
        lines = cv2.imread(str(folder / 'lines.png'), cv2.IMREAD_UNCHANGED)
        self.assertEqual(level_map[640, 680], 254)             # not an area to paint
        self.assertEqual(lines[640, 680, 3], 0)                # a hole in the ink, not white paint
        opaque = lines[..., 3] > 0
        self.assertEqual(int(lines[opaque][:, :3].max()), 0)   # everything printed is black
        painted = cv2.imread(str(folder / 'original.png'))
        self.assertEqual(painted[640, 680].tolist(), [255, 255, 255])   # white in the finished picture

    def test_finishing_is_deterministic_and_idempotent(self):
        first = self.raw_level()
        second = self.tmp / 'copy' / '900'
        shutil.copytree(first, second)
        finish.finish_level(first)
        finish.finish_level(second)
        for name in ('map.png', 'lines.png', 'original.png', 'data.json'):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
        once = factory.playable_sha(first)
        finish.finish_level(first)
        self.assertEqual(factory.playable_sha(first), once)

    def test_no_background_is_an_error(self):
        folder = write_level(self.tmp / '900')
        level_map = cv2.imread(str(folder / 'map.png'), cv2.IMREAD_UNCHANGED)
        level_map[level_map == 255] = 0
        cv2.imwrite(str(folder / 'map.png'), level_map)
        with self.assertRaises(ValueError):
            finish.finish_level(folder)


class VideoChecks(Scratch):
    def clip(self, **kwargs):
        path = self.tmp / 'clip.mp4'
        write_video(path, draw_picture(), **kwargs)
        return checks.check_video(path, self.picture())

    def test_gentle_motion_passes(self):
        result = self.clip()
        self.assertEqual(result['verdict'], 'PASS', failures(result))

    def test_still_image_fails(self):
        self.assertIn('Hardly anything moves', failures(self.clip(motion='still')))

    def test_cut_fails(self):
        self.assertIn('sudden jump', failures(self.clip(motion='cut')))

    def test_darkening_background_fails(self):
        self.assertIn('does not stay white', failures(self.clip(motion='darken')))

    def test_subject_leaving_the_frame_fails(self):
        self.assertIn('leaves the frame', failures(self.clip(motion='exit')))

    def test_recolouring_fails(self):
        self.assertIn('Colours change', failures(self.clip(motion='recolor')))

    def test_wrong_length_fails(self):
        self.assertIn('lasts', failures(self.clip(frames=32)))

    def test_video_of_another_picture_fails(self):
        path = self.tmp / 'clip.mp4'
        write_video(path, draw_picture(shapes=SHAPES[:2]))
        self.assertIn('First frame', failures(checks.check_video(path, self.picture())))

    def test_not_a_video_fails(self):
        path = self.tmp / 'clip.mp4'
        path.write_bytes(b'nope')
        self.assertEqual(checks.check_video(path, self.picture())['verdict'], 'FAIL')


class FactoryGates(Scratch):
    """The whole line, with ComfyUI replaced by files placed where it would put them."""

    def setUp(self):
        super().setUp()
        repo = self.tmp / 'repo'
        (repo / 'levels').mkdir(parents=True)
        (repo / 'level-loader.ts').write_text("const levelRegistry = {\n};\n\nexport const LEVEL_IDS = [];\n")
        (repo / 'catalog.json').write_text('{}\n')
        recipe = {'id': '900', 'slug': 'shapes', 'title': 'Shapes', 'category': 'toys', 'kind': 'object', 'factory': 1,
                  'seed': 1, 'image_prompt': 'shapes', 'video_prompt': 'shapes sway'}
        (repo / 'manifest.json').write_text(json.dumps({'levels': [recipe]}))
        (repo / 'source-index.json').write_text('[]\n')
        replaced = {'RUNS': repo / 'runs', 'SOURCES': repo / 'sources', 'LEVELS': repo / 'levels',
                    'LOADER': repo / 'level-loader.ts', 'CATALOG': repo / 'catalog.json',
                    'MANIFEST': repo / 'manifest.json', 'RAW': repo / 'raw', 'APP_ASSETS': repo / 'app',
                    'INDEX': repo / 'source-index.json', 'REFINISHED': repo / 'refinished.json',
                    'LEGACY': repo / 'legacy'}
        for name, value in replaced.items():
            self.addCleanup(setattr, factory, name, getattr(factory, name))
            setattr(factory, name, value)
        (repo / 'sources').mkdir()
        (repo / 'raw').mkdir()
        self.repo = repo
        self.manifest = factory.load_manifest()
        self.level = factory.Level(self.manifest['levels'][0])
        self.level.run.mkdir(parents=True)

    def generate(self, stage, **kwargs):
        """Stand in for ComfyUI: drop the output and the receipt the factory writes on collect."""
        if stage == 'image':
            cv2.imwrite(str(self.level.image), draw_picture(**kwargs))
        else:
            write_video(self.level.video, cv2.imread(str(self.level.image)), **kwargs)
        graph = self.level.graph(stage)
        factory.save_json(self.level.run / f'{stage}.api.json', graph)
        factory.save_json(self.level.run / f'{stage}-job.json', {
            'id': '900', 'stage': stage, 'prompt_id': 'test', 'status': 'completed',
            'graph_sha256': factory.sha_json(graph), 'sha256': factory.sha(self.level.artifact(stage))})

    def approve(self, stage):
        factory.review(self.level, stage, 'PASS', 'test', ['looked at the sheet'])

    def test_full_line_then_tampering_is_caught(self):
        level = self.level
        with self.assertRaises(factory.Blocked):
            factory.integrate(level)

        self.generate('image')
        with self.assertRaisesRegex(factory.Blocked, 'check image'):
            self.approve('image')                      # no review before the measured checks
        ok, why = factory.check_image(level)
        self.assertTrue(ok, why)
        self.assertTrue((level.run / 'review-image.jpg').is_file())
        with self.assertRaisesRegex(factory.Blocked, 'visual review'):
            level.image_gate()
        with self.assertRaises(factory.Blocked):
            factory.review(level, 'image', 'PASS', 'test', [])   # a review must say what was seen
        self.approve('image')
        level.image_gate()

        with self.assertRaisesRegex(factory.Blocked, 'not generated'):
            factory.integrate(level)                   # no video yet
        self.generate('video')
        with self.assertRaisesRegex(factory.Blocked, 'check video'):
            factory.integrate(level)
        ok, why = factory.check_video(level)
        self.assertTrue(ok, why)
        with self.assertRaisesRegex(factory.Blocked, 'visual review'):
            factory.integrate(level)
        self.approve('video')
        self.assertEqual(level.status(), 'ready to integrate')

        factory.integrate(level)
        self.assertEqual(level.status(), 'integrated')
        for name in factory.BUNDLE:
            self.assertTrue((factory.LEVELS / '900' / name).is_file(), name)
        self.assertIn(factory.loader_entry('900'), factory.LOADER.read_text())
        self.assertEqual(json.loads(factory.CATALOG.read_text())['900'], {'title': 'Shapes', 'category': 'toys'})
        self.assertTrue(json.loads((factory.LEVELS / '900' / 'data.json').read_text())['has_reward'])
        self.assertTrue(factory.verify())
        factory.integrate(level)                       # repeating is harmless
        self.assertEqual(factory.LOADER.read_text().count("'900'"), 1)

        data = factory.LEVELS / '900' / 'data.json'
        original = data.read_text()
        data.write_text(original.replace('"number": 1', '"number": 2', 1))
        self.assertFalse(factory.verify())             # a hand-edited level is noticed
        data.write_text(original)
        self.assertTrue(factory.verify())
        loader = factory.LOADER.read_text()
        factory.LOADER.write_text(loader.replace(factory.loader_entry('900'), ''))
        self.assertFalse(factory.verify())             # so is an unregistered one

    def test_changed_picture_revokes_approval(self):
        self.generate('image')
        factory.check_image(self.level)
        self.approve('image')
        self.level.image_gate()
        cv2.imwrite(str(self.level.image), draw_picture(shapes=SHAPES[:5] + [('orange', 'circle', (680, 860, 60))] + SHAPES[6:]))
        with self.assertRaisesRegex(factory.Blocked, 'changed after generation'):
            self.level.image_gate()

    def test_changed_recipe_revokes_generation(self):
        self.generate('image')
        self.assertTrue(self.level.generated('image'))
        self.level.recipe['image_prompt'] = 'different shapes'
        self.assertFalse(self.level.generated('image'))
        with self.assertRaisesRegex(factory.Blocked, 'retry'):
            factory.prepare(self.level, 'image')

    def test_a_job_record_is_never_overwritten(self):
        self.generate('image')
        before = (self.level.run / 'image-job.json').read_text()
        with self.assertRaisesRegex(factory.Blocked, 'already recorded'):
            factory.record(self.level, 'image', 'second-submission')
        self.assertEqual((self.level.run / 'image-job.json').read_text(), before)

    def test_failed_checks_cannot_be_reviewed_through(self):
        self.generate('image', shapes=[('red', 'circle', (512, 512, 300))])
        ok, why = factory.check_image(self.level)
        self.assertFalse(ok)
        with self.assertRaisesRegex(factory.Blocked, 'cannot override'):
            self.approve('image')
        factory.review(self.level, 'image', 'FAIL', 'test', ['one colour'])
        with self.assertRaises(factory.Blocked):
            self.level.image_gate()

    def test_bad_video_blocks_integration_and_retry_archives_it(self):
        self.generate('image')
        factory.check_image(self.level)
        self.approve('image')
        self.generate('video', motion='still')
        ok, why = factory.check_video(self.level)
        self.assertFalse(ok)
        with self.assertRaisesRegex(factory.Blocked, 'video check failed'):
            factory.integrate(self.level)
        factory.retry(self.manifest, self.level, 'video', None, 'static')
        self.assertFalse(self.level.video.exists())
        self.assertTrue((self.level.run / 'attempts' / '01-video' / 'video.mp4').is_file())
        saved = json.loads(factory.MANIFEST.read_text())['levels'][0]
        self.assertEqual(saved['video_seed'], 1001)
        self.assertEqual(saved['history'][0]['reason'], 'static')
        self.level.image_gate()                        # the approved picture survives a video retry
        factory.retry(self.manifest, self.level, 'image', None, 'start again')
        self.assertFalse(self.level.image.exists())
        self.assertEqual(json.loads(factory.MANIFEST.read_text())['levels'][0]['seed'], 1001)

    def test_refuses_to_overwrite_a_shipped_level(self):
        self.generate('image')
        factory.check_image(self.level)
        self.approve('image')
        self.generate('video')
        factory.check_video(self.level)
        self.approve('video')
        (factory.LEVELS / '900').mkdir()
        (factory.LEVELS / '900' / 'data.json').write_text('{}')
        with self.assertRaisesRegex(factory.Blocked, 'refusing to overwrite'):
            factory.integrate(self.level)

    def ship(self):
        self.generate('image')
        factory.check_image(self.level)
        self.approve('image')
        self.generate('video')
        factory.check_video(self.level)
        self.approve('video')
        factory.integrate(self.level)

    def test_replace_swaps_an_unreleased_factory_level(self):
        self.ship()
        first = factory.sha(factory.LEVELS / '900' / 'map.png')
        factory.retry(self.manifest, self.level, 'image', None, 'new style')
        self.assertNotEqual(self.level.status(), 'integrated')
        moved = SHAPES[:5] + [('orange', 'circle', (680, 860, 60))] + SHAPES[6:]
        self.generate('image', shapes=moved)
        ok, why = factory.check_image(self.level)
        self.assertTrue(ok, why)
        self.approve('image')
        self.generate('video')
        factory.check_video(self.level)
        self.approve('video')
        with self.assertRaisesRegex(factory.Blocked, '--replace'):
            factory.integrate(self.level)              # never by accident
        self.assertEqual(factory.sha(factory.LEVELS / '900' / 'map.png'), first)
        factory.integrate(self.level, replace=True)
        self.assertNotEqual(factory.sha(factory.LEVELS / '900' / 'map.png'), first)
        self.assertEqual(self.level.status(), 'integrated')
        self.assertEqual(factory.LOADER.read_text().count("'900'"), 1)
        self.assertTrue(factory.verify())

    def test_replace_never_touches_a_level_made_elsewhere(self):
        self.generate('image')
        factory.check_image(self.level)
        self.approve('image')
        self.generate('video')
        factory.check_video(self.level)
        self.approve('video')
        (factory.LEVELS / '900').mkdir()
        (factory.LEVELS / '900' / 'data.json').write_text('{}')
        with self.assertRaisesRegex(factory.Blocked, 'refusing to overwrite'):
            factory.integrate(self.level, replace=True)

    def test_refinish_cleans_an_older_level_and_verify_watches_it(self):
        folder = factory.LEVELS / '7'
        write_level(folder)
        data = json.loads((folder / 'data.json').read_text())
        data['id'] = '7'
        (folder / 'data.json').write_text(json.dumps(data))
        picture = draw_picture()
        cv2.imwrite(str(factory.RAW / '7.png'), picture)
        write_video(folder / 'reward.mp4', picture)
        factory.LOADER.write_text(factory.LOADER.read_text().replace('};', "  '7': {\n  },\n};", 1))
        factory.CATALOG.write_text(json.dumps({'7': {'title': 'Old shapes', 'category': 'toys'}}))
        reward = factory.sha(folder / 'reward.mp4')

        saved = factory.refinish('7')
        self.assertEqual(saved['finish_revision'], factory.finish.REVISION)
        self.assertEqual(factory.sha(folder / 'reward.mp4'), reward)   # the reward is left alone
        self.assertTrue(factory.verify())
        files = dict(saved['files'])
        self.assertEqual(factory.refinish('7')['files'], files)        # repeating changes nothing
        (folder / 'data.json').write_text(json.dumps(dict(data, palette=['#000000'])))
        self.assertFalse(factory.verify())                             # a later hand edit is noticed

    def test_refinish_leaves_factory_levels_to_the_factory(self):
        self.ship()
        with self.assertRaisesRegex(factory.Blocked, 'factory level'):
            factory.refinish('900')

    def reviewer_says(self, answer):
        self.addCleanup(setattr, factory, 'ask_reviewer', factory.ask_reviewer)
        factory.ask_reviewer = lambda views, prompt, model, keep_loaded=True: answer

    def answer(self, verdict, failing=()):
        count = len(factory.REVIEW_CHECKLIST['image'])
        return json.dumps({'verdict': verdict, 'summary': 'looked', 'items': [
            {'check': n, 'pass': n not in failing, 'seen': 'a shape'} for n in range(1, count + 1)]})

    def test_local_reviewer_passes_only_on_a_complete_clean_answer(self):
        self.generate('image')
        factory.check_image(self.level)
        self.reviewer_says(self.answer('PASS', failing=(3,)))        # says PASS but lists a fault
        self.assertEqual(factory.auto_review(self.level, 'image'), 'UNSURE')
        self.assertIsNone(self.level.review('image'))                # nothing recorded; a person looks
        self.reviewer_says('I think it looks nice')
        self.assertEqual(factory.auto_review(self.level, 'image'), 'UNSURE')
        self.reviewer_says(self.answer('PASS'))
        self.assertEqual(factory.auto_review(self.level, 'image'), 'PASS')
        self.assertTrue(self.level.review('image')['reviewer'].startswith('ollama:'))
        self.level.image_gate()

    def test_local_reviewer_rejection_closes_the_gate(self):
        self.generate('image')
        factory.check_image(self.level)
        self.reviewer_says(self.answer('FAIL', failing=(2,)))
        self.assertEqual(factory.auto_review(self.level, 'image'), 'FAIL')
        with self.assertRaisesRegex(factory.Blocked, 'rejected in review'):
            self.level.image_gate()

    def test_local_reviewer_never_sees_a_picture_that_failed_its_checks(self):
        self.generate('image', shapes=[('red', 'circle', (512, 512, 300))])
        factory.check_image(self.level)
        self.reviewer_says(self.answer('PASS'))
        with self.assertRaisesRegex(factory.Blocked, 'measured checks'):
            factory.auto_review(self.level, 'image')

    def test_manifest_rejects_duplicate_titles_and_bad_recipes(self):
        factory.CATALOG.write_text(json.dumps({'7': {'title': 'Shapes', 'category': 'toys'}}))
        with self.assertRaisesRegex(ValueError, 'already has a picture'):
            factory.load_manifest()
        factory.CATALOG.write_text('{}')
        manifest = json.loads(factory.MANIFEST.read_text())
        manifest['levels'][0]['kind'] = 'robot'
        factory.MANIFEST.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'kind must be'):
            factory.load_manifest()


if __name__ == '__main__':
    unittest.main()
