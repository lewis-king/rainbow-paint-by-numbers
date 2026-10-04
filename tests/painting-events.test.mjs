import assert from 'node:assert/strict';
import { test } from 'node:test';
import { PaintingVisit } from '../utils/painting-events.ts';
const picture = { picture_id: '29', picture_name: 'Puppy', picture_category: 'animals' };
const setup = (progress = 0) => {
  const events = []; let clock = 0;
  return { events, advance: ms => { clock += ms; }, visit: new PaintingVisit(picture, progress, e => events.push(e), () => clock) };
};
test('selection/loading and restoration do not count as painting', () => {
  const {visit,events}=setup(50); visit.paint(50);
  assert.deepEqual(events, []);
  visit.paint(51);
  assert.equal(events[0].name, 'painting_started');
  assert.equal(events[0].params.start_type, 'resume');
  assert.equal(events.length, 1);
});
test('only one start, milestone and completion per visit', () => {
  const {visit,events}=setup();
  for (const p of [1, 1, 25, 25, 80, 99, 100, 99]) visit.paint(p);
  assert.deepEqual(events.map(e=>e.name), ['painting_started','painting_progress','painting_progress','painting_progress','painting_completed']);
  assert.deepEqual(events.filter(e=>e.name==='painting_progress').map(e=>e.params.milestone),[25,50,75]);
});
test('background time and reward viewing time are excluded', () => {
  const {visit,events,advance}=setup();
  visit.paint(1);advance(10000);visit.pause();advance(60000);visit.resume();advance(5000);visit.paint(99);advance(40000);visit.leave();visit.leave();
  assert.equal(events.find(e=>e.name==='painting_completed').params.active_seconds,15);
  assert.equal(events.filter(e=>e.name==='painting_left').length,1);
  assert.equal(events.at(-1).params.active_seconds,15);
});
test('opening a finished picture never adds another completion', () => {
  const {visit,events}=setup(100);visit.paint(100);visit.leave();
  assert.deepEqual(events.map(e=>e.name),['painting_left']);
  assert.equal(events[0].params.completed,1);
});
test('transport failures never break gameplay', () => {
  const visit = new PaintingVisit(picture,0,()=>{throw Error('offline')});
  assert.doesNotThrow(()=>{visit.paint(100);visit.leave()});
});
