# Versioned survey rules and reporting

## Purpose

FieldReady Local now supports package-owned, versioned survey rulesets. A batch is bound to
one ruleset at import time and retains that binding in SQLite. Revalidating the same batch
therefore cannot silently switch to a different rule version.

User-supplied arbitrary rule JSON is deliberately **not** supported in this milestone.
Rulesets ship with the application, are code-reviewed and are covered by answer-key tests.

## Packaged rulesets

### synthetic-household-v0.1

The original four-column compatibility demo remains available unchanged for regression
evidence.

Columns:

- record_id
- adults
- children
- household_size

### field-survey-v1.0.0

The richer hackathon demonstration contains 14 fictional field-survey records and checks:

- record identifier completeness and uniqueness;
- district and consent category validity;
- respondent-age completeness/range;
- adult, child and household count validity;
- household component totals;
- children-under-five consistency;
- interview-duration plausibility;
- conditional description for an "other" water source;
- GPS-accuracy quality.

The independent fixture expectation is:

- **14 records**;
- **17 findings**;
- **13 affected records**;
- severity: **3 critical, 9 high, 5 medium**;
- **80 evaluable** rule applications;
- **5 not-evaluable** rule applications.

The synthetic fixture intentionally contains no real respondent or institutional data.

## Supported rule operators

The M1 engine supports a deliberately small auditable set:

| Operator | Purpose |
| --- | --- |
| unique | Require a field value to be unique within the imported batch. |
| sum_equals | Compare a reported total with the sum of named component fields. |
| less_equal | Require one integer field not to exceed another. |
| between | Apply an inclusive numeric review range. |
| conditional_required | Require a field only when a stated condition is true. |

Column definitions separately support:

- string, integer and enum types;
- required fields;
- inclusive numeric minimum/maximum;
- allowed enum values;
- per-field severity.

Missing or type-invalid prerequisites are recorded as **not evaluable** rather than being
silently treated as passes.

## Finding evidence contract

Versioned findings contain:

- record ordinal and record identifier;
- stable rule ID;
- category;
- severity;
- field;
- observed value;
- expected value;
- deterministic explanation message;
- deterministic verification guidance.

The local language model never creates those facts. The browser and report use the evidence
returned by Python. For versioned rules, the deterministic explanation renderer can use the
package-owned message and verification text.

## SQLite migration

M0 databases use schema version 1. M1 migrates them to version 2 by adding a ruleset binding
to the batches table.

Existing batches receive the original ruleset ID:

synthetic-household-v0.1

Legacy batch identifiers remain unchanged. New non-legacy batch identifiers incorporate
both the source SHA-256 and the ruleset ID so the same source bytes cannot alias across
different rule versions.

## CLI examples

List packaged rulesets:

    python scripts/fieldready.py rulesets

Run the richer demo:

    python scripts/fieldready.py demo-field

Import a synthetic CSV against the richer ruleset:

    python scripts/fieldready.py import-csv .\my_synthetic.csv --ruleset field-survey-v1.0.0

Export a reviewed run:

    python scripts/fieldready.py export RUN_ID .\runtime\review-package

Use `--overwrite` only when intentionally replacing an existing package.

## Supervisor review package

The export contains exactly four generated files:

- summary.md
- findings.csv
- review_history.csv
- manifest.json

The manifest records SHA-256 hashes for the three evidence/report files.

The raw imported CSV is **not included**. The export contains only validation findings,
current review states and explicit review-event history. CSV output also prefixes obvious
spreadsheet-formula prefixes (`=`, `+`, `@`) to reduce formula-injection risk when opened
in spreadsheet software.

The browser export action does not accept a user-supplied filesystem path. It writes to the
application-controlled local exports directory beside the SQLite database. The model-facing
MCP server still exposes only its three read/validate tools and has no export or review-write
tool.

## Adding another ruleset

A future ruleset should not be added merely by dropping in an unreviewed JSON file. It should
include, in the same pull request:

1. a versioned packaged JSON specification;
2. a synthetic demonstration fixture;
3. an independently stated expected finding set;
4. severity/category count assertions;
5. non-evaluable-rule assertions;
6. clean-install package-data coverage;
7. documentation describing the intended questionnaire semantics.

This keeps rule changes inspectable, testable and defensible during judging.
