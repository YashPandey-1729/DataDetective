import math
import pandas as pd


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def generate_chart(result, args):
    rows = result.get('rows', [])
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError('Chart requires a nonempty tabular evidence result.')
    if len(rows) > 200:
        raise ValueError('Chart result exceeds 200 rows.')
    kind = args.chart_type
    if kind not in {'line', 'bar', 'scatter', 'histogram', 'heatmap'}:
        raise ValueError('Unsupported chart type.')
    layout = {'xaxis': {'title': {'text': args.x}}, 'yaxis': {'title': {'text': args.y or 'Count'}}}
    if kind == 'heatmap':
        numeric = [c for c in rows[0] if all(c in row and (row[c] is None or _number(row[c])) for row in rows)
                   and sum(_number(row.get(c)) for row in rows) >= 3]
        if len(numeric) < 2:
            raise ValueError('A correlation heatmap requires at least two numeric columns with three observations each.')
        matrix = pd.DataFrame(rows)[numeric].corr(min_periods=3)
        # Undefined correlation is null, never a fabricated zero.
        z = [[float(value) if pd.notna(value) and math.isfinite(value) else None for value in row] for row in matrix.to_numpy()]
        trace = {'type': 'heatmap', 'x': numeric, 'y': numeric, 'z': z, 'colorscale': 'Teal', 'zmin': -1, 'zmax': 1,
                 'colorbar': {'title': {'text': 'Pearson r'}}}
        layout = {'xaxis': {'title': {'text': 'Metric'}}, 'yaxis': {'title': {'text': 'Metric'}}}
    else:
        if not args.x or not all(args.x in row for row in rows):
            raise ValueError('Chart requires an existing x column in every result row.')
        x = [row[args.x] for row in rows]
        if any(value is not None and not isinstance(value, (str, int, float)) for value in x):
            raise ValueError('X values must be scalar labels or numbers.')
        if any(isinstance(value, (int, float)) and not _number(value) for value in x):
            raise ValueError('Chart numeric values must be finite and cannot be booleans.')
        if kind == 'histogram':
            if any(value is not None and not _number(value) for value in x) or not any(_number(value) for value in x):
                raise ValueError('Histogram requires finite numeric x values.')
            trace = {'type': 'histogram', 'x': x, 'marker': {'color': '#56d8e4'}}
        else:
            if not args.y or not all(args.y in row for row in rows):
                raise ValueError('An existing y column is required in every result row.')
            y = [row[args.y] for row in rows]
            if any(value is not None and not _number(value) for value in y) or not any(_number(value) for value in y):
                raise ValueError('Y values must contain finite numbers.')
            trace = {'type': 'bar' if kind == 'bar' else 'scatter', 'x': x, 'y': y,
                     'marker': {'color': '#56d8e4'}, 'name': args.y}
            if kind != 'bar':
                trace.update(mode='lines+markers' if kind == 'line' else 'markers', line={'color': '#56d8e4', 'width': 3})
    return {'title': args.title or 'Investigation evidence', 'data': [trace], 'layout': layout,
            'evidence_id': args.evidence_id, 'truncated': result.get('truncated', False)}
