"""Production adapters for time, sleeping, and retry jitter."""

import random
import time
from datetime import UTC, datetime


class SystemClock:
    """UTC wall clock for production manifests and checkpoints."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        return datetime.now(UTC)


class BlockingSleeper:
    """Standard blocking sleeper for sequential retry delays."""

    def sleep(self, seconds: float) -> None:
        """Block for a non-negative duration."""
        time.sleep(seconds)


class RandomJitter:
    """System pseudorandom source for bounded backoff jitter."""

    def fraction(self) -> float:
        """Return a value from zero up to one."""
        return random.random()
