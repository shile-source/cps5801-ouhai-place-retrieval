"""Synthetic tiny XLM-R checkpoint: streamed vs standard CLS pipeline, not research."""
from datetime import datetime
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run_fixture(emit=True):
    import numpy as np
    import torch
    from transformers import XLMRobertaConfig,XLMRobertaModel,AutoTokenizer
    from sentence_transformers import SentenceTransformer,models
    from src.retrieval.streamed_bge import load_streamed_bge
    torch.manual_seed(5801)
    output=ROOT/'outputs'/('synthetic_loader_equivalence_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    output.mkdir()
    checkpoint=output/'synthetic_tiny_checkpoint'
    checkpoint.mkdir()
    source=ROOT/'models/bge-m3/694b61558aea4ae2512ed8d0e189d5cf8adc2259'
    tokenizer=AutoTokenizer.from_pretrained(str(source),local_files_only=True)
    config=XLMRobertaConfig(vocab_size=tokenizer.vocab_size,hidden_size=8,num_hidden_layers=1,
            num_attention_heads=2,intermediate_size=16,max_position_embeddings=132)
    tiny=XLMRobertaModel(config)
    assert sum(p.numel() for p in tiny.parameters())<3_000_000
    tiny.save_pretrained(checkpoint,safe_serialization=True)
    tokenizer.save_pretrained(checkpoint)
    texts=['合成阅读样本','合成运动样本','synthetic multilingual fixture']
    cases=[]
    (checkpoint/'1_Pooling').mkdir()
    for pooling,normalize in [('cls',True),('mean',False)]:
        pool=models.Pooling(8,pooling_mode_cls_token=pooling=='cls',pooling_mode_mean_tokens=pooling=='mean')
        pool.save(str(checkpoint/'1_Pooling'))
        specs=[{'idx':0,'name':'0','path':'','type':'sentence_transformers.models.Transformer'},
               {'idx':1,'name':'1','path':'1_Pooling','type':'sentence_transformers.models.Pooling'}]
        if normalize:
            specs.append({'idx':2,'name':'2','path':'2_Normalize','type':'sentence_transformers.models.Normalize'})
        (checkpoint/'modules.json').write_text(json.dumps(specs),encoding='utf-8')
        layers=[models.Transformer(str(checkpoint),max_seq_length=128),pool]
        standard=SentenceTransformer(modules=layers+([models.Normalize()] if normalize else []),device='cuda')
        streamed=load_streamed_bge(checkpoint,'cuda','float32',128)
        # Disable encode-time normalisation here so the published module graph is tested.
        first=standard.encode(texts,normalize_embeddings=False,convert_to_numpy=True,show_progress_bar=False)
        second=streamed.encode(texts,normalize_embeddings=False,convert_to_numpy=True,show_progress_bar=False)
        original=standard[0].auto_model.state_dict()
        copied=streamed[0].auto_model.state_dict()
        assert set(original)==set(copied)
        max_weight=max(float((original[n]-copied[n]).abs().max().cpu()) for n in original)
        max_embedding=float(np.max(np.abs(first-second)))
        assert max_weight==0
        assert np.allclose(first,second,atol=1e-6,rtol=1e-6)
        cases.append({'pooling':pooling,'normalize_module':normalize,
                      'maximum_parameter_difference':max_weight,'maximum_embedding_difference':max_embedding})
        tensor_count=len(original)
        del standard,streamed,original,copied,layers
    report={'purpose':'synthetic_loader_equivalence_NOT_real_retrieval_metrics','seed':5801,
            'parameters':sum(p.numel() for p in tiny.parameters()),'tensor_count':tensor_count,
            'cases':cases,
            'maximum_parameter_difference':max(c['maximum_parameter_difference'] for c in cases),
            'maximum_embedding_difference':max(c['maximum_embedding_difference'] for c in cases),
            'tolerance':1e-6,'passed':True,'real_checkpoint_reencoded':False,'new_human_labels':0}
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if emit:print(json.dumps({'output':str(output),**report}),flush=True)
    return {'output':str(output),**report}


def main():
    from src.retrieval.gpu_lease import GPULease
    with GPULease():run_fixture()


if __name__=='__main__':main()
