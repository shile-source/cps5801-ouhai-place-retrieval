"""Private model worker. Reads live queries from stdin; never downloads weights."""
import json
import os
import sys
import time

def run_worker():
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    from src.data.load_candidates import load_candidates
    from src.retrieval.dense import SentenceEncoderRetriever
    from src.retrieval.bge_m3 import BGEM3DenseRetriever
    import torch
    start = time.perf_counter()
    if not torch.cuda.is_available():
        raise RuntimeError('Existing CUDA GPU is unavailable; no reinstall or model substitution attempted')
    torch.cuda.reset_peak_memory_stats()
    pois = load_candidates(sys.argv[1])
    backend = sys.argv[2] if len(sys.argv)>2 else 'encoder'
    if backend not in ('encoder','bge_m3'):
        raise ValueError('Unknown dense backend')
    retriever_class=BGEM3DenseRetriever if backend=='bge_m3' else SentenceEncoderRetriever
    load_options={'direct_gpu_load':True} if backend=='bge_m3' and os.environ.get('CPS5801_BGE_DIRECT_GPU_LOAD')=='1' else {}
    precision=os.environ.get('CPS5801_EMBEDDING_PRECISION','float32')
    load_options['precision']=precision
    if backend=='encoder' and os.environ.get('CPS5801_DENSE_LOADER')=='streamed':
        load_options['safe_streaming']=True
    if backend=='bge_m3':
        load_options['safetensors_backend']=os.environ.get('CPS5801_SAFETENSORS_BACKEND','mmap')
        load_options['loader']=os.environ.get('CPS5801_BGE_LOADER','transformers')
    print(json.dumps({'stage':'before_model_construction','backend':backend,'precision':precision}),file=sys.stderr,flush=True)
    with torch.inference_mode():
        retriever = retriever_class(pois, device='cuda', batch_size=4, max_length=128,**load_options)
    token_lengths=[len(ids) for ids in retriever.encoder.tokenizer(
        list(retriever.documents),add_special_tokens=True,truncation=False,padding=False)['input_ids']]
    print(json.dumps({'type':'ready','load_ms':(time.perf_counter()-start)*1000,
                      'gpu':torch.cuda.get_device_name(0),'dimension':retriever.embedding_dimension,
                      'backend':backend,'max_length':128,'batch_size':4,
                      'direct_gpu_load':load_options.get('direct_gpu_load',False),
                      'parameter_dtype':str(next(retriever.encoder.parameters()).dtype),
                      'safetensors_backend':('pread' if load_options.get('safe_streaming') else load_options.get('safetensors_backend','mmap')),
                      'loader':load_options.get('loader','streamed' if load_options.get('safe_streaming') else 'transformers'),
                      'maximum_document_tokens':max(token_lengths,default=0),
                      'documents_truncated_at_128':sum(n>128 for n in token_lengths)}), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        count=request.get('top_k',5)
        if type(count) is not int or not 1 <= count <= len(pois):
            raise ValueError('Invalid ranking size')
        allowed=request.get('eligible_ids')
        if allowed is not None:
            if not isinstance(allowed,list) or any(not isinstance(p,str) for p in allowed) or len(allowed)!=len(set(allowed)) or not set(allowed)<={p.poi_id for p in pois}:
                raise ValueError('Invalid common eligible pool')
            allowed=set(allowed)
        torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            rows = retriever.search(request['query'], count,predicate=(lambda p:p.poi_id in allowed) if allowed is not None else None)
        torch.cuda.synchronize()
        print(json.dumps({'type':'result','search_ms':(time.perf_counter()-start)*1000,
            'rows':[{'rank':r.rank,'poi_id':r.poi_id,'score':r.score,'model':r.model} for r in rows],
            'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated()}, ensure_ascii=False), flush=True)

def main():
    from src.retrieval.gpu_lease import GPULease
    with GPULease():
        run_worker()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'type':'error','error':str(exc)},ensure_ascii=False),flush=True)
        raise
