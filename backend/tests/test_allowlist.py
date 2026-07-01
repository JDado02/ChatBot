from app.security.allowlist import extract_host, is_origin_allowed

ALLOWED = ["alpha.example.com", "www.alpha.example.com", "localhost"]


def test_extract_host_from_origin():
    assert extract_host("https://alpha.example.com") == "alpha.example.com"


def test_extract_host_with_port_and_path():
    assert extract_host("https://alpha.example.com:8443/widget.js") == "alpha.example.com"


def test_extract_host_bare_domain():
    assert extract_host("localhost") == "localhost"


def test_extract_host_none():
    assert extract_host(None) is None
    assert extract_host("") is None


def test_extract_host_case_insensitive():
    assert extract_host("https://Alpha.Example.COM") == "alpha.example.com"


def test_origin_allowed():
    assert is_origin_allowed("https://alpha.example.com", None, ALLOWED) is True


def test_origin_allowed_via_referer_fallback():
    assert is_origin_allowed(None, "https://localhost:3000/page", ALLOWED) is True


def test_origin_preferred_over_referer():
    # Origin non consentito => nega, anche se il Referer sarebbe valido.
    assert is_origin_allowed("https://evil.com", "https://alpha.example.com", ALLOWED) is False


def test_origin_not_allowed():
    assert is_origin_allowed("https://evil.com", None, ALLOWED) is False


def test_fail_closed_without_origin_or_referer():
    assert is_origin_allowed(None, None, ALLOWED) is False


def test_fail_closed_without_configured_domains():
    assert is_origin_allowed("https://alpha.example.com", None, []) is False


def test_no_subdomain_wildcard():
    # 'sub.alpha.example.com' NON è autorizzato solo perché lo è alpha.example.com
    assert is_origin_allowed("https://sub.alpha.example.com", None, ALLOWED) is False
