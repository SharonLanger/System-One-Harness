"""Presentation contracts use supplied source strings, never source-file reads."""
from copy import deepcopy
from itertools import product

import pytest

from context_format import format_context, _GAP_NOTES


def context(code='function chosen() {}', line=4):
    return {'path':'/repo/src/a.ts', 'code':code,
            'callable':{'start':10,'end':30,'location':{'line':line,'column':1}},
            'dependencies':[], 'gaps':[], 'hash':'internal-secret'}


def dependency(code, kind='VariableStatement', path='/repo/support.ts', start=0, line=9):
    return {'path':path,'start':start,'end':start+len(code),'kind':kind,
            'code':code,'location':{'line':line,'column':1}}


def render(value, **options):
    return format_context(value, project_root='/repo', **options)


def test_minimal_plain_text_and_no_empty_labels():
    assert render(context()) == ('Selected TypeScript context (partial).\n\nSelected method\n\n'
                                 'src/a.ts (lines 4–4)\nfunction chosen() {}')


@pytest.mark.parametrize('imports,declarations,notes', list(product([False,True], repeat=3)))
def test_independent_switches(imports,declarations,notes):
    value=context(); value['dependencies']=[dependency('import {x} from "x";', 'ImportDeclaration'), dependency('const x=1;')]
    value['gaps']=[{'code':'depth_limit','message':'secret'}]
    output=render(value,include_imports=imports,include_dependencies=declarations,include_notes=notes)
    assert ('\n\nImports\n\n' in output)==imports
    assert ('\n\nSupporting declarations\n\n' in output)==declarations
    assert ('\n\nContext notes\n\n' in output)==notes
    assert 'secret' not in output


def test_source_intact_immutable_repeatable_and_no_file_reads(monkeypatch):
    code='function chosen() {\r\n// ``` # heading internal-secret 😀\r\nreturn `hash`;\r\n}'
    value=context(code); value['dependencies']=[dependency('class C { '+code+' }')]
    before=deepcopy(value)
    monkeypatch.setattr('builtins.open',lambda *a,**k: pytest.fail('formatter read a file'))
    output=render(value)
    assert code in output and value['dependencies'][0]['code'] in output
    assert value==before and render(value)==output
    assert '\n# ' not in output and '\n- ' not in output


def test_deduplication_uses_path_and_range_not_code():
    value=context(); first=dependency('const x=1;')
    value['dependencies']=[{**first,'path':value['path'],'start':10,'end':30},first,dict(first),
                           {**first,'start':100,'end':110},{**first,'path':'/repo/other.ts'}]
    output=render(value)
    assert output.count('const x=1;')==3
    assert 'other.ts (lines 9–9)' in output


@pytest.mark.parametrize('category,note', _GAP_NOTES.items())
def test_known_gap_notes(category,note):
    value=context(); value['gaps']=[{'code':category,'message':'private diagnostic'}]
    assert render(value).endswith('Context notes\n\n'+note)
    assert 'private diagnostic' not in render(value)


def test_gap_order_dedup_and_unknown_diagnostics():
    value=context(); value['gaps']=[{'code':code,'message':'secret AST hash'} for code in ['depth_limit','unknown','depth_limit','another']]
    assert render(value).endswith(_GAP_NOTES['depth_limit']+'\nSome additional context could not be collected.')
    assert 'secret' not in render(value) and 'internal-secret' not in render(value)


@pytest.mark.parametrize('newline',['\n','\r\n','\r','\u2028','\u2029'])
@pytest.mark.parametrize('terminal',[False,True])
def test_inclusive_ranges_and_exact_line_endings(newline,terminal):
    code='function chosen() {'+newline+'return "😀";'+newline+'}'+(newline if terminal else '')
    assert render(context(code)).endswith('src/a.ts (lines 4–6)\n'+code)


@pytest.mark.parametrize('code,last',[('x',4),('x\n',4),('x\n\n\n',6)])
def test_single_lines_and_trailing_blank_lines(code,last):
    assert render(context(code)).endswith(f'src/a.ts (lines 4–{last})\n'+code)


def test_independent_locations():
    value=context(); value['dependencies']=[dependency('interface X {\na: number;\n}',line=9),dependency('import "x";',kind='ImportDeclaration',path='/repo/import.ts',line=2)]
    output=render(value)
    assert 'support.ts (lines 9–11)\ninterface X' in output
    assert 'import.ts (lines 2–2)\nimport "x";' in output


def test_explicit_root_independent_of_process_cwd(tmp_path,monkeypatch):
    before=deepcopy(context()); expected=render(before)
    for cwd in [tmp_path,tmp_path/'nested']:
        cwd.mkdir(exist_ok=True); monkeypatch.chdir(cwd)
        assert render(before)==expected
    assert before==context()


def test_required_absolute_project_root():
    with pytest.raises(TypeError): format_context(context())
    for root in ['', '.', 'relative']:
        with pytest.raises(ValueError,match='project_root must be absolute'):
            format_context(context(),project_root=root)


def test_root_normalization_and_portable_display():
    assert format_context(context(),project_root='/repo/./')==render(context())
    value=context(); value['path']='/copy of repo/😀/src/a.ts'
    assert format_context(value,project_root='/copy of repo/😀').endswith('src/a.ts (lines 4–4)\nfunction chosen() {}')


def test_inventory_fixture_retains_independently_specified_spans():
    from pathlib import Path
    fixture=Path(__file__).resolve().parents[1]/'tests/fixtures/first_flow_project/src/fulfillment/inventory.ts'
    lines=fixture.read_text().splitlines(keepends=True)
    method=''.join(lines[45:56]).removesuffix('\n')
    interface=''.join(lines[8:12]).removesuffix('\n')
    assert method.startswith('export function consolidateOrderLines(') and method.endswith('\n}')
    assert interface=='export interface OrderLine {\n  sku: string;\n  quantity: number;\n}'
    value=context(method,line=46)
    value['dependencies']=[dependency(interface,line=9)]
    output=render(value)
    assert 'src/a.ts (lines 46–56)\n'+method in output
    assert 'support.ts (lines 9–12)\n'+interface in output
