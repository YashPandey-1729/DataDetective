"""Run the synthetic hackathon workflow against a running local backend.

No expected answers are sent to the agent. Offline results are checked afterwards.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['offline','agent'],default='offline')
    parser.add_argument('--format',choices=['csv','xlsx'],default='csv')
    args=parser.parse_args()
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
        def call(method,path,**kwargs):
            response=client.request(method,path,**kwargs)
            response.raise_for_status()
            return response.json()
        health=call('GET','/api/health')
        if args.mode=='agent' and not health['ai_configured']:
            raise SystemExit('Gemini is not configured. Set GEMINI_API_KEY in .env and restart FastAPI, or use --mode offline.')
        filename='retail_sales.'+args.format
        dataset=call('POST','/api/datasets',files={'file':(filename,(ROOT/filename).read_bytes())})
        image=call('POST','/api/images',files={'file':('revenue_decline.png',(ROOT/'revenue_decline.png').read_bytes(),'image/png')})
        state=call('POST','/api/investigations',json={'dataset_id':dataset['id'],'image_id':image['id'],'mode':args.mode,
            'question':'Why did revenue decline in February? Compare regions, then investigate categories and products in the region contributing most. Verify the numerical change.'})
        deadline=time.monotonic()+720
        while state['status'] in {'queued','running'} and time.monotonic()<deadline:
            time.sleep(.5)
            state=call('GET',f'/api/investigations/{state["id"]}')
        if state['status']!='completed':
            raise SystemExit(f"Investigation did not complete: {state['status']} / {state.get('stop_reason')} / {state['errors']}")
        counts=Counter(e['tool'] for e in state['evidence'])
        assert counts['execute_sql']>=2, 'Expected multiple real SQL actions.'
        assert state['charts'] and state['report']['verified_cells']>0
        if args.mode=='offline':
            expected=json.loads((ROOT/'expected_findings.json').read_text())
            rows=[row for e in state['evidence'] if e['tool']=='execute_sql' for row in e['result'].get('rows',[]) if 'pct_change' in row]
            assert rows and abs(rows[0]['delta']-expected['february_delta'])<.01
            assert abs(rows[0]['pct_change']-expected['february_pct_change'])<1e-8
            segments={row['segment']:row for e in state['evidence'] if e['tool']=='execute_sql' for row in e['result'].get('rows',[]) if 'segment' in row}
            categories={row['category']:row for e in state['evidence'] if e['tool']=='execute_sql' for row in e['result'].get('rows',[]) if 'category' in row}
            for row in expected['regional_comparison']:
                assert abs(segments[row['Region']]['delta']-row['delta'])<.01
            for row in expected['west_category_comparison']:
                assert abs(categories[row['Category']]['delta']-row['delta'])<.01
            assert state['image_context'] is None, 'Offline mode must not pretend to interpret images.'
        else:
            assert state['image_context'], 'Live Gemini image interpretation did not complete.'
        report=client.get(f'/api/investigations/{state["id"]}/report');report.raise_for_status()
        (ROOT/'latest_checked_report.md').write_text(report.text,encoding='utf-8')
        print(json.dumps({'status':state['status'],'mode':args.mode,'investigation_id':state['id'],
            'tools':dict(counts),'charts':len(state['charts']),'verified_cells':state['report']['verified_cells'],
            'report':'demo/latest_checked_report.md'},indent=2))


if __name__=='__main__': main()
