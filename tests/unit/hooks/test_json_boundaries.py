"""Authored JSON input remains supported; invalid/ambiguous input fails explicitly."""
import json
import pytest
from hooks.contracts import Context, Noop, Failure, ValidationError
from hooks.gateway import parse_payload, serialize_response
from json_utils import load_json


@pytest.mark.parametrize('value', [
    {'name': 'שלום 😀', 'nested': {'items': [1, True, None, {'x': 'a\nb'}]}},
    {}, {'zero': 0, 'false': False, 'empty': '', 'list': []},
])
def test_json_file_load_preserves_types_and_values(tmp_path, value):
    source = tmp_path / 'input.json'
    source.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    assert load_json(source) == value


@pytest.mark.parametrize('raw', ['{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', '{bad', ''])
def test_json_file_rejects_malformed_or_duplicate_input(tmp_path, raw):
    source = tmp_path / 'input.json'
    source.write_text(raw)
    with pytest.raises(ValueError):
        load_json(source)


def test_json_file_missing_is_an_explicit_io_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_json(tmp_path / 'missing.json')


@pytest.mark.parametrize('raw', ['{"hook_event_name":"X","x":NaN}',
    '{"hook_event_name":"X","x":Infinity}', '{"hook_event_name":"X","nested":{"x":1,"x":2}}'])
def test_hook_json_rejects_nonstandard_numbers_and_nested_duplicates(raw):
    with pytest.raises(ValidationError) as exc:
        parse_payload(raw, 'X')
    assert exc.value.code == 'invalid_json'


def test_public_context_serialization_round_trips_unicode_and_control_characters():
    text = 'שלום 😀\n"quoted"\t\\source'
    encoded = serialize_response(Context(text), 'UserPromptSubmit')
    assert encoded.count('\n') == 1 and encoded.endswith('\n')
    assert json.loads(encoded) == {'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit', 'additionalContext': text}}


@pytest.mark.parametrize('result', [Noop('no_match'), Failure('unavailable', 'source')])
def test_noncontext_results_have_no_protocol_output(result):
    assert serialize_response(result, 'UserPromptSubmit') == ''
