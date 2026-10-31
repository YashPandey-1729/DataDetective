import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from backend.services.models import default_model


def new_id():
    return uuid.uuid4().hex


@dataclass
class Dataset:
    id: str
    name: str
    df: Any
    profile: dict
    created: float = field(default_factory=time.time)


datasets: dict[str, Dataset] = {}
images: dict[str, dict] = {}
investigations: dict[str, dict] = {}


def cleanup():
    cutoff = time.time() - 7200
    active=[s for s in investigations.values() if s['status'] in {'queued','running'}]
    pinned_datasets={s['dataset_id'] for s in active}
    pinned_images={s.get('image_id') for s in active}
    for collection in (datasets, images, investigations):
        for key, value in list(collection.items()):
            if (collection is datasets and key in pinned_datasets) or (collection is images and key in pinned_images):
                continue
            created = value.created if isinstance(value, Dataset) else value.get('accessed',value['created'])
            if created < cutoff and (not isinstance(value, dict) or value.get('status') not in {'queued','running'}):
                del collection[key]


def create_investigation(request):
    state = {'id': new_id(), 'dataset_id':request.dataset_id, 'question':request.question,
             'image_id':request.image_id,'image_context':None,'mode':request.mode,
             'model':(request.model or default_model()) if request.mode=='agent' else None,'status':'queued',
             'plan':[],'events':[],'evidence':[],'findings':[],'charts':[],'report':None,'errors':[],'created':time.time(),
             'accessed':time.time(),'stop_reason':None}
    investigations[state['id']] = state
    return state
