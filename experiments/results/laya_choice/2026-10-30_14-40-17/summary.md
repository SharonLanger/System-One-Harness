# Laya Choice

Status: **success**.
This report records a direct adapter call. Enrichment and rule processing were not run.

## Requested configuration

model `aac6fef/laya-typed-decisions-mlx`; temperature SDK default; language `en`

## Input

```
I ate an apple.
```

## Questions and exact instructions

### fruit
Type: `choice`
Instructions:
```
Which fruit is mentioned?
```
Criteria:
```json
{
  "apple": "apple",
  "pear": "pear"
}
```

## Results

**fruit**
Selected: `apple`
Probabilities:
```json
{
  "apple": 0.8865,
  "pear": 0.1135
}
```
Confidence: `0.4895`
Answer confidence: `0.8865`
Action probability: `1.0`

## Run details

Started: 2026-10-30T14:40:17+02:00 (+0200); UTC: 2026-10-30T12:40:17+00:00.
Duration: 0.665 seconds.
Result directory: `/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/results/laya_choice/2026-10-30_14-40-17` (see `details.json` for the structured source of truth).
