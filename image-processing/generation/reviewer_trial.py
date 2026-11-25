"""How well does a local vision model review? Run it over sheets whose verdict is known.

    venv/bin/python generation/reviewer_trial.py qwen3.8:27b gemma4:31b

Known sheets come from runs/: every level in the app passed review, and the archived
attempts under runs/ID/attempts/ were rejected for a recorded reason. Nothing is
written to the factory's records. A reviewer is fit for the line when it rejects
the known rejects; passing a bad picture is the costly mistake, an UNSURE is not.
"""
import json
import sys
import time
from pathlib import Path

import factory


def known_sheets():
    cases = []
    for run in sorted(factory.RUNS.glob('[0-9]*'), key=lambda p: int(p.name)):
        recipe = next((r for r in factory.load_manifest()['levels'] if r['id'] == run.name), None)
        if recipe is None:
            continue
        for stage in ('image', 'video'):
            saved = factory.read_json(run / f'{stage}-review.json')
            if saved and (run / f'review-{stage}.jpg').is_file():
                cases.append((f'{run.name} current {stage}', run / f'review-{stage}.jpg', stage, recipe, saved['verdict'], ''))
        for attempt in sorted(run.glob('attempts/*')):
            old = factory.read_json(attempt / 'recipe.json') or recipe
            reason = old.get('retry_reason', '')
            failed_stage = attempt.name.split('-')[1]
            for stage in ('image', 'video'):
                sheet = attempt / f'review-{stage}.jpg'
                if not sheet.is_file():
                    continue
                saved = factory.read_json(attempt / f'{stage}-review.json')
                if saved:
                    expected = saved['verdict']
                elif stage == failed_stage:
                    expected = 'FAIL'   # archived because of this sheet
                else:
                    continue
                cases.append((f'{run.name} {attempt.name} {stage}', sheet, stage, old, expected,
                              reason if expected == 'FAIL' else ''))
    return cases


def main(models):
    cases = known_sheets()
    print(f'{len(cases)} sheets with a known verdict '
          f'({sum(c[4] == "FAIL" for c in cases)} rejects)\n', flush=True)
    factory.reviewer_gpu(wait_minutes=0)
    for model in models:
        tally = {'right': 0, 'unsure': 0, 'passed a reject': 0, 'failed a good one': 0}
        started = time.time()
        for index, (name, sheet, stage, recipe, expected, reason) in enumerate(cases):
            checks = factory.REVIEW_CHECKLIST[stage]
            prompt = factory.REVIEWER_BRIEF.format(
                title=recipe['title'], kind=recipe['kind'], views=factory.VIEWS[stage],
                subject=recipe.get('subject') or recipe['image_prompt'],
                checks='\n'.join(f'{n}. {c}' for n, c in enumerate(checks, 1)))
            answer = factory.ask_reviewer(factory.review_views(sheet, stage), prompt, model,
                                          keep_loaded=index < len(cases) - 1)
            verdict, notes = factory.read_verdict(answer, checks)
            outcome = ('right' if verdict == expected else 'unsure' if verdict == 'UNSURE'
                       else 'passed a reject' if expected == 'FAIL' else 'failed a good one')
            tally[outcome] += 1
            faults = ' | '.join(note for note in notes if 'FAULT' in note)[:260]
            print(f'{model}  {name:<26} expected {expected:<4} got {verdict:<6} {outcome.upper() if outcome != "right" else ""}'
                  + (f'\n      known fault: {reason[:120]}' if reason else '')
                  + (f'\n      it said: {faults}' if faults else ''), flush=True)
        print(f'\n{model}: {json.dumps(tally)} in {time.time() - started:.0f}s\n', flush=True)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1:] or [factory.VISION_MODEL])
