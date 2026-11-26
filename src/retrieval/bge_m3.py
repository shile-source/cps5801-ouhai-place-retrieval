"""Pinned BGE-M3 dense/CLS output only; no sparse or multi-vector fusion."""
import json
import importlib.util
from pathlib import Path
from .dense import SentenceEncoderRetriever
from .safetensor_io import transformers_safetensors_backend

MODEL_ID='BAAI/bge-m3'
REVISION='694b61558aea4ae2512ed8d0e189d5cf8adc2259'
MODEL_PATH=Path(__file__).resolve().parents[2]/'models/bge-m3'/REVISION


class BGEM3DenseRetriever(SentenceEncoderRetriever):
    model_name=MODEL_ID
    embedding_dimension=1024

    def __init__(self,*args,direct_gpu_load=False,safetensors_backend='mmap',loader='transformers',**kwargs):
        if type(direct_gpu_load) is not bool:
            raise ValueError('Direct GPU loading must be an explicit boolean')
        self.direct_gpu_load=direct_gpu_load
        if safetensors_backend not in ('mmap','pread'):
            raise ValueError('Explicit supported safetensors backend required')
        self.safetensors_backend=safetensors_backend
        if loader not in ('transformers','streamed'):
            raise ValueError('Explicit supported BGE loader required')
        if loader=='streamed' and safetensors_backend!='pread':
            raise ValueError('Streamed loading requires pread')
        self.loader=loader
        super().__init__(*args,**kwargs)

    def _loader_context(self):
        return transformers_safetensors_backend(self.safetensors_backend)

    def _build_encoder(self,checkpoint,device):
        if self.loader=='streamed':
            from .streamed_bge import load_streamed_bge
            return load_streamed_bge(checkpoint,device,self.precision,self.max_length)
        return super()._build_encoder(checkpoint,device)

    def _loader_kwargs(self,device):
        options=super()._loader_kwargs(device)
        if not self.direct_gpu_load:
            return options
        if device not in ('cuda','cuda:0'):
            raise ValueError('Explicit direct loading requires CUDA device0')
        if importlib.util.find_spec('accelerate') is None:
            raise RuntimeError('Direct GPU load helper is not installed; no automatic installation')
        return {**options,'device_map':{'':'cuda:0'}}

    def _checkpoint_path(self):
        if not (MODEL_PATH/'deployment_manifest.json').is_file():
            raise FileNotFoundError('Verified local BGE-M3 deployment missing; no automatic download')
        manifest=json.loads((MODEL_PATH/'deployment_manifest.json').read_text(encoding='utf-8'))
        if manifest.get('status')!='download_complete_content_verified' or manifest.get('revision')!=REVISION:
            raise ValueError('BGE-M3 download is incomplete or revision differs')
        pool=json.loads((MODEL_PATH/'1_Pooling/config.json').read_text(encoding='utf-8'))
        if pool.get('word_embedding_dimension')!=1024 or pool.get('pooling_mode_cls_token') is not True or pool.get('pooling_mode_mean_tokens') is not False:
            raise ValueError('BGE-M3 requires published CLS pooling configuration')
        return MODEL_PATH
