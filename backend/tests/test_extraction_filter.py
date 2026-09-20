from app.agents.extraction import MAX_EXTRACTION_ITEMS, _filter_extraction


def test_keeps_entities_with_allowed_type():
    raw = {"entities": [{"type": "TASK", "name": "OCR Pipeline"}], "relationships": []}
    assert _filter_extraction(raw)["entities"] == [{"type": "TASK", "name": "OCR Pipeline"}]


def test_drops_entities_with_disallowed_type():
    raw = {"entities": [{"type": "IGNORE_PREVIOUS_INSTRUCTIONS", "name": "x"}], "relationships": []}
    assert _filter_extraction(raw)["entities"] == []


def test_drops_relationships_referencing_dropped_entities():
    raw = {
        "entities": [{"type": "TASK", "name": "OCR"}],
        "relationships": [{"source": "OCR", "relation": "RELATED_TO", "target": "Frontend"}],
    }
    assert _filter_extraction(raw)["relationships"] == []


def test_keeps_relationship_between_two_valid_entities():
    raw = {
        "entities": [{"type": "TASK", "name": "OCR"}, {"type": "PERSON", "name": "Alex"}],
        "relationships": [{"source": "OCR", "relation": "ASSIGNED_TO", "target": "Alex"}],
    }
    assert _filter_extraction(raw)["relationships"] == [{"source": "OCR", "relation": "ASSIGNED_TO", "target": "Alex"}]


def test_malformed_entity_entries_are_ignored():
    raw = {"entities": ["not-a-dict", {"type": "TASK"}], "relationships": []}
    assert _filter_extraction(raw)["entities"] == []


def test_non_string_type_does_not_crash_with_unhashable_typeerror():
    raw = {"entities": [{"type": ["not", "a", "string"], "name": "x"}], "relationships": []}
    assert _filter_extraction(raw)["entities"] == []


def test_non_string_state_change_entity_does_not_crash():
    raw = {
        "entities": [{"type": "TASK", "name": "OCR"}],
        "relationships": [],
        "state_changes": [{"entity": {"nested": "dict"}, "new_state": "MERGED"}],
    }
    assert _filter_extraction(raw)["state_changes"] == []


def test_keeps_valid_state_change():
    raw = {
        "entities": [{"type": "TASK", "name": "OCR"}],
        "relationships": [],
        "state_changes": [{"entity": "OCR", "new_state": "MERGED", "confidence": 0.9}],
    }
    assert _filter_extraction(raw)["state_changes"] == [{"entity": "OCR", "new_state": "MERGED", "confidence": 0.9}]


def test_entity_list_is_capped_to_bound_graph_growth():
    raw = {"entities": [{"type": "TASK", "name": f"task-{i}"} for i in range(MAX_EXTRACTION_ITEMS + 20)]}
    assert len(_filter_extraction(raw)["entities"]) <= MAX_EXTRACTION_ITEMS
