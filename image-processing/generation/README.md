# Rainbow Paint by Numbers asset generation

This directory is the repository source of truth for the ComfyUI workflows,
prompts, approved source artwork and quality reviews. The ComfyUI installation
contains editable copies of the workflows; it is not their only home.

## Saved files

- `workflows/rainbow-paint-by-numbers.json`: default original Qwen-Image workflow.
- `workflows/rainbow-paint-by-numbers-rewards.json`: default Wan 2.2 video workflow.
- Matching `.api.json` files: executable API graphs.
- `workflows/rainbow-paint-by-numbers-qwen21-research.json`: optional Qwen 2.1 research workflow.
- `workflows/rainbow-paint-by-numbers-minimax-h3-research.json`: optional MiniMax H3 research workflow.
- Existing Flux2 and Wan2.2 fallback filenames remain available for compatibility.
- `manifest.json`: current subjects, prompts, seeds, motion prompts and engagement criteria.
- `sources/<id>/`: approved image, exact API graph, job receipt, review and prompt recipe.
  Image-edit references are copied here too. `source-index.json` records image hashes.
  Approved reward videos, API graphs, receipts and reviews are also checkpointed.
  `source-index.json` identifies the currently accepted image/video hashes.
- `reviews/`: Astra decisions and measured paintability reports. Source approval
  does not imply video or final playable-asset approval.
- `provenance/`: model and licence records. These are not publication clearance.

`runs/` retains local attempts and superseded images but is gitignored. Approved
images are deliberately copied to the versionable `sources/` directory so they
do not depend on the ComfyUI output folder or temporary files. Final assets are
promoted to `assets/images/levels/` only after all quality gates pass.

## Regenerate the saved workflows

Run from the repository root with ComfyUI running:

```bash
python image-processing/generation/build_workflows.py
```

To also install copies in the local ComfyUI workflow browser:

```bash
python image-processing/generation/build_workflows.py \
  --install-dir /home/lewis/comfy/ComfyUI/user/default/workflows
```

The builder queries ComfyUI's node schema directly; it requires no temporary
template files. Model filenames are explicit in `build_workflows.py`.

## Generate, review and preserve

```bash
python image-processing/generation/batch.py image 29 58
python image-processing/generation/batch.py sheets
python image-processing/generation/checkpoint.py
```

Ordinary image generation uses the installed original `qwen_image_fp8_e4m3fn.safetensors`
checkpoint; ordinary video generation uses Wan 2.2. The original Qwen graph uses
its matching Qwen 2.5 VL encoder and VAE, without a distillation LoRA. It generates
from text; historical Qwen 2.1 image-edit references are not used by this graph.
The base models are Apache 2.0: [Qwen-Image](https://huggingface.co/Qwen/Qwen-Image)
and [Wan 2.2](https://github.com/Wan-Video/Wan2.2).

For research/testing, open the explicitly named research workflow in ComfyUI,
or select the model on the command line:

```bash
python image-processing/generation/batch.py image 29 29 --model qwen21-research
python image-processing/generation/batch.py video 29 29 --model minimax-h3-research
```

These examples skip existing completed jobs; they do not replace approved assets.
Archive a previous attempt before intentionally regenerating it. Changing a
workflow does not change existing assets or their applicable model terms.
Research labels are organisational, not a waiver of model restrictions.

Generation resumes from job receipts. Inspect a failed or stale job before
retrying; archive its image, graph, receipt and review before another attempt.
The checkpoint command saves only current, hash-matched Astra source approvals.

For ages 4+, require substantial contrasting colour areas and clear repeated
colour/number matching. Toucan 35 and cow 37 are the user's approved benchmarks.
Background, outlines, tiny highlights and adjacent shades are not meaningful
extra colours. Reject malformed anatomy, repeated-object sheets and excessive
small detail. Inspect the actual processed numbered picture as well as the source.

Real objects, vehicles, buildings, food and plants must have **no anthropomorphic
faces, eyes, mouths or limbs**, including their decorations. Animal faces remain
appropriate. Object source approvals require `object_realism_revision: 1` as well
as the engagement gate. This applies to reward videos too.

Video generation requires revision-2 source approval with an exact image hash:

```bash
python image-processing/generation/batch.py video 29 58
```

Review the resulting motion with Astra before processing. The user retained the
original `image-processing/process.py`; use that script to create game bundles.
`npm run verify:new-assets` checks explicit imports, structural metadata, original
processor receipts, copied output hashes and separate source/video approvals.
Historical experimental processed-image reviews are not current release gates.

## Current checkpoint

As of 2026-10-04, all 30 source images and all 30
reward videos are accepted and saved under `sources/29/` through `sources/58/`.
Each directory contains `image.png`, `video.mp4`, exact API graphs, job receipts,
recipes and reviews. `provenance/generation-completion.json` records the final
hash/format audit. Video reviews inspect chronological sampled frames, not every
frame. Snail 32 uses the original attempt explicitly selected by the user. Train
43 uses the corrected tall-chimney steam version; minor late steam-edge contact
is documented as acceptable. Xylophone 55 and guitar/tambourine 56 were replaced
following user feedback. Guitar 56 now animates both instruments, including
tambourine jingles/ribbons. Windmill 57 rotates continuously in one direction
with an initial speed-up; brief outline-only top-edge contact is documented as
a minor visual caveat.

All 30 sources have now also been reprocessed with the original committed
`process.py`, copied to `assets/images/levels/29/` through `58/`, and explicitly
registered in `utils/level-loader.ts`. The game contains 58 registered pictures.
Earlier experimental bundles were backed up and replaced. Original levels 1–28
and the processor were verified unchanged. Structural map/label checks,
TypeScript, Android/iOS bundle exports and exported asset byte checks passed.
`provenance/integration-completion.json` records this verification. No new native
device run or store submission is claimed. Analytics remains deferred.

## Desktop resource limits

After the workstation freeze, launch ComfyUI with `--reserve-vram 4` and verify
actual GPU headroom. Run generation and image processing in separate phases.
The reserve is not a hard allocation cap. Generation batches share a cross-process
lock to run one at a time. The restored original `process.py` does not use that
lock or the experimental resource wrapper. Manually queued ComfyUI jobs also do
not participate in the lock. Check the queue and keep processing/emulators off
while generating. For this conversion the unchanged processor ran sequentially
with external CPU affinity limited to cores 0–1 and numerical-library thread
limits of two, after generation had finished and GPU models were unloaded.
See `recovery-2026-10-04.md` for the evidence and interrupted job recovery.
