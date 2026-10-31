# Dataset summary

200 cases / 100 families, two requests per family. Categories: explicit 50, semantic 40, distractor 30, same-name 20, absent 20, ambiguous 20, multiple 20. Selectable: 140; expected refusal: 60. Split: 120 development, 80 held-out, preserving families. Noise: 160 regular, 30 noisy, 10 heavy. Candidate sets: 50 cases each with 2, 4, 8, 16 callables.

Fixtures cover static methods, exported functions, callable expressions and async instance methods. Expected targets are distributed by rotating source order. Compiler-produced full outlines are embedded in cases.json with repository-relative paths, source hashes, ranges, locations and IDs. Dataset byte SHA-256 is recorded in protocol.json. Reauthor with prepare_dataset.py only when creating a new dataset version, not during resume.
