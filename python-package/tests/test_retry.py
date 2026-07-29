from teledrive.retry_policy import next_delay, should_retry
from teledrive.error_handler import classify


def test_delays_grow_and_cap():
    d1 = next_delay(1)
    d2 = next_delay(2)
    d10 = next_delay(10)
    assert d1 <= d2
    assert d10 <= 61  # cap 60 + jitter cap 15


def test_transient_retries_until_max():
    err = classify(TimeoutError("timeout"))
    assert should_retry(err, attempt=1) is True
    assert should_retry(err, attempt=5) is False


def test_permanent_no_retry():
    err = classify(ValueError("invalid link"))
    assert should_retry(err, attempt=1) is False
