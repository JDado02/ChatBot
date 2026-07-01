from app.prompt import SYSTEM_PROMPT, build_context, build_room_facts, build_system_prompt
from app.rooms import Room
from app.search import SearchHit

HIT = SearchHit(1, "colazione", "Colazione a buffet", "7:00-10:30, inclusa.", None, 0.9)


def _room(ac):
    return Room("305", "Suite Junior", 3, 38, 3, "King Size", ["Wi-Fi", "Cassaforte"], ac, None, None)


def test_build_context_empty():
    assert "nessuna informazione" in build_context([])


def test_room_facts_computes_kelvin():
    ac = {
        "disponibile": True,
        "range_temperatura": {"min_celsius": 16, "max_celsius": 30, "supporta_kelvin": True},
    }
    facts = build_room_facts(_room(ac))
    # 16°C -> 289.15 K, 30°C -> 303.15 K, calcolati dal backend
    assert "289.15 K" in facts
    assert "303.15 K" in facts
    assert "305" in facts  # numero stanza


def test_room_facts_without_kelvin():
    ac = {"disponibile": True, "range_temperatura": {"min_celsius": 18, "max_celsius": 26}}
    facts = build_room_facts(_room(ac))
    assert "18°C" in facts
    assert "26°C" in facts
    assert "equivalenti a" not in facts  # nessuna conversione Kelvin mostrata


def test_room_facts_no_ac():
    facts = build_room_facts(_room(None))
    assert "Climatizzatore" not in facts
    assert "Wi-Fi" in facts  # le dotazioni ci sono comunque


def test_system_prompt_includes_room_data_section():
    p = build_system_prompt([HIT], room_facts="Stanza 305 ...")
    assert "DATI STANZA" in p
    assert "Colazione a buffet" in p
