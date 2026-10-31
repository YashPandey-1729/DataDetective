import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from backend.agent.schemas import DatasetResponse, InvestigationRequest, InvestigationResponse, StatisticsRequest, AgentAction, ToolArgs
from backend.agent.investigator import InvestigationAgent
from backend.services import sessions
from backend.services.reporting import markdown_report
from backend.tools.data_loader import load_dataset, MAX_UPLOAD
from backend.tools.profiler import profile_dataset
from backend.tools.vision import validate_image
from backend.services.request_limits import RequestLimitsMiddleware
from backend.services.models import available_models, default_model, is_local_model
from backend.services.ollama import status as ollama_status
from backend.tools.statistics import calculate_statistics
from backend.tools.statistical_catalog import describe_statistics
from backend.agent.tool_contracts import validate_tool_arguments

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
tasks=set()
investigation_jobs={}
statistics_gate=asyncio.Semaphore(2)


@asynccontextmanager
async def lifespan(app):
    yield
    pending=list(tasks)
    for task in pending: task.cancel()
    await asyncio.gather(*pending,return_exceptions=True)
    tasks.clear()
    investigation_jobs.clear()


app=FastAPI(title='DataDetective AI',version='1.1.0',lifespan=lifespan)
app.add_middleware(RequestLimitsMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type'])


def google_configured():
    key=os.getenv('GEMINI_API_KEY','').strip()
    return bool(key) and key not in {'your-api-key-here','replace-with-your-key','your_api_key_here'}


@app.get('/api/health')
def health():
    local=ollama_status()
    models=available_models()
    for model in models:
        model['available']=local['ready'] if model['provider']=='ollama' else google_configured()
        model['reason']=local.get('message') if model['provider']=='ollama' else None if model['available'] else 'Set GEMINI_API_KEY in the root .env and restart the backend.'
    return {'status':'ok','ai_configured':any(model['available'] for model in models),
            'google_configured':google_configured(),'ollama':local,
            'model':default_model(),'models':models,'offline_available':True}


async def read_upload(file, limit):
    data=await file.read(limit+1)
    await file.close()
    if len(data)>limit:
        raise HTTPException(413,'Upload exceeds size limit.')
    return data


@app.get('/api/statistics/catalog')
def statistics_catalog(name:str=Query(default='all',max_length=120),category:str|None=Query(default=None,max_length=50)):
    return describe_statistics(name,category)


@app.post('/api/datasets/{dataset_id}/statistics')
async def dataset_statistics(dataset_id:str,request:StatisticsRequest):
    sessions.cleanup()
    if dataset_id not in sessions.datasets:raise HTTPException(404,'Dataset expired or unavailable. Upload it again.')
    args=ToolArgs(**request.model_dump())
    try:
        validate_tool_arguments(AgentAction(tool='calculate_statistics',explanation='Requested statistical calculation.',args=args))
        if statistics_gate.locked():raise HTTPException(429,'Statistical calculation capacity reached. Retry after active calculations finish.')
        async with statistics_gate:
            return await asyncio.to_thread(calculate_statistics,sessions.datasets[dataset_id].df,args)
    except ValueError as exc:raise HTTPException(422,str(exc)[:800]) from None
    except (ArithmeticError,TypeError) as exc:
        raise HTTPException(422,'Statistical calculation is undefined for these inputs or exceeds numerical precision. Review the function arguments and scale of the data.') from None


@app.post('/api/datasets',response_model=DatasetResponse)
async def upload_dataset(file:UploadFile=File(...)):
    sessions.cleanup()
    if len(sessions.datasets)>=12: raise HTTPException(429,'Session dataset limit reached. Restart the backend or wait for expiry.')
    data=await read_upload(file,MAX_UPLOAD)
    name=(file.filename or 'dataset').replace('\\','/').split('/')[-1][:180]
    try:
        df=await asyncio.to_thread(load_dataset,data,name)
        profile=await asyncio.to_thread(profile_dataset,df)
    except ValueError as exc: raise HTTPException(422,str(exc))
    if len(sessions.datasets)>=12: raise HTTPException(429,'Session dataset limit reached.')
    item=sessions.Dataset(sessions.new_id(),name,df,profile)
    sessions.datasets[item.id]=item
    return {'id':item.id,'name':name,'profile':profile}


@app.get('/api/demo/{name}',response_model=DatasetResponse)
async def demo_dataset(name:str):
    if name not in {'retail_sales','sensor_data','student_performance'}: raise HTTPException(404,'Unknown demo dataset.')
    sessions.cleanup()
    filename=name+'.csv'
    path=Path(__file__).resolve().parents[1]/'demo'/filename
    if not path.exists(): raise HTTPException(404,'Run python demo/generate.py first.')
    if len(sessions.datasets)>=12: raise HTTPException(429,'Dataset limit reached.')
    df=await asyncio.to_thread(load_dataset,path.read_bytes(),filename)
    profile=await asyncio.to_thread(profile_dataset,df)
    if len(sessions.datasets)>=12: raise HTTPException(429,'Session dataset limit reached.')
    item=sessions.Dataset(sessions.new_id(),filename,df,profile);sessions.datasets[item.id]=item
    return {'id':item.id,'name':filename,'profile':profile}


@app.post('/api/images')
async def upload_image(file:UploadFile=File(...)):
    sessions.cleanup()
    if len(sessions.images)>=20: raise HTTPException(429,'Image limit reached.')
    if Path(file.filename or '').suffix.lower() not in {'.png','.jpg','.jpeg'}: raise HTTPException(422,'Use PNG or JPEG.')
    data=await read_upload(file,5*1024*1024)
    try: data=await asyncio.to_thread(validate_image,data)
    except ValueError as exc: raise HTTPException(422,str(exc))
    if len(sessions.images)>=20: raise HTTPException(429,'Image limit reached.')
    import time
    id=sessions.new_id();sessions.images[id]={'bytes':data,'created':time.time()}
    return {'id':id,'status':'uploaded','note':'Image interpretation occurs during an AI investigation.'}


@app.post('/api/investigations',response_model=InvestigationResponse,status_code=202)
async def investigate(request:InvestigationRequest):
    sessions.cleanup()
    if request.dataset_id not in sessions.datasets: raise HTTPException(404,'Dataset expired or unavailable. Upload it again.')
    if request.image_id and request.image_id not in sessions.images: raise HTTPException(404,'Image expired or unavailable.')
    if request.mode=='agent' and request.model and request.model not in {option['id'] for option in available_models()}:
        raise HTTPException(422,'Unknown AI model. Choose a model listed by /api/health.')
    if request.mode=='agent':
        selected=request.model or default_model()
        if is_local_model(selected):
            local=await asyncio.to_thread(ollama_status)
            if not local['ready']: raise HTTPException(503,local['message'])
        elif not google_configured():
            raise HTTPException(503,'Set GEMINI_API_KEY in the root .env and restart the backend, or select local Gemma or Offline analytics.')
    if len(tasks)>=4 or len(sessions.investigations)>=40: raise HTTPException(429,'Investigation capacity reached. Wait for active work to finish or sessions to expire.')
    state=sessions.create_investigation(request)
    agent=InvestigationAgent(state)
    task=asyncio.create_task(agent.run())
    tasks.add(task)
    investigation_jobs[state['id']]=(task,agent)
    def finished(completed):
        tasks.discard(completed)
        investigation_jobs.pop(state['id'],None)
        # Cancellation before the coroutine's first turn never reaches run().
        if completed.cancelled(): agent.mark_cancelled()
    task.add_done_callback(finished)
    return state


@app.get('/api/investigations/{id}',response_model=InvestigationResponse)
async def investigation(id:str):
    sessions.cleanup()
    if id not in sessions.investigations: raise HTTPException(404,'Investigation not found or expired.')
    sessions.investigations[id]['accessed']=time.time()
    return sessions.investigations[id]


@app.post('/api/investigations/{id}/cancel',response_model=InvestigationResponse)
async def cancel_investigation(id:str):
    state=await investigation(id)
    if state['status'] not in {'queued','running'}:
        return state
    job=investigation_jobs.get(id)
    if not job or job[0].done():
        raise HTTPException(409,'This investigation has no active job. Refresh its progress before retrying.')
    task,agent=job
    agent.mark_cancelled(user_requested=True)
    task.cancel()
    return state


@app.get('/api/investigations/{id}/report',response_class=PlainTextResponse)
async def report(id:str):
    state=await investigation(id)
    if not state['report']: raise HTTPException(409,'Report is not ready.')
    return PlainTextResponse(markdown_report(state),headers={'Content-Disposition':f'attachment; filename="investigation-{id[:8]}.md"'})
