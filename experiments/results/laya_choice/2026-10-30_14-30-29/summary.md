# Laya choice experiment

- Status: **success**
- Started: 2026-10-30T14:30:29+02:00 (+0200)
- UTC: 2026-10-30T12:30:29+00:00
- Requested model: `aac6fef/laya-typed-decisions-mlx`
- Requested temperature: SDK default
- Language: `en`
- Input text: 'I ate an apple.'
- Questions: `{"fruit": {"type": "choice", "instructions": "Which fruit is mentioned?", "criteria": {"apple": "apple", "pear": "pear"}}}`
- Response: `{"model": "laya-rl-agent", "answers": {"fruit": {"type": "choice", "choice": "apple", "probabilities": {"apple": 0.8865, "pear": 0.1135}, "confidence": 0.4895, "answer_confidence": 0.8865, "action": {"act_probability": 1.0}}}, "usage": {"input_tokens": 25, "output_tokens": 0, "state_tokens": 5, "state_tokens_dropped": 0, "truncated": false, "truncated_questions": []}}`
- Outcome: `{"answer": {"type": "choice", "choice": "apple", "probabilities": {"apple": 0.8865, "pear": 0.1135}, "confidence": 0.4895, "answer_confidence": 0.8865, "action": {"act_probability": 1.0}}}`
- Processing: enrichment not_run; rules not_run
- Duration: 0.645 seconds
- Error: `null`
