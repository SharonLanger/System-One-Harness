"""Literal presentation oracles and complete-candidate UTF-16 budget checks."""
import pytest
from laya_context_router.flows import first_method_context as flow
from laya_context_router.hooks.contracts import Context, Noop


def test_O01_R01_N01_literal_source_and_direct_locations(h, golden):
    result = h.run()
    assert result == Context(golden)
    assert h.path.read_text().split('export function calculateInvoiceTotalWithAdjustment')[1].rstrip() in result.text
    assert 'calculateAdjustment' not in result.text
    assert result.text.count('roundToCents') == 2


@pytest.mark.parametrize('ending', ['\n', '\r\n', '\r', '\u2028', '\u2029'])
@pytest.mark.parametrize('trailing', ['', 'END'])
def test_O02_source_bytes_and_inclusive_lines(ending, trailing):
    code = 'function selected() {' + ending + '\t// 😀 `code`  ' + ending + '}'
    if trailing:
        code += ending
    header = flow._method_header('src/a.ts', {'name': 'selected', 'location': {'line': 7}}, code)
    result = flow._pack(header, [], 'ok', 8000)[0]
    assert 'Lines: 7–9\n' in result
    separator = '\n' if code.endswith(('\n', '\u2028', '\u2029')) else '\n\n'
    assert result.split('Lines: 7–9\n', 1)[1].startswith(code + separator + 'Methods called')
    assert len((code + separator).splitlines()) >= 4
    assert code.encode() in result.encode()


def test_O03_visible_metadata_controls_preserve_source():
    code = 'function selected() { return "\t😀"; }'
    header = flow._method_header('src/a.ts', {'name': 'x\n\t\x00\u2028', 'location': {'line': 1}}, code)
    assert 'Method: x\\n\\t\\u0000\\u2028 | Lines:' in header
    assert code in header
    assert flow._metadata('function x(\r\ny:\tstring)\x7f') == r'function x(\r\ny:\tstring)\u007f'


def test_O03_real_multiline_navigation_signature_stays_one_line(h):
    h.path.write_text('function target(\n\tvalue: string\n): string { return value; }\n'
                      'export function chosen() { return target("x"); }')
    h.choose('chosen')
    result = h.run()
    assert isinstance(result, Context)
    assert h.path.read_text().splitlines()[-1] in result.text
    rows = [line for line in result.text.splitlines() if ' | function target(' in line]
    assert rows == ['src/billing/invoice-service.ts | function target(\\n\\tvalue: string\\n): string | Lines: 1–3']


@pytest.mark.parametrize('size', [7999, 8000, 8001])
def test_O04_complete_exact_boundaries(size):
    # Independently measure fixed presentation rather than using the production counter.
    suffix = '\n\nContext scope: selected method only.'
    header = 'x' * (size - len(('row' + suffix).encode('utf-16-le')) // 2)
    full = header + 'row' + suffix
    assert len(full.encode('utf-16-le')) // 2 == size
    packed = flow._pack(header, ['row'], 'ok', 8000)
    if size <= 8000:
        assert packed == (full, 1)
    else:
        assert packed is None


def test_O05_lower_bound_stops_before_navigation(h, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('navigation should not run for oversized method')
    monkeypatch.setattr(flow.typescript, 'get_called_method_locations', forbidden)
    assert h.run(max_context_chars=10) == Noop('output_budget_exceeded')
    assert not h.prepared()


def test_O06_O07_O10_largest_prefix_including_partial_and_omission_notes():
    header, rows = 'method\n', ['first' * 30, 'second' * 60, 'third' * 60]
    wanted = (header + rows[0] + '\nCall list is partial; some targets could not be resolved.\n'
              '2 additional reported methods omitted to fit the context budget.'
              '\n\nContext scope: selected method only.')
    limit = len(wanted.encode('utf-16-le')) // 2
    assert flow._pack(header, rows, 'partial', limit) == (wanted, 1)
    zero = ('method\nCall list is partial; some targets could not be resolved.\n'
            '3 additional reported methods omitted to fit the context budget.'
            '\n\nContext scope: selected method only.')
    assert flow._pack(header, rows, 'partial', len(zero)) == (zero, 0)
    assert flow._pack(header, rows, 'partial', len(zero)-1) is None
    unavailable = 'method\nCall list unavailable.\n\nContext scope: selected method only.'
    assert flow._pack(header, [], 'unavailable', len(unavailable)) == (unavailable, 0)
    assert flow._pack(header, [], 'unavailable', len(unavailable)-1) is None


def test_O08_full_short_list_can_fit_when_omission_notice_does_not():
    full = 'method\nx\n\nContext scope: selected method only.'
    assert flow._pack('method\n', ['x'], 'ok', len(full)) == (full, 1)


def test_O09_supplementary_unicode_and_invalid_unicode():
    assert flow._units('a😀') == 3
    full = '😀\nx\n\nContext scope: selected method only.'
    assert flow._pack('😀\n', ['x'], 'ok', len(full)) is None
    assert flow._pack('😀\n', ['x'], 'ok', len(full)+1) == (full, 1)
    with pytest.raises(UnicodeEncodeError):
        flow._pack('\ud800', [], 'ok', 8000)


@pytest.mark.parametrize('limit', [1, 500, 8000, 10000])
def test_O09_configured_limit_can_only_lower_cap(h, golden, limit):
    result = h.run(max_context_chars=limit)
    if isinstance(result, Context):
        assert len(result.text.encode('utf-16-le')) // 2 <= min(limit, 8000)
    elif limit < 500:
        assert result == Noop('output_budget_exceeded')
    else:
        pytest.fail(repr(result))


def test_O09_config_cannot_raise_hard_cap_for_large_method(h):
    h.path.write_text('export function chosen() { /*' + 'x' * 8100 + '*/ return 1; }')
    h.choose('chosen')
    assert h.run(max_context_chars=10000) == Noop('output_budget_exceeded')


def test_O09_invalid_unicode_is_formatting_failure(h, monkeypatch):
    real = flow.typescript.extract_callable
    def corrupt(*args, **kwargs):
        result = real(*args, **kwargs)
        result['code'] = '\ud800'
        return result
    monkeypatch.setattr(flow.typescript, 'extract_callable', corrupt)
    result = h.run()
    assert result.code == 'formatting_error' and result.stage == 'formatting'
    assert not h.prepared()
