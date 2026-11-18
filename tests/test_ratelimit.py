from libarrei.ratelimit import RateLimiter


def test_rate_limiter_sleeps_only_the_remaining_gap():
    now, slept = [0.0], []
    limiter = RateLimiter(1.0, clock=lambda: now[0], sleep=slept.append)
    limiter.wait()
    now[0] = 0.25
    limiter.wait()
    assert slept == [0.75]
