# Phase 1 — gateway transport

Parent remote commit b56283870d8693a42a1c4526024d626b14d9d95f; D01 verified-tree publication applies.

Added internal Context/Noop/Failure outcomes, typed validation errors, strict parser, one shared executable boundary, injectable dispatcher/logger, whole-input deadline, Python/native stdout isolation and one response serializer. Current active hook unchanged. The new gateway is not registered or released; its default dispatcher is introduced next phase.

Validation: `python3 -m pytest -q tests/test_hook_gateway_transport.py tests/test_gateway_migration_baseline.py`: 41 passed. Transport module has33cases; baseline8cases.

Mapping: A01–A15 covered by bad_arguments/bad_input/name_pair_unicode_and_limit plus process_noise_output_and_final_record; A16 process_input_deadline; E01–E07 process output, literal_output and broken_pipe_never_records_success; invalid results test S09; Unicode S10; process cases cover Context/Noop/Failure/exception propagation. Session validation S03 belongs Phase2, not generic transport. import_does_not_load_sdk proves no model import on gateway import.

Captured stdout is checked against literal text independently of application logs. Broken pipe records unknown partial bytes, never emission success. No real model or live Claude calls. D02 official schema and D03 root API remain unresolved release dependencies.
