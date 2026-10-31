"""Reproducible synthetic demo assets. Expected answers use Pandas, independently of DuckDB."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def generate():
    rng=np.random.default_rng(42)
    rows=[]; transaction=1
    products={'Electronics':[('Laptop',780),('Headphones',95)],'Home':[('Desk lamp',45),('Chair',140)],'Lifestyle':[('Backpack',65),('Bottle',22)]}
    for month in range(1,5):
        for day in range(1,29):
            for region in ['West','East','North','South']:
                for category,items in products.items():
                    # A synthetic supply constraint affects West Electronics in February.
                    count=1 if month==2 and region=='West' and category=='Electronics' else 4
                    for _ in range(count):
                        product,price=items[int(rng.integers(0,2))]
                        qty=int(rng.integers(1,5)); unit=round(price*rng.uniform(.92,1.08),2)
                        rows.append([f'T{transaction:06}',f'2026-{month:02}-{day:02}',region,product,category,qty,unit,round(unit*qty,2)])
                        transaction+=1
    retail=pd.DataFrame(rows,columns=['Transaction ID','Date','Region','Product','Category','Quantity','Unit Price','Revenue'])
    retail.to_csv(ROOT/'retail_sales.csv',index=False)
    retail.head(300).to_excel(ROOT/'retail_preview.xlsx',index=False)
    monthly=retail.assign(Month=retail.Date.str[:7]).groupby('Month').Revenue.sum()
    jan=retail[retail.Date.str.startswith('2026-01')]; feb=retail[retail.Date.str.startswith('2026-02')]
    regional=pd.concat([jan.groupby('Region').Revenue.sum().rename('January'),feb.groupby('Region').Revenue.sum().rename('February')],axis=1)
    regional['delta']=regional.February-regional.January
    west=pd.concat([jan[jan.Region=='West'].groupby('Category').Revenue.sum().rename('January'),feb[feb.Region=='West'].groupby('Category').Revenue.sum().rename('February')],axis=1)
    west['delta']=west.February-west.January
    expected={'synthetic':True,'seed':42,'rows':len(retail),'monthly_revenue':monthly.round(2).to_dict(),
              'february_delta':round(monthly.iloc[1]-monthly.iloc[0],2),'february_pct_change':(monthly.iloc[1]/monthly.iloc[0]-1)*100,
              'regional_comparison':json.loads(regional.round(2).reset_index().to_json(orient='records')),
              'west_category_comparison':json.loads(west.round(2).reset_index().to_json(orient='records')),
              'generator_context':'West Electronics transaction frequency was reduced in February. The dataset alone shows contributions, not a proven causal supply constraint.',
              'period_caveat':'Synthetic months each contain days 1–28 only; equal windows, not complete calendar months.'}
    (ROOT/'expected_findings.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
    plt.style.use('dark_background')
    fig,ax=plt.subplots(figsize=(10,4.8));fig.set_facecolor('#101827');ax.set_facecolor('#101827')
    ax.plot(monthly.index,monthly.values,marker='o',color='#66d9e1',linewidth=3)
    ax.axvspan(.75,1.25,color='#e993a9',alpha=.1)
    ax.annotate('Investigate February decline',xy=(1,monthly.iloc[1]),xytext=(1.2,monthly.max()*.96),arrowprops={'arrowstyle':'->','color':'#efb1c0'},color='#efb1c0')
    ax.set_title('Retail revenue · synthetic demo',loc='left',pad=20);ax.set_ylabel('Revenue (synthetic currency units)');ax.set_xlabel('Month · each period covers days 1–28')
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.12)
    fig.tight_layout();fig.savefig(ROOT/'revenue_decline.png',dpi=160);plt.close(fig)
    timestamps=pd.date_range('2026-01-01',periods=2400,freq='h')
    measurements=22+2*np.sin(np.arange(2400)/24*2*np.pi)+rng.normal(0,.45,2400)
    measurements[[45,601,1202,1800]]= [43,45,-5,51]; measurements[[17,101,503,800,1700]]=np.nan
    pd.DataFrame({'Timestamp':timestamps,'Sensor ID':[f'S-{i%4+1}' for i in range(2400)],'Measurement':measurements.round(3)}).to_csv(ROOT/'sensor_data.csv',index=False)
    n=900; study=rng.uniform(.5,7,n); attendance=rng.uniform(55,100,n)
    pd.DataFrame({'Student ID':[f'ST-{i//3:04}' for i in range(n)],'Subject':np.tile(['Mathematics','Science','Literature'],n//3),
        'Score':np.clip(20+study*5+attendance*.35+rng.normal(0,8,n),0,100).round(1),
        'Attendance':attendance.round(1),'Study hours':study.round(2),'Practice sessions':rng.integers(0,8,n)}).to_csv(ROOT/'student_performance.csv',index=False)
    print(f'Generated {len(retail):,} retail rows, 2,400 sensor rows, 900 student rows and chart reference.')


if __name__=='__main__': generate()
