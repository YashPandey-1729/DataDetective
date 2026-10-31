"""PDF export from retained, validated report data; no model calls or external assets."""
from io import BytesIO
import json
import textwrap
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, CondPageBreak, Image, Preformatted, LongTable, TableStyle, KeepTogether


_render_lock=Lock()
_TEAL=colors.HexColor('#087f8c')


def _register_fonts():
    fonts=Path(matplotlib.get_data_path())/'fonts'/'ttf'
    for name,filename in [('DD','DejaVuSans.ttf'),('DD-Bold','DejaVuSans-Bold.ttf'),('DD-Mono','DejaVuSansMono.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name,str(fonts/filename)))


def _chart_image(chart):
    """Render the existing chart values, rather than asking a model to recreate them."""
    figure=Figure(figsize=(7,3.5),dpi=150,layout='constrained')
    FigureCanvasAgg(figure)
    axis=figure.add_subplot()
    axis.tick_params(labelsize=8)
    for trace in chart['data']:
        kind=trace['type']
        x=trace.get('x',[])
        if kind=='heatmap':
            matrix=np.array([[np.nan if value is None else value for value in row] for row in trace['z']],dtype=float)
            image=axis.imshow(np.ma.masked_invalid(matrix),cmap='BrBG',vmin=trace.get('zmin'),vmax=trace.get('zmax'),aspect='auto')
            xticks=list(range(0,len(x),max(1,(len(x)+11)//12)))
            yticks=list(range(0,len(trace['y']),max(1,(len(trace['y'])+11)//12)))
            axis.set_xticks(xticks,[str(x[i])[:40] for i in xticks],rotation=45,ha='right')
            axis.set_yticks(yticks,[str(trace['y'][i])[:40] for i in yticks])
            figure.colorbar(image,ax=axis)
        elif kind=='histogram':
            axis.hist([value for value in x if value is not None],bins='auto',color='#087f8c')
        elif kind in {'bar','scatter'}:
            y=[np.nan if value is None else value for value in trace['y']]
            # Positions keep repeated category labels distinct, just like retained rows.
            categorical=any(isinstance(value,str) or value is None for value in x)
            positions=list(range(len(x))) if categorical else x
            if kind=='bar': axis.bar(positions,y,color='#087f8c')
            elif 'lines' in trace.get('mode',''): axis.plot(positions,y,'o-',color='#087f8c',markersize=3)
            else: axis.scatter(positions,y,color='#087f8c',s=18)
            if categorical:
                ticks=list(range(0,len(x),max(1,(len(x)+11)//12)))
                axis.set_xticks(ticks,[str(x[i])[:40] for i in ticks],rotation=35,ha='right')
        else:
            raise ValueError('Unsupported static chart type.')
    layout=chart.get('layout',{})
    for coordinate in ('x','y'):
        title=layout.get(coordinate+'axis',{}).get('title',{})
        label=title.get('text') if isinstance(title,dict) else title
        if label: getattr(axis,'set_'+coordinate+'label')(str(label)[:100],fontsize=9)
    axis.spines[['top','right']].set_visible(False)
    output=BytesIO()
    figure.savefig(output,format='png',dpi=150)
    output.seek(0)
    return output


def pdf_report(state):
    # Matplotlib/font registration use process-wide state. Serialize exports to
    # keep concurrent downloads deterministic without blocking the event loop.
    with _render_lock:
        return _build_report(state)


def _build_report(state):
    _register_fonts()
    report=state['report']
    output=BytesIO()
    width=6.9*inch
    styles={
        'title':ParagraphStyle('title',fontName='DD-Bold',fontSize=25,leading=32,textColor=_TEAL,spaceAfter=16),
        'heading':ParagraphStyle('heading',fontName='DD-Bold',fontSize=14,leading=20,textColor=_TEAL,spaceBefore=16,spaceAfter=9,keepWithNext=True),
        'subheading':ParagraphStyle('subheading',fontName='DD-Bold',fontSize=10,leading=15,spaceBefore=9,spaceAfter=5,keepWithNext=True),
        'body':ParagraphStyle('body',fontName='DD',fontSize=9.5,leading=15,spaceAfter=7,wordWrap='CJK',alignment=TA_LEFT),
        'small':ParagraphStyle('small',fontName='DD',fontSize=8,leading=12,textColor=colors.HexColor('#526476'),spaceAfter=6,wordWrap='CJK'),
        'code':ParagraphStyle('code',fontName='DD-Mono',fontSize=7,leading=10,spaceAfter=10),
        'cell':ParagraphStyle('cell',fontName='DD',fontSize=8,leading=12,wordWrap='CJK'),
        'header':ParagraphStyle('header',fontName='DD-Bold',fontSize=8,leading=12,textColor=colors.white),
    }
    story=[]
    def paragraph(value,style='body'):
        # Uploaded labels and model prose are text, never ReportLab markup/links.
        clean=''.join(char for char in str(value) if char in '\n\t' or ord(char)>=32)
        return Paragraph(escape(clean).replace('\n','<br/>'),styles[style])
    def text(value,style='body'):
        story.append(paragraph(value,style))
    def section(title): text(title,'heading')
    def items(values,empty='None recorded.'):
        for value in values: text('- '+str(value))
        if not values: text(empty,'small')

    text('DataDetective AI','title')
    text('INVESTIGATION REPORT','small')
    text(state['question'],'subheading')
    text(f"Mode: {state['mode']} | Status: {state['status']}",'small')
    if state.get('model'): text('Model: '+state['model'],'small')
    text(f"Report type: {report.get('generation','model')} | Numeric cells recomputed: {report['verified_cells']}",'small')
    text('Investigation ID: '+state['id'],'small')
    if state.get('stop_reason') not in {None,'sufficient_evidence','offline_complete'}:
        text('INCOMPLETE INVESTIGATION - '+state['stop_reason'].replace('_',' '),'subheading')
    section('Summary')
    text(report['summary'])
    section('Findings')
    if not report['findings']: text('No findings were established.')
    for index,finding in enumerate(report['findings'],1):
        story.append(CondPageBreak(1.8*inch))
        text(f"{index}. {finding['kind'].capitalize()}",'subheading')
        text(finding['claim'])
        text('Sources: '+(', '.join(finding['evidence_ids']) or 'No analytical evidence'),'small')
        measurements=finding.get('measurements',[])
        if measurements:
            rows=[[paragraph(label,'header') for label in ['Metric','Value','Source / context']]]
            for measure in measurements:
                source=next((e for e in state['evidence'] if e['id']==measure['evidence_id']),None)
                context=measure.get('context',{})
                if source and source['tool']=='calculate_statistics' and measure.get('row') is None:
                    # These explanatory fields are retained once in the appendix.
                    context={key:value for key,value in context.items() if key not in {'note','method','assumptions'}}
                labels='; '.join(f'{key}: {value}' for key,value in context.items())
                provenance=f"{measure['verification']} | {measure['evidence_id']} | row: {measure.get('row')}"+('\n'+labels if labels else '')
                rows.append([paragraph(measure['field'],'cell'),paragraph(measure['value'],'cell'),paragraph(provenance,'cell')])
            table=LongTable(rows,colWidths=[1.65*inch,1.6*inch,3.65*inch],repeatRows=1,splitInRow=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),_TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f1f6f8'),colors.white]),
                ('LINEBELOW',(0,0),(-1,0),.5,_TEAL),('LEFTPADDING',(0,0),(-1,-1),7),
                ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.append(table)

    if state.get('charts'):
        section('Charts from computed evidence')
        text('Static views of retained chart data. Axis labels may be abbreviated or spaced for legibility. Interactive charts remain in the workspace.','small')
        for chart in state['charts']:
            text(chart['title'],'subheading')
            try:
                image=_chart_image(chart)
                story.append(Image(image,width=width,height=width/2))
            except (ValueError,TypeError,KeyError,OverflowError):
                text('This chart could not be rendered. Review its source evidence in the workspace.','small')
            text('Source: '+chart['evidence_id']+(' | Retained rows only; source was truncated.' if chart.get('truncated') else ''),'small')

    section('Numerical verification ledger')
    ledger=[entry for entry in state['evidence'] if entry['tool']=='verify_finding']
    if not ledger: text('No numerical cells were independently recomputed.','small')
    for entry in ledger:
        result=entry['result']
        text(f"{entry['id']}: {result['status']} - {result['field']} = {result.get('actual')}",'subheading')
        text(f"Source: {result['evidence_id']} | row: {result['row']} | expected: {result.get('expected')}",'small')
        text(result.get('scope','Recomputation checks the numeric cell only, not causality.'),'small')
    section('Limitations and uncertainty')
    items(report['limitations'])
    next_steps_start=len(story)
    section('Recommended next steps')
    items(report['next_steps'])
    story[next_steps_start:]=[KeepTogether(story[next_steps_start:])]
    if report.get('warnings'):
        section('Report checks')
        items(report['warnings'])
    if state.get('errors'):
        section('Execution notices')
        items(state['errors'])

    story.append(CondPageBreak(2.8*inch))
    section('Evidence appendix')
    text('Export previews are limited to 4,000 characters per result and 40,000 characters overall. Shortened previews are marked; full retained evidence remains available in the workspace.','small')
    remaining=40000
    for entry in state['evidence']:
        if remaining<=0:
            text('Additional evidence omitted from this PDF preview. Inspect the workspace for all retained results.','small')
            break
        text(f"{entry['id']} - {entry['tool']}",'subheading')
        result=entry['result']
        if entry['tool']=='profile_dataset':
            result={key:value for key,value in result.items() if key!='preview'}
        elif entry['tool']=='generate_chart':
            result={key:value for key,value in result.items() if key!='data'}
        payload=json.dumps(result,ensure_ascii=False,default=str)
        allowance=min(4000,remaining)
        shortened=len(payload)>allowance
        payload=payload[:allowance]
        remaining-=len(payload)
        lines=textwrap.wrap(payload,width=90,replace_whitespace=False,drop_whitespace=False,break_on_hyphens=False)
        for offset in range(0,len(lines),18):
            story.append(Preformatted('\n'.join(lines[offset:offset+18]),styles['code']))
        if shortened: text('Preview shortened for PDF export. Full retained result is available in the workspace.','small')

    def footer(canvas,document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d8e3e8'))
        canvas.line(document.leftMargin,.55*inch,document.pagesize[0]-document.rightMargin,.55*inch)
        canvas.setFont('DD',8)
        canvas.setFillColor(colors.HexColor('#526476'))
        canvas.drawString(document.leftMargin,.35*inch,'DataDetective AI | Computed evidence, with limitations')
        canvas.drawRightString(document.pagesize[0]-document.rightMargin,.35*inch,str(document.page))
        canvas.restoreState()
    document=SimpleDocTemplate(output,pagesize=(8.5*inch,11*inch),leftMargin=.8*inch,rightMargin=.8*inch,
        topMargin=.65*inch,bottomMargin=.8*inch,title='DataDetective AI investigation',author='DataDetective AI')
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
