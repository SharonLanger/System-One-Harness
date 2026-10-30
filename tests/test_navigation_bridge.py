from pathlib import Path
import pytest
from laya_context_router.building_blocks import typescript as ts


def fixture(tmp_path):
    (tmp_path / 'tsconfig.json').write_text('{"include":["*.ts"]}')
    (tmp_path / 'target.ts').write_text('export function work() { return 1; }\n')
    (tmp_path / 'caller.ts').write_text('import {work} from "./target";\nexport function run() { work(); }\n')
    return ts.outline(tmp_path / 'target.ts')['callables'][0]['id']


def test_outgoing_and_incoming_bridge(tmp_path):
    target = fixture(tmp_path)
    caller = next(x for x in ts.outline(tmp_path / 'caller.ts')['callables'] if x['name'] == 'run')['id']
    outgoing = ts.get_called_method_locations('caller.ts', caller, project_root=tmp_path)
    assert outgoing['status'] == 'ok', outgoing
    assert outgoing['data']['methods'][0]['path'] == 'target.ts'
    assert outgoing['data']['methods'][0]['callable_id'] == target
    incoming = ts.get_calling_method_locations('target.ts', target, project_root=tmp_path, tsconfig_path='tsconfig.json')
    assert incoming['status'] == 'ok', incoming
    assert incoming['data']['callers'][0]['path'] == 'caller.ts'
    assert incoming['data']['callers'][0]['callable_id'] == caller
    assert incoming['data']['scope']['searched_files'] == ['caller.ts', 'target.ts']


@pytest.mark.parametrize('item', [
    {'path': '../escape.ts'}, {'start_line': 0}, {'end_line': 0}, {'call_sites': []},
    {'callable_id': 'not-an-id'}, {'signature': 9},
])
def test_outgoing_rejects_invalid_fields(item):
    original = {'path': 'src/a.ts', 'callable_id': 'a'*64+':1:2', 'name': 'a',
                'signature': 'function a()', 'start_line': 1, 'end_line': 1,
                'call_sites': [{'path': 'src/b.ts', 'start_line': 1, 'start_column': 1, 'end_line': 1, 'end_column': 4}]}
    assert item
    original.update(item)
    with pytest.raises(ts.TypeScriptError):
        ts._validate_navigation({'status': 'ok', 'data': {'methods': [original]}, 'diagnostics': []}, 'methods')


def test_incoming_rejects_invalid_scope():
    with pytest.raises(ts.TypeScriptError):
        ts._validate_navigation({'status':'ok','data':{'callers':[],'scope':{'tsconfig_path':'../x','searched_files':[], 'limits':[], 'omissions':[]}},'diagnostics':[]}, 'callers')


def test_existing_call_api_unchanged(tmp_path):
    fixture(tmp_path)
    caller = ts.outline(tmp_path / 'caller.ts')['callables'][0]['id']
    old = ts.list_called_callables(tmp_path / 'caller.ts', caller, repository_root=tmp_path)
    assert set(old['data']['calls'][0]) == {'path', 'id', 'name', 'signature'}
    assert Path(old['data']['calls'][0]['path']).is_absolute()
