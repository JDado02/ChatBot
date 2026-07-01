from app.security.tenants import get_tenant_by_api_key, Tenant


class FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    """Connessione finta: registra l'ultima query e restituisce una riga fissa."""

    def __init__(self, row):
        self._row = row
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        return FakeCursor(self._row)


def test_maps_row_to_tenant():
    conn = FakeConn(("hotel_alpha", "Hotel Alpha", ["alpha.example.com", "localhost"], True))
    t = get_tenant_by_api_key(conn, "pk_alpha_dev_0001")
    assert isinstance(t, Tenant)
    assert t.tenant_id == "hotel_alpha"
    assert t.allowed_domains == ["alpha.example.com", "localhost"]
    assert t.active is True
    # l'api_key è passata come parametro (no string-interpolation → no injection)
    assert conn.last_params == ("pk_alpha_dev_0001",)


def test_unknown_api_key_returns_none():
    conn = FakeConn(None)
    assert get_tenant_by_api_key(conn, "pk_inesistente") is None


def test_empty_api_key_returns_none_without_query():
    conn = FakeConn(("x", "y", [], True))
    assert get_tenant_by_api_key(conn, "") is None
    assert conn.last_sql is None  # non deve nemmeno interrogare il DB


def test_null_domains_becomes_empty_list():
    conn = FakeConn(("hotel_x", "Hotel X", None, True))
    t = get_tenant_by_api_key(conn, "pk")
    assert t.allowed_domains == []
