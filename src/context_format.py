"""Present validated collector context without changing its source or metadata."""
import os
import re


# Only known gap categories are presented. Collector messages may contain
# internal details; the complete original objects remain available in logs.
_GAP_NOTES = {
    'caller_coverage': 'Callers and ambient context are not exhaustively collected.',
    'module_side_effects': 'Module initialization and side effects are not reconstructed.',
    'depth_limit': 'Some supporting declarations were omitted at the collection depth limit.',
    'size_limit': 'Some supporting declarations were omitted at the source collection size limit.',
    'missing_module': 'Some imported modules could not be resolved.',
    'external_dependency': 'External package implementations are not collected.',
    'declaration_only': 'Some references have declarations without collected implementations.',
    'dynamic_reference': 'Some computed or indirect references could not be resolved.',
    'unresolved_reference': 'Some references have no resolved supporting declaration.',
    'closure_capture': 'Some outer local declarations or captured values are not collected.',
    'inherited_dispatch': 'Some inherited implementation targets are not collected.',
    'mutable_state': 'Declaration text does not establish runtime values or later writes.',
    'class_state': 'Class initialization, writes, inheritance and dispatch remain partial.',
    'namespace_context': 'Namespace operations and foreign property targets remain partial.',
    'unsupported_reexport_route': 'Some import or re-export routes could not be established.',
    'unsupported_dependency': 'Some supporting source could not be collected.',
    'source_load_limit': 'Some source files exceeded the source loading limit.',
    'outside_repository': 'Some supporting source lies outside the repository boundary.',
    'project_references': 'Referenced projects are not traversed separately.',
    'config_error': 'Project configuration could not be used for cross-file resolution.',
    'missing_config': 'No project configuration was available for module resolution.',
    'project_membership': 'The selected file is outside the configured project; only local context is collected.',
    'unsupported_resolution_mode': 'The project module resolution mode is unsupported; only local context is collected.',
}


def _source_block(path, location, code):
    """Keep source intact, including backticks and original line endings."""
    first = location['line']
    breaks = len(re.findall(r'\r\n|[\r\n\u2028\u2029]', code))
    if code.endswith(('\r', '\n', '\u2028', '\u2029')):
        breaks -= 1
    last = first + max(0, breaks)
    return f'{path} (lines {first}–{last})\n{code}'


def format_context(extracted_context, *, project_root, include_imports=True,
                   include_dependencies=True, include_notes=True) -> str:
    """Render selected source and optional supporting context, without mutation.

    project_root is the validated absolute analysis root, never the process cwd.
    This pure presentation layer does not read or validate filesystem state.
    Input is the validated collector object. Imports and other supporting
    declarations have independent presentation switches; neither changes what
    the collector gathers or retains for diagnostics.
    """
    base = os.fspath(project_root)
    if not os.path.isabs(base):
        raise ValueError('project_root must be absolute')
    selected = extracted_context['callable']
    parts = ['Selected TypeScript context (partial).', 'Selected method',
             _source_block(os.path.relpath(extracted_context['path'], base), selected['location'],
                           extracted_context['code'])]
    declarations, imports = [], []
    seen = {(extracted_context['path'], selected['start'], selected['end'])}
    for item in extracted_context['dependencies']:
        identity = (item['path'], item['start'], item['end'])
        if identity in seen:
            continue
        seen.add(identity)
        if item['kind'] == 'ImportDeclaration':
            if include_imports:
                imports.append(_source_block(os.path.relpath(item['path'], base), item['location'], item['code']))
        elif include_dependencies:
            declarations.append(_source_block(os.path.relpath(item['path'], base), item['location'], item['code']))
    if declarations:
        parts.extend(['Supporting declarations', *declarations])
    if imports:
        parts.extend(['Imports', *imports])
    if include_notes:
        notes = list(dict.fromkeys(_GAP_NOTES.get(
            gap['code'], 'Some additional context could not be collected.')
            for gap in extracted_context['gaps']))
        if notes:
            parts.extend(['Context notes', '\n'.join(notes)])
    return '\n\n'.join(parts)
