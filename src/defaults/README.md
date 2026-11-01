# Shared defaults

Rules are named JSON objects with exactly one `question_type` (`choice`, `noul`,
`score`) and an ANDed `conditions` list. An empty list intentionally accepts every
structurally valid answer. Numeric thresholds are finite; supported fields are
`confidence`, `answer_confidence`, `action.act_probability`, plus
`probability_gap`/`normalized_entropy` on choice/score and
`distance_from_boundary` on noul. Missing response fields reject with `field_missing`.

Current policies are exact flattened copies of legacy blocks:

| Name | Type | Conditions in evaluation order |
| --- | --- | --- |
| ticket_department_default | choice | answer_confidence >= .9; probability_gap >= .5 |
| ticket_churn_default | noul | distance_from_boundary >= .1 |
| method_selection_default | choice | answer_confidence >= .5; probability_gap >= .15 |
| multiple_methods_default | noul | answer_confidence >= .5 |

Shared questions: `department`, `churn_risk`, `method_selection`,
`multiple_relevant`. Method selection contains only the existing sentinel until
block preparation adds candidates. Catalog names are identifiers, never paths.

To add a default, add one named JSON file to the matching directory and validate
with `Catalog()`. Names must be unique across all files in that catalog. References
resolve using package resources and return independent copies.
