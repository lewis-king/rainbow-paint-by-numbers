/** Event semantics shared by the eventual analytics transport and deterministic tests.
 * No identifiers, free text, coordinates, screenshots, or children's drawings.
 */
export type PaintingEventName =
  | 'picture_selected' | 'painting_started' | 'painting_progress'
  | 'painting_completed' | 'painting_left' | 'painting_resumed'
  | 'painting_reset' | 'reward_viewed';
export type PaintingEvent = {
  name: PaintingEventName;
  params: {
    picture_id: string;
    picture_name: string;
    picture_category: string;
    progress_bucket?: number;
    milestone?: number;
    active_seconds?: number;
    start_type?: 'new' | 'resume';
    completed?: 0 | 1;
  };
};
export type EventSink = (event: PaintingEvent) => void;

/** One visit to one picture. Restoration never counts as starting or completing. */
export class PaintingVisit {
  private started = false;
  private completed = false;
  private progress: number;
  private milestones: Set<number>;
  private activeSince: number | null;
  private activeMs = 0;
  private closed = false;
  private readonly startType: 'new' | 'resume';

  private readonly picture: Pick<PaintingEvent['params'], 'picture_id' | 'picture_name' | 'picture_category'>;
  private readonly sink: EventSink;
  private readonly now: () => number;

  constructor(
    picture: Pick<PaintingEvent['params'], 'picture_id' | 'picture_name' | 'picture_category'>,
    initialProgress: number,
    sink: EventSink,
    now: () => number = Date.now,
  ) {
    this.picture = picture;
    this.sink = sink;
    this.now = now;
    this.progress = initialProgress;
    this.completed = initialProgress >= 99;
    this.startType = initialProgress > 0 ? 'resume' : 'new';
    this.milestones = new Set([25, 50, 75].filter(n => initialProgress >= n));
    this.activeSince = null; // Time begins with actual painting, not a loaded screen.
  }

  private emit(name: PaintingEventName, params: Partial<PaintingEvent['params']> = {}) {
    try { this.sink({ name, params: { ...this.picture, ...params } }); }
    catch { /* Analytics must never interrupt painting. */ }
  }

  private activeSeconds() {
    return Math.max(0, Math.round((this.activeMs + (this.activeSince === null ? 0 : this.now() - this.activeSince)) / 1000));
  }

  paint(progress: number) {
    if (this.closed || this.completed || !Number.isFinite(progress) || progress <= this.progress) return;
    if (!this.started) {
      this.started = true;
      this.activeSince = this.now();
      this.emit('painting_started', { start_type: this.startType });
    }
    this.progress = Math.min(100, Math.max(0, progress));
    for (const milestone of [25, 50, 75]) {
      if (this.progress >= milestone && !this.milestones.has(milestone)) {
        this.milestones.add(milestone);
        this.emit('painting_progress', { milestone });
      }
    }
    if (this.progress >= 99) {
      this.completed = true;
      this.pause();
      this.emit('painting_completed', { active_seconds: this.activeSeconds() });
    }
  }

  pause() {
    if (this.activeSince !== null) {
      this.activeMs += Math.max(0, this.now() - this.activeSince);
      this.activeSince = null;
    }
  }

  resume() {
    if (this.started && !this.completed && !this.closed && this.activeSince === null) {
      this.activeSince = this.now();
      this.emit('painting_resumed');
    }
  }

  leave() {
    if (this.closed) return;
    this.pause();
    this.closed = true;
    this.emit('painting_left', {
      progress_bucket: this.progress >= 99 ? 100 : Math.floor(this.progress / 25) * 25,
      active_seconds: this.activeSeconds(), completed: this.completed ? 1 : 0,
    });
  }
}
