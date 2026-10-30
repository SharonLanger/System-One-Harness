# Laya score experiment

- Status: **success**
- Started: 2026-10-30T14:31:45+02:00 (+0200)
- UTC: 2026-10-30T12:31:45+00:00
- Requested model: `aac6fef/laya-typed-decisions-mlx`
- Requested temperature: SDK default
- Language: `en`
- Input text: 'The apple is small, about the size of a golf ball.'
- Questions: `{"apple_size": {"type": "score", "instructions": "How large is the apple?", "criteria": ["tiny", "small", "medium", "large"]}}`
- Raw response: `{"model": "laya-rl-agent", "answers": {"apple_size": {"type": "score", "score": 0.8279, "legend": {"0": "tiny", "1": "small", "2": "medium", "3": "large"}, "probabilities": {"0": 0.2925, "1": 0.6001, "2": 0.0946, "3": 0.0129}, "confidence": 0.3182, "answer_confidence": 0.6001, "action": {"act_probability": 1.0}}}, "usage": {"input_tokens": 46, "output_tokens": 0, "state_tokens": 13, "state_tokens_dropped": 0, "truncated": false, "truncated_questions": []}}`
- Outcome: `{"apple_size": {"type": "score", "score": 0.8279, "legend": {"0": "tiny", "1": "small", "2": "medium", "3": "large"}, "probabilities": {"0": 0.2925, "1": 0.6001, "2": 0.0946, "3": 0.0129}, "confidence": 0.3182, "answer_confidence": 0.6001, "action": {"act_probability": 1.0}}}`
- Processing: enrichment not_run; rules not_run
- Duration: 0.515 seconds
- Error: `null`
