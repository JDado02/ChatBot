from app.sessions import InMemorySessionStore, RedisSessionStore, session_key


def test_key_format():
    assert session_key("hotel_alpha", "s1") == "hotel_alpha:s1"


def test_inmemory_append_and_history():
    s = InMemorySessionStore()
    s.append("t", "s", "user", "ciao")
    s.append("t", "s", "assistant", "salve")
    h = s.history("t", "s")
    assert [m["role"] for m in h] == ["user", "assistant"]
    assert h[0]["content"] == "ciao"


def test_inmemory_isolation_between_sessions():
    s = InMemorySessionStore()
    s.append("t", "s1", "user", "a")
    s.append("t", "s2", "user", "b")
    assert len(s.history("t", "s1")) == 1
    assert s.history("t", "s2")[0]["content"] == "b"


def test_inmemory_trims_to_max():
    s = InMemorySessionStore(max_messages=2)
    for i in range(5):
        s.append("t", "s", "user", str(i))
    h = s.history("t", "s")
    assert len(h) == 2
    assert [m["content"] for m in h] == ["3", "4"]


class FakeRedis:
    def __init__(self):
        self.lists = {}
        self.ttls = {}

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def ltrim(self, key, start, stop):
        lst = self.lists.get(key, [])
        n = len(lst)
        end = n if stop == -1 else (n + stop + 1 if stop < 0 else stop + 1)
        self.lists[key] = lst[start:end]

    def expire(self, key, seconds):
        self.ttls[key] = seconds

    def lrange(self, key, start, stop):
        lst = self.lists.get(key, [])
        n = len(lst)
        end = n if stop == -1 else (n + stop + 1 if stop < 0 else stop + 1)
        return lst[start:end]


def test_redis_store_roundtrip_and_ttl():
    fake = FakeRedis()
    store = RedisSessionStore(fake, ttl_seconds=1800, max_messages=2)
    store.append("t", "s", "user", "uno")
    store.append("t", "s", "assistant", "due")
    store.append("t", "s", "user", "tre")
    h = store.history("t", "s")
    assert [m["content"] for m in h] == ["due", "tre"]  # trim a 2
    assert fake.ttls["t:s"] == 1800
