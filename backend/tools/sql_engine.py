import threading
import duckdb
import sqlglot
from sqlglot import exp
from backend.tools.profiler import records

# Deliberately narrow: every function outside this list is rejected by the parser.
ALLOWED_FUNCTIONS = {'SUM','AVG','MIN','MAX','COUNT','ROUND','ABS','COALESCE','NULLIF','CAST','TRY_CAST','CASE','TIMESTAMP_TRUNC',
                     'DATE_TRUNC','TIME_TO_STR','STRFTIME','EXTRACT','YEAR','MONTH','DAY','LOWER','UPPER',
                     'LENGTH','TRIM','STDDEV','STDDEV_SAMP','STDDEV_POP','VARIANCE','MEDIAN','QUANTILE_CONT',
                     'CORR','LAG','LEAD','ROW_NUMBER','RANK','DENSE_RANK','IF','GREATEST','LEAST','CONCAT',
                     'PERCENTILE_CONT','DATE_DIFF','DATEDIFF','TS_OR_DS_TO_DATE','TIME_STR_TO_TIME','STR_TO_TIME'}


def validate_sql(sql: str) -> str:
    if not sql or len(sql) > 8000:
        raise ValueError('SQL must contain 1–8,000 characters.')
    try:
        trees = sqlglot.parse(sql, read='duckdb')
    except sqlglot.errors.ParseError as exc:
        raise ValueError('Invalid DuckDB SELECT syntax.') from exc
    if len(trees) != 1 or not isinstance(trees[0], exp.Select):
        raise ValueError('Only one SELECT query is permitted (CTEs supported).')
    tree = trees[0]
    if any(node.args.get('recursive') for node in tree.find_all(exp.With)):
        raise ValueError('Recursive queries are disabled.')
    forbidden = {'Insert','Update','Delete','Create','Drop','Command','Copy','Into','Attach','Pragma','Set','Use','Transaction','Merge'}
    ctes = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    tables = list(tree.find_all(exp.Table))
    if len(tables) > 8:
        raise ValueError('Too many table references.')
    for node in tree.walk():
        if type(node).__name__ in forbidden:
            raise ValueError('Unsupported SQL operation.')
        if isinstance(node, exp.Table):
            if not isinstance(node.this, exp.Identifier) or node.db or node.catalog or node.name.lower() not in {'dataset', *ctes}:
                raise ValueError('Only the dataset table and local CTEs are accessible.')
        if isinstance(node, exp.Func):
            name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name().upper()
            if name not in ALLOWED_FUNCTIONS:
                raise ValueError(f'Function {name} is not approved.')
    return tree.sql(dialect='duckdb')


def execute_sql(df, sql: str) -> dict:
    safe_sql = validate_sql(sql)
    con = duckdb.connect(config={'memory_limit': '256MB', 'threads': '2', 'enable_external_access': 'false', 'temp_directory': '',
                                 'autoinstall_known_extensions': 'false', 'autoload_known_extensions': 'false'})
    stop_watchdog = threading.Event()
    def interrupt_expired_query():
        if not stop_watchdog.wait(4.0):
            # Keep interrupting until execution exits: a single interrupt can be
            # lost if its deadline falls between setup and analytical statements.
            while not stop_watchdog.is_set():
                con.interrupt()
                stop_watchdog.wait(.05)
    watchdog = threading.Thread(target=interrupt_expired_query, daemon=True)
    try:
        watchdog.start()
        con.register('_input', df)
        con.execute('CREATE TABLE dataset AS SELECT * FROM _input')
        con.unregister('_input')
        con.execute("SET max_expression_depth=100")
        con.execute('SET lock_configuration=true')
        result = con.execute(f'SELECT * FROM ({safe_sql}) AS bounded_result LIMIT 201').fetchdf()
        if len(set(result.columns)) != len(result.columns):
            raise ValueError('Query result columns must have unique aliases.')
        return {'sql': safe_sql, 'columns': list(result.columns), 'rows': records(result.head(200)),
                'row_count': min(len(result), 200), 'truncated': len(result) > 200}
    except duckdb.Error as exc:
        raise ValueError('Query failed: ' + str(exc)[:350]) from exc
    finally:
        stop_watchdog.set()
        if watchdog.is_alive():
            watchdog.join()
        con.close()
