import math


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _same(left, right):
    if _finite_number(left) and _finite_number(right):
        return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12)
    return type(left) is type(right) and left == right


def verify_finding(df, evidence, args, sql_runner):
    source = next((e for e in evidence if e['id'] == args.evidence_id), None)
    if not source or source['tool'] != 'execute_sql':
        raise ValueError('Verification requires successful SQL evidence.')
    if args.row is None or not args.field or args.expected is None or not args.claim:
        raise ValueError('Supply claim, evidence_id, row, field, and expected numeric value.')
    if not _finite_number(args.expected) or args.row < 0:
        raise ValueError('Verification requires a finite expected value and a nonnegative row.')
    try:
        original_row = source['result']['rows'][args.row]
        original = original_row[args.field]
    except (KeyError, IndexError, TypeError):
        raise ValueError('Verification cell is unavailable or nonnumeric.')
    if not _finite_number(original):
        raise ValueError('Verification cell must contain a finite number.')
    result = sql_runner(df, source['result']['sql'])
    # SQL does not promise row order without a complete ORDER BY. Match the
    # remaining row fields so group reorderings cannot verify the wrong cell.
    identity = {key: value for key, value in original_row.items() if key != args.field}
    candidates = [(index, row.get(args.field)) for index, row in enumerate(result['rows'])
                  if all(key in row and _same(value, row[key]) for key, value in identity.items())]
    values = [value for _, value in candidates]
    unambiguous = bool(values) and all(_finite_number(value) for value in values) and all(_same(values[0], value) for value in values)
    actual = values[0] if unambiguous else None
    matched = unambiguous and _same(actual, original) and _same(actual, args.expected)
    return {'claim': args.claim, 'evidence_id': source['id'], 'sql': result['sql'], 'row': args.row, 'field': args.field,
            'original': original, 'actual': actual, 'expected': args.expected, 'status': 'verified' if matched else 'inconclusive',
            'matched_row': candidates[0][0] if unambiguous else None, 'identity_fields': list(identity),
            'scope': 'Only the referenced numeric cell in an unambiguously matched result row was independently recomputed; this does not verify causality or other text in the claim.',
            'note': 'The row could not be matched unambiguously.' if not unambiguous else 'Result row matched using the other returned fields.'}
