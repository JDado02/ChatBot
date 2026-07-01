from app.security.ratelimit import InMemoryRateLimiter, RedisRateLimiter


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def test_allows_up_to_limit_then_blocks():
    clk = Clock(0.0)
    rl = InMemoryRateLimiter(limit=3, window_seconds=60, now=clk)
    assert [rl.allow("k") for _ in range(4)] == [True, True, True, False]


def test_window_resets():
    clk = Clock(0.0)
    rl = InMemoryRateLimiter(limit=2, window_seconds=60, now=clk)
    assert rl.allow("k") is True
    assert rl.allow("k") is True
    assert rl.allow("k") is False
    clk.t = 61.0  # nuova finestra
    assert rl.allow("k") is True


def test_keys_are_independent():
    clk = Clock(0.0)
    rl = InMemoryRateLimiter(limit=1, window_seconds=60, now=clk)
    assert rl.allow("a") is True
    assert rl.allow("b") is True
    assert rl.allow("a") is False


def test_reset():
    rl = InMemoryRateLimiter(limit=1, window_seconds=60, now=Clock(0.0))
    assert rl.allow("k") is True
    assert rl.allow("k") is False
    rl.reset("k")
    assert rl.allow("k") is True


class FakeRedis:
    """Minimo client Redis per testare la logica di RedisRateLimiter."""

    def __init__(self):
        self.counters = {}
        self.expires = {}

    def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key, seconds):
        self.expires[key] = seconds


def test_redis_rate_limiter():
    fake = FakeRedis()
    rl = RedisRateLimiter(fake, limit=2, window_seconds=30)
    assert [rl.allow("k") for _ in range(3)] == [True, True, False]
    # EXPIRE impostato una sola volta (alla prima richiesta)
    assert fake.expires["rl:k"] == 30
