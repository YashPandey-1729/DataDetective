import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from backend.agent.schemas import DatasetResponse, InvestigationRequest, InvestigationResponse
from backend.agent.investigator import InvestigationAgent
from backend.services import sessions
from backend.services.reporting import markdown_report
from backend.tools.data_loader import load_dataset, MAX_UPLOAD
from backend.tools.profiler import profile_dataset
from backend.tools.vision import validate_image
from backend.services.request_limits import RequestLimitsMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
tasks=set()


@asynccontextmanager
async def lifespan(app):
    yield
    pending=list(tasks)
    for task in pending: task.cancel()
    await asyncio.gather(*pending,return_exceptions=True)
    tasks.clear()


app=FastAPI(title='DataDetective AI',version='1.1.0',lifespan=lifespan)
app.add_middleware(RequestLimitsMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type'])


@app.get('/api/health')
def health():
    key=os.getenv('GEMINI_API_KEY','').strip()
    return {'status':'ok','ai_configured':bool(key) and key not in {'your-api-key-here','replace-with-your-key','your_api_key_here'},
            'model':os.getenv('GEMINI_MODEL','gemini-flash-latest'),'offline_available':True}


async def read_upload(file, limit):
    data=await file.read(limit+1)
    await file.close()
    if len(data)>limit:
        raise HTTPException(413,'Upload exceeds size limit.')
    return data


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
    if request.mode=='agent' and not health()['ai_configured']: raise HTTPException(503,'Set GEMINI_API_KEY in the root .env and restart the backend, or select Offline analytics.')
    if len(tasks)>=4 or len(sessions.investigations)>=40: raise HTTPException(429,'Investigation capacity reached. Wait for active work to finish or sessions to expire.')
    state=sessions.create_investigation(request)
    task=asyncio.create_task(InvestigationAgent(state).run());tasks.add(task);task.add_done_callback(tasks.discard)
    return state


@app.get('/api/investigations/{id}',response_model=InvestigationResponse)
async def investigation(id:str):
    sessions.cleanup()
    if id not in sessions.investigations: raise HTTPException(404,'Investigation not found or expired.')
    sessions.investigations[id]['accessed']=time.time()
    return sessions.investigations[id]


@app.get('/api/investigations/{id}/report',response_class=PlainTextResponse)
async def report(id:str):
    state=await investigation(id)
    if not state['report']: raise HTTPException(409,'Report is not ready.')
    return PlainTextResponse(markdown_report(state),headers={'Content-Disposition':f'attachment; filename="investigation-{id[:8]}.md"'})
