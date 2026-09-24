# ClearCSV sample expected behavior

`customers-dirty.csv` is synthetic and intentionally contains review candidates. Import must preserve every value as text; no suggestion is applied automatically.

## Verifiable locations

- Rows 1 and 27 (CSV data records 2 and 28): exact duplicate; the later row may receive an `exclude_row` proposal, while row 1 remains the reference.
- Rows 3 and 28: ambiguous dates (`01/02/2026` and `03/04/2026`) remain unchanged and require review.
- Rows 5, 10, and 11: blank or whitespace-only cells are findings; no missing value is invented.
- Row 4: malformed email is suspicious; no domain or user is generated.
- Row 24: leading space in city is preserved until a human accepts a text normalization proposal.
- Row 29: formula-looking note is data, never evaluated.
- Row 30: malicious-looking note is untrusted data, never treated as an instruction.
- Row 3: quoted multiline note is imported as one cell.
- IDs such as `00001` and `00027` retain leading zeroes in original and faithful export.
- Rows 34 and 35 provide a possible approximate duplicate context; any AI suggestion is advisory only.

## AI invariants

Fixture mode must be visibly labeled and may return no AI proposals. Live mode may suggest only supplied stable row/column IDs, must match immutable original values, and must never edit protected-looking email fields or exclude a row based only on approximate similarity. Invalid provider output must leave deterministic findings and the review engine usable.
