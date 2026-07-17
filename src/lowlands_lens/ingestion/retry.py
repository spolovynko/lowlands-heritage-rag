"""Sanitized failure classification and bounded retry execution."""

from collections.abc import Callable
from dataclasses import dataclass

from lowlands_lens.discovery.client import (
    EuropeanaAuthenticationError,
    EuropeanaHttpStatusError,
    EuropeanaInvalidJsonError,
    EuropeanaInvalidResponseError,
    EuropeanaRateLimitError,
    EuropeanaRecordNotFoundError,
    EuropeanaTimeoutError,
    EuropeanaTransportError,
)
from lowlands_lens.ingestion.contracts import (
    FailureCategory,
    FailureDetail,
    RetryPolicy,
)
from lowlands_lens.ingestion.filesystem import BronzeIntegrityError
from lowlands_lens.ingestion.ports import AttemptObserver, JitterSource, Sleeper


@dataclass(frozen=True, slots=True)
class RetryResult[ResultT]:
    """Successful value plus the number of consumed attempts."""

    value: ResultT
    attempts: int


class OperationFailedError(RuntimeError):
    """Sanitized terminal operation failure after classification or retries."""

    def __init__(self, failure: FailureDetail, attempts: int) -> None:
        self.failure = failure
        self.attempts = attempts
        super().__init__(failure.message)


class AttemptBudgetExhaustedError(RuntimeError):
    """Raised before access when the run's durable call ceiling is exhausted."""


def execute_with_retry[ResultT](
    operation: Callable[[], ResultT],
    *,
    policy: RetryPolicy,
    sleeper: Sleeper,
    jitter: JitterSource,
    before_attempt: AttemptObserver,
) -> RetryResult[ResultT]:
    """Execute an operation within attempt, delay, and external call budgets."""
    total_delay = 0.0
    for attempt in range(1, policy.max_attempts + 1):
        before_attempt()
        try:
            return RetryResult(value=operation(), attempts=attempt)
        except Exception as error:
            failure = classify_failure(error)
            if not failure.retryable:
                raise OperationFailedError(failure, attempt) from None
            if attempt == policy.max_attempts:
                raise OperationFailedError(_retry_exhausted(), attempt) from None

            delay = _retry_delay(failure, attempt, policy, jitter)
            if total_delay + delay > policy.max_total_delay_seconds:
                raise OperationFailedError(_retry_exhausted(), attempt) from None
            sleeper.sleep(delay)
            total_delay += delay

    raise AssertionError("The bounded retry loop must return or raise.")


def classify_failure(error: Exception) -> FailureDetail:
    """Convert known exceptions into stable details without original diagnostics."""
    if isinstance(error, EuropeanaTimeoutError):
        return FailureDetail(
            category=FailureCategory.TIMEOUT,
            retryable=True,
            message="The Europeana request timed out.",
        )
    if isinstance(error, EuropeanaTransportError):
        return FailureDetail(
            category=FailureCategory.TRANSPORT,
            retryable=True,
            message="The Europeana request could not be completed.",
        )
    if isinstance(error, EuropeanaRateLimitError):
        return FailureDetail(
            category=FailureCategory.RATE_LIMITED,
            retryable=True,
            message="Europeana temporarily rate limited the request.",
            status_code=429,
            retry_after_seconds=error.retry_after_seconds,
        )
    if isinstance(error, EuropeanaHttpStatusError) and 500 <= error.status_code < 600:
        return FailureDetail(
            category=FailureCategory.PROVIDER_SERVER,
            retryable=True,
            message="Europeana returned a transient server failure.",
            status_code=error.status_code,
        )
    if isinstance(error, EuropeanaAuthenticationError):
        return FailureDetail(
            category=FailureCategory.AUTHENTICATION,
            retryable=False,
            message="Europeana rejected the configured credential.",
            status_code=401,
        )
    if isinstance(error, EuropeanaRecordNotFoundError):
        return FailureDetail(
            category=FailureCategory.NOT_FOUND,
            retryable=False,
            message="The requested Europeana record was not found.",
            status_code=404,
        )
    if isinstance(error, EuropeanaInvalidJsonError):
        return FailureDetail(
            category=FailureCategory.INVALID_JSON,
            retryable=False,
            message="Europeana returned invalid JSON.",
        )
    if isinstance(error, EuropeanaInvalidResponseError):
        return FailureDetail(
            category=FailureCategory.INVALID_RESPONSE,
            retryable=False,
            message="Europeana returned an invalid Record response.",
        )
    if isinstance(error, BronzeIntegrityError):
        return FailureDetail(
            category=FailureCategory.INTEGRITY,
            retryable=False,
            message="Existing Bronze evidence failed an integrity check.",
        )
    if isinstance(error, EuropeanaHttpStatusError):
        return FailureDetail(
            category=FailureCategory.UNKNOWN,
            retryable=False,
            message="Europeana returned a permanent HTTP failure.",
            status_code=error.status_code,
        )
    return FailureDetail(
        category=FailureCategory.UNKNOWN,
        retryable=False,
        message="The ingestion operation failed permanently.",
    )


def _retry_delay(
    failure: FailureDetail,
    attempt: int,
    policy: RetryPolicy,
    jitter: JitterSource,
) -> float:
    """Calculate Retry-After or bounded exponential delay with positive jitter."""
    if failure.retry_after_seconds is not None:
        return float(failure.retry_after_seconds)
    fraction = jitter.fraction()
    if not 0.0 <= fraction <= 1.0:
        raise RuntimeError("The jitter source returned an invalid fraction.")
    exponential: float = min(
        policy.max_delay_seconds,
        policy.base_delay_seconds * (2 ** (attempt - 1)),
    )
    jittered: float = exponential * (1.0 + policy.jitter_ratio * fraction)
    return policy.max_delay_seconds if jittered > policy.max_delay_seconds else jittered


def _retry_exhausted() -> FailureDetail:
    """Return a stable terminal detail without retaining the last exception."""
    return FailureDetail(
        category=FailureCategory.RETRY_EXHAUSTED,
        retryable=True,
        message="The retry budget was exhausted.",
    )
