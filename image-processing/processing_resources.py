"""Keep local image processing responsive on a shared desktop."""
import functools
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def heavy_work_slot():
    """One generation batch OR CPU conversion at a time across repo tools."""
    import fcntl
    lock_path = Path(tempfile.gettempdir()) / f'rainbow-processing-{os.getuid()}.lock'
    with lock_path.open('a') as lock:
        print('Waiting for the shared generation/processing slot...', flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def serialized_work(function):
    @functools.wraps(function)
    def guarded(*args, **kwargs):
        with heavy_work_slot():
            return function(*args, **kwargs)
    return guarded


def desktop_friendly(function):
    """Serialize expensive processing and bound native-library parallelism.

    flock is released even if a process crashes. Runtime threadpool limits also
    cover callers which imported NumPy before importing the processor.
    """
    @functools.wraps(function)
    def guarded(*args, **kwargs):
        import cv2
        from threadpoolctl import threadpool_limits

        threads = max(1, min(4, int(os.environ.get('RAINBOW_PROCESS_THREADS', '2'))))
        with heavy_work_slot():
            previous_threads = cv2.getNumThreads()
            affinity = os.sched_getaffinity(0) if hasattr(os, 'sched_getaffinity') else None
            try:
                if affinity:
                    os.sched_setaffinity(0, set(sorted(affinity)[:threads]))
                # Lower priority only; leave the calling worker at this priority.
                if hasattr(os, 'getpriority') and os.getpriority(os.PRIO_PROCESS, 0) < 10:
                    os.setpriority(os.PRIO_PROCESS, 0, 10)
                cv2.setNumThreads(threads)
                with threadpool_limits(limits=threads):
                    return function(*args, **kwargs)
            finally:
                cv2.setNumThreads(previous_threads)
                if affinity:
                    os.sched_setaffinity(0, affinity)
    return guarded
