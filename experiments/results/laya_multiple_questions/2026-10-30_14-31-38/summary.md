# Laya multiple questions experiment

- Status: **success**
- Started: 2026-10-30T14:31:38+02:00 (+0200)
- UTC: 2026-10-30T12:31:38+00:00
- Requested model: `aac6fef/laya-typed-decisions-mlx`
- Requested temperature: SDK default
- Language: `en`
- Input text: 'I ate a small red apple.'
- Questions: `{"fruit": {"type": "choice", "instructions": "Which fruit is mentioned?", "criteria": {"apple": "apple", "pear": "pear"}}, "fruit_mentioned": {"type": "noul", "instructions": "Is a fruit mentioned?"}, "apple_size": {"type": "score", "instructions": "How large is the apple?", "criteria": ["tiny", "small", "medium", "large"]}}`
- Raw response: `{"model": "laya-rl-agent", "answers": {"fruit": {"type": "choice", "choice": "apple", "probabilities": {"apple": 0.914, "pear": 0.086}, "confidence": 0.5772, "answer_confidence": 0.914, "action": {"act_probability": 1.0}}, "fruit_mentioned": {"type": "noul", "noul": 0.6623, "confidence": 0.6623, "answer_confidence": 0.6623, "action": {"act_probability": 1.0}}, "apple_size": {"type": "score", "score": 0.993, "legend": {"0": "tiny", "1": "small", "2": "medium", "3": "large"}, "probabilities": {"0": 0.1945, "1": 0.6316, "2": 0.1603, "3": 0.0136}, "confidence": 0.307, "answer_confidence": 0.6316, "action": {"act_probability": 1.0}}}, "usage": {"input_tokens": 105, "output_tokens": 0, "state_tokens": 7, "state_tokens_dropped": 0, "truncated": false, "truncated_questions": []}}`
- Outcome: `{"fruit": {"type": "choice", "choice": "apple", "probabilities": {"apple": 0.914, "pear": 0.086}, "confidence": 0.5772, "answer_confidence": 0.914, "action": {"act_probability": 1.0}}, "fruit_mentioned": {"type": "noul", "noul": 0.6623, "confidence": 0.6623, "answer_confidence": 0.6623, "action": {"act_probability": 1.0}}, "apple_size": {"type": "score", "score": 0.993, "legend": {"0": "tiny", "1": "small", "2": "medium", "3": "large"}, "probabilities": {"0": 0.1945, "1": 0.6316, "2": 0.1603, "3": 0.0136}, "confidence": 0.307, "answer_confidence": 0.6316, "action": {"act_probability": 1.0}}}`
- Processing: enrichment not_run; rules not_run
- Duration: 1.223 seconds
- Error: `null`
