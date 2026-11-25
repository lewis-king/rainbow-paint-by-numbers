# Level factory

Everything that turns an idea ("a kitten with a ball of wool") into a playable
level lives here, with the code. One command line drives it: `factory.py`.

```bash
cd image-processing
venv/bin/python generation/factory.py status
```

## What a level goes through

| Step | Command | What happens |
|---|---|---|
| Recipe | `add --title Kitten --category animals --kind animal --subject "..." --motion "..."` | Writes the prompts, seed and next free id into `manifest.json`. Refuses a title the game already has |
| Picture | `submit image 59` then `collect image 59` | Qwen-Image 2.1 on the local ComfyUI. A subject drawn too close to the edge is shrunk onto a white margin; the untouched output is kept as `image-as-generated.png` |
| Checks | `check image 59` | Source checks, then builds the numbered level (`process.py` + `finish.py`) and measures how it plays. Writes `review-image.jpg` |
| Review | `review 59 image PASS --reviewer "..." --note "..."` | A person or a vision model looks at the sheet. The verdict is tied to the exact files |
| Reward | `submit video 59`, `collect video 59`, `check video 59`, `review 59 video PASS ...` | Wan 2.2 image-to-video from the approved picture, measured, then reviewed from `review-video.jpg` |
| Into the app | `integrate 59` | Rebuilds from the approved files, re-runs every check, copies the level to `assets/images/levels/`, registers it in `utils/level-loader.ts` and `utils/picture-catalog.json`, and saves the full record in `sources/59/` |
| Proof | `verify` | Recomputes every check and hash for every factory-made level from the committed files |

`run 59-68 --wait-gpu 30` does all of that for each level until it reaches a
review, then stops and says which sheet to look at. Ids are a list (`59 61`) or
a range (`59-68`).

Other commands: `retry ID image|video --reason "..."` archives an attempt under
`runs/ID/attempts/` and moves to a new seed (`--subject`/`--motion` rewrite the
recipe, `--keep-seed` repeats it). `cancel` takes this factory's unfinished
jobs off ComfyUI and frees the GPU without touching anyone else's. `audit`
runs the playability checks over any shipped level.

`integrate --replace 59` swaps a factory level already in the app for a newer
attempt, after the same checks and reviews. Use it only before the level is
released, because the picture itself changes. It never touches a level the
factory did not make.

`refinish 1-58` runs the current finishing pass over the levels made before
the factory. It starts from each level as `process.py` first made it, kept in
`legacy/ID/`, and the picture in `raw_assets/`, so a rerun never builds on an
earlier pass. The art,
title and reward stay. Check results are written to `refinished.json` with the
file hashes, and `verify` fails if one of those levels is edited afterwards.
Failures are recorded and not enforced: those pictures are simplified as far as
the art allows, and some keep more than 12 colours. Saved progress survives,
because the game stores which pixels were painted and reads their colour from
the new map. Run it again whenever `finish.py` gets a new `REVISION`.

`gallery` writes `gallery.html` next to this file: every level in the app in a
row of picture, lines with numbers as the game draws them, and the reward
playing. Open it in a browser to vet the whole set by eye. It links to the
assets in the repo, so run it again after adding levels.

### Using the comfy MCP instead of `submit`

`submit` posts the graph to ComfyUI over HTTP. To queue through the comfy MCP:

1. `prepare image 59` prints the path of the exact API graph.
2. `run_workflow(workflow_path=..., wait=False)` in the MCP returns a `prompt_id`.
3. `record image 59 PROMPT_ID`, then `collect image 59` as usual.

Both routes use the same graphs from `build_workflows.py`.

## The gates

Nothing reaches `assets/images/levels/` unless all of these hold at the moment
of `integrate`, which measures everything again instead of trusting saved reports.

**Measured (`checks.py`).** Limits are in `LIMITS` at the top of the file.

- Picture: 1024x1024, clean white edges, subject not cropped, not tiny, no
  drawn frame, no loose swatches or confetti around the subject, black
  outlines around the shapes, enough colour.
- Level: 5 to 12 colours and 8 to 50 numbers; every palette swatch has
  something to paint; no two colours look alike; every group of same-colour
  neighbours has a number, inside an area, clear of the outline, not on top
  of another number; at most 40% of numbers on areas too small to hold them;
  no unpaintable background pockets; white parts stay paintable; each colour
  matches the art it paints; printed detail stays under 1% of the picture.
- Video: H.264 yuv420p, square, 4 to 6.5 s, under 1.6 MB; first frame is the
  finished picture; something moves; no cut or flash; background stays white;
  subject stays in frame; colours and outlines hold.

**Seen (`review`).** The checks cannot tell a cute fox from a malformed one, a
face on a flower, or a stray blob. The review checklist in `factory.py` covers
those, and the sheets show the source, the unpainted picture as the phone draws
it (3x and true size), the painted result, the palette, and 15 video frames.
A review cannot pass a level whose measured checks failed.

**Bound to the files.** Checks and reviews record SHA-256 hashes of the picture,
the numbered level and the video. Change any of them, or the prompt or seed,
and the gates that depended on it close again. Job records are write-once and
levels are locked per process, so two factory runs cannot trample each other.

## `process.py` and `finish.py`

`process.py` is unchanged and still decides the colours, outlines and look.
Measured against the checks above, every level it produced on its own fails:
the toucan shows 12 palette swatches of which 5 paint nothing, and the windmill
has 114 numbers piled on outline slivers. `finish.py` runs after it for new
levels and, without redrawing anything:

- absorbs anti-aliasing fringes into the area beside them;
- removes palette entries with nothing left to paint and merges look-alikes;
- re-reads each colour from the art (the RGB merge keeps the darkest shade,
  which turned cream grey) and separates regions merged across two different
  art colours (a turquoise spout joined to a blue whale);
- restores outline pixels that were handed to a light region (round eyes
  eroded into squares) and decides afresh which black is ink and which is a
  black area to paint;
- numbers the areas, each number centred where the digit fits.

Revision 11 keeps the picture's detail while it simplifies:

- **The canvas starts blank.** Nothing is printed in colour. The child can
  pinch to zoom, and the rainbow brush is there when an area is fiddly. The
  one printed detail is the white sparkle in an eye.
- **Small details are painted.** A stripe, spot or tassel at least 5 map px
  wide and 60 px in area stays an area to paint. Its number is drawn smaller
  to fit: `size` (font px, 4 to 9) in `data.json`, which `GameCanvas.tsx`
  honours. At the smallest size the number may sit over the lines. Thinner
  fringes from anti-aliasing join the area beside them.
- **Fine black strokes stay.** A mouth, whiskers or guitar strings drawn inside
  a colour are printed over the paint and add no regions.
- **Shading is merged.** A darker or lighter patch of the same hue that touches
  its object with no outline between them joins it. Different hues, greys and
  anything the artist outlined are left alone.
- **Neighbours share a number.** Areas of one colour within 20 map px of each
  other get one number, on the roomiest of them, as `process.py` always did.
  One petal marked 12 tells the child the petals beside it are 12 too.
- **Every area paints the art's colour.** After the merges each area is
  compared with the picture under it. One that has drifted more than delta E 12
  takes the palette colour that matches, or a new colour read from the art. A
  colour is never repainted as another to save a swatch, so older detailed art
  can pass 12 colours; the palette bar scrolls.
- **Two colours in one region are divided.** `process.py` can join pink
  flippers to a grey seal. A patch that differs clearly from the rest of its
  region, is one even colour and has room for a number becomes its own area.
  Shading of the same hue and thin streaks stay as they are.
- **Lines have one weight.** Bare boundaries and hairlines are drawn at a
  steady 5 map px. Lines the artist already drew that heavy are not thickened.
- **No part turns into paper.** `process.py` can take a white sail or a cream
  tummy behind a fine outline for background. Anything the page around the
  subject does not reach is given back as an area to paint in the art's
  colour, and the level check fails if a part is still lost.

Outlines, strokes and eye sparkles live in `lines.png`, which the game draws on
top. The one app change is the optional `size` on a number.
`factory.py audit` lists what the checks find in the shipped levels.

## Where things are

- `manifest.json`: every recipe. Entries with `"factory"` are factory levels;
  29 to 58 are the October 2026 batch and are historical.
- `runs/ID/` (not committed): working files, attempts, review sheets.
- `sources/ID/` (committed on integrate): picture, video, exact graphs, job
  receipts, check reports, reviews, sheets, recipe and `receipt.json`.
- `workflows/`: editable copies of the ComfyUI graphs; regenerate with
  `python build_workflows.py [--install-dir ~/comfy/ComfyUI/user/default/workflows]`.
- `reviews/`, `provenance/`, `recovery-2026-10-04.md`, `revision-prompts.json`:
  records of the 29 to 58 batch.

## Sharing the GPU

`submit` reads ComfyUI's free VRAM first (20 GiB for a picture, 27 for a video).
If ComfyUI is idle but holding old models it asks it to unload them; if another
program still has the memory it waits (`--wait-gpu MINUTES`) or stops. Queuing
video work onto a GPU something else was using is how this workstation froze in
October. `process.py` runs on four threads behind a cross-process lock.

## Tests

```bash
image-processing/venv/bin/python -m unittest discover -s image-processing/generation/tests
```

Sixty-three tests plant one fault at a time (a dead swatch, a number on the wrong
colour, a cut in the video, an edited `data.json`) and prove the matching gate
catches it. The last ones drive a picture through the whole line with ComfyUI
replaced by files, then tamper with the result to show `verify` notices.

## Writing recipes that pass

- Name every colour and keep to large shapes. Small parts get small numbers
  that are fiddly to paint.
- Say what stands alone ("on one small green mound only a little wider than
  the castle"). Scenes that run to the edge are rejected.
- Objects, food and plants must have no faces. Say "Only the frog has a face"
  when a flower sits next to an animal.
- A face on a black head does not survive numbering. Put faces on light colours.
- Describe only what should be drawn. Qwen-Image draws what a prompt names,
  so "no frame, no blobs, no face" produced frames, blobs and a face on the
  cake. Unwanted things live in the negative prompt (`IMAGE_NEGATIVE` in
  `build_workflows.py`), which is stored with each recipe.
- Name enough parts to fill the picture. Asking the model for "15 to 30
  shapes" made it pad a simple boat with loose colour swatches.
- The words "paint-by-numbers" and "sticker" make the model draw palette
  blobs, frames and sticker borders. The template avoids them.
- For the reward, say what must stay the same as well as what moves ("the
  puddle keeps its flat colour and outline"). Water and spouts are what Wan
  most often redraws.
