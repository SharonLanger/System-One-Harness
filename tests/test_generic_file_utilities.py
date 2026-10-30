from laya_context_router.building_blocks.resolve_file import resolve_file


def test_partial_path_contract_and_generic_test_file(tmp_path):
    wanted = tmp_path / 'src/service1/invoice-service.ts'
    wanted.parent.mkdir(parents=True)
    wanted.write_text('')
    other = tmp_path / 'src/service2/invoice-service.ts'
    other.parent.mkdir(parents=True)
    other.write_text('')
    assert resolve_file('service1/invoice-service.ts', cwd=tmp_path, repository_root=tmp_path).selected_path == wanted
    assert resolve_file('invoice-service.ts', cwd=tmp_path, repository_root=tmp_path).status == 'ambiguous'
    spec = tmp_path / 'a.spec.ts'
    spec.write_text('')
    assert resolve_file('a.spec.ts', cwd=tmp_path, repository_root=tmp_path).selected_path == spec


def test_configured_detector_production_test_and_python_spans():
    from laya_context_router.building_blocks.file_reference_utils import detect_configured_references
    text = '😀 a.ts a.spec.ts `src/my file.ts`:12:3 a.d.ts'
    refs = detect_configured_references(text)
    assert [ref.path for ref in refs] == ['a.ts', 'src/my file.ts']
    assert all(text[ref.start:ref.end] == ref.path for ref in refs)
    assert [ref.path for ref in detect_configured_references(text, {'preset': 'test'})] == ['a.spec.ts']


def test_legacy_python_regex_flags_and_conditionals_remain_compatible():
    import re
    from laya_context_router.building_blocks.file_reference_utils import detect_file_references
    pattern = re.compile(r'^(?P<quote>")?(?P<path>foo\.ts)(?(quote)")$', re.IGNORECASE | re.MULTILINE)
    refs = detect_file_references('"FOO.TS"\nfoo.ts\n"foo.ts', pattern)
    assert [(ref.path, ref.kind) for ref in refs] == [('FOO.TS', 'non_code'), ('foo.ts', 'production_code')]


def test_configured_detector_forwards_bridge_settings(monkeypatch):
    from laya_context_router.building_blocks.file_reference_utils import detect_configured_references
    calls = []
    def detector(text, config, **kwargs):
        calls.append((text, config, kwargs))
        return {'status': 'ok', 'data': {'references': []}, 'diagnostics': []}
    monkeypatch.setattr('laya_context_router.building_blocks.typescript.detect_references', detector)
    assert detect_configured_references('a.ts', {'preset': 'test'}, node='custom-node',
                                        helper='/custom/helper.js', timeout=1.25) == []
    assert calls == [('a.ts', {'preset': 'test'},
                      {'node': 'custom-node', 'helper': '/custom/helper.js', 'timeout': 1.25})]
