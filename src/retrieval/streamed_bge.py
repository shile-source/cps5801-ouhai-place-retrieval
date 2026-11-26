"""Load the existing BGE backbone one tensor at a time; no new architecture/training."""
import json
from pathlib import Path
import sys
import math


def tensor_row_ranges(shape, element_size, budget_bytes=16*1024**2):
    """Bound host reads by first-axis rows; reject a row exceeding the budget."""
    if not shape or any(type(n) is not int or n<=0 for n in shape):
        raise ValueError('Positive nonscalar tensor shape required')
    row_bytes=math.prod(shape[1:])*element_size
    if row_bytes>budget_bytes or element_size not in (2,4):
        raise ValueError('A tensor row exceeds the bounded host-read budget')
    rows=max(1,budget_bytes//row_bytes)
    return [(start,min(shape[0],start+rows)) for start in range(0,shape[0],rows)]


def restore_generated_buffers(backbone, config, torch):
    """Materialize only standard generated XLM-R IDs, never learned parameters."""
    for name,buffer in list(backbone.named_buffers()):
        if not buffer.is_meta:
            continue
        suffix=name.rsplit('.',1)[-1]
        shape=(1,config.max_position_embeddings)
        if tuple(buffer.shape)!=shape or buffer.dtype!=torch.long:
            raise ValueError('Unsupported meta buffer: '+name)
        if suffix=='position_ids':value=torch.arange(shape[1],dtype=torch.long,device='cpu').expand(shape)
        elif suffix=='token_type_ids':value=torch.zeros(shape,dtype=torch.long,device='cpu')
        else:raise ValueError('Unsupported meta buffer: '+name)
        module=backbone
        parts=name.split('.')
        for part in parts[:-1]:module=getattr(module,part)
        module._buffers[parts[-1]]=value


def validate_tensor_catalog(expected,actual):
    if set(expected)!=set(actual):
        raise ValueError('Checkpoint tensor names differ from the standard backbone; no partial load')
    for name,shape in expected.items():
        if tuple(shape)!=tuple(actual[name]):
            raise ValueError('Checkpoint tensor shape mismatch: '+name)


def load_streamed_bge(checkpoint,device,precision,max_length):
    """Public AutoModel + standard CLS/normalisation; strict original parameter mapping.

    The adapter avoids a whole-checkpoint copy-on-write mapping and Transformers'
    aggregate loading path on Windows. All 391 original tensors must match before
    any parameter assignment. Only the loading strategy and module plumbing differ.
    """
    if device not in ('cuda','cuda:0'):
        raise ValueError('This guarded streamed loader requires CUDA device0')
    import torch
    from accelerate import init_empty_weights
    from accelerate.utils import set_module_tensor_to_device
    from safetensors import safe_open
    from transformers import AutoConfig,AutoModel,AutoTokenizer
    from sentence_transformers import SentenceTransformer,models
    checkpoint=Path(checkpoint)
    dtype={'float32':torch.float32,'float16':torch.float16}[precision]
    config=AutoConfig.from_pretrained(str(checkpoint),local_files_only=True,trust_remote_code=False)
    # include_buffers=True uses a device context in the installed Accelerate;
    # the default register-parameter interception can allocate a large CPU tensor
    # before replacing it with a meta parameter.
    with init_empty_weights(include_buffers=True):
        backbone=AutoModel.from_config(config,trust_remote_code=False)
    restore_generated_buffers(backbone,config,torch)
    expected={name:tuple(t.shape) for name,t in backbone.state_dict().items()}
    with safe_open(checkpoint/'model.safetensors',framework='pt',device='cpu',backend='pread') as reader:
        actual={name:tuple(reader.get_slice(name).get_shape()) for name in reader.keys()}
        # Older official XLM-R checkpoints persist generated position-ID buffers;
        # current Transformers does not. Accept only exact generated-buffer equality,
        # never an unexpected learned weight or an unchecked missing parameter.
        buffers=dict(backbone.named_buffers())
        for name in set(actual)-set(expected):
            if name not in buffers or name.rsplit('.',1)[-1] not in ('position_ids','token_type_ids'):
                raise ValueError('Unexpected checkpoint tensor: '+name)
            source_buffer=reader.get_tensor(name)
            if not torch.equal(source_buffer,buffers[name].cpu()):
                raise ValueError('Generated position buffer differs from source')
            expected[name]=tuple(buffers[name].shape)
            del source_buffer
        validate_tensor_catalog(expected,actual)
        for number,name in enumerate(expected,1):
            shape=tuple(actual[name])
            if name in buffers or not shape:
                tensor=reader.get_tensor(name).to('cuda:0')
            else:
                tensor=torch.empty(shape,device='cuda:0',dtype=dtype)
                view=reader.get_slice(name)
                with torch.no_grad():
                    for first,last in tensor_row_ranges(shape,4):
                        piece=view[first:last]
                        tensor[first:last].copy_(piece,non_blocking=False)
                        del piece
            set_module_tensor_to_device(backbone,name,'cuda:0',value=tensor,dtype=dtype)
            del tensor
            if number==1 or number%50==0 or number==len(expected):
                print(json.dumps({'stage':'streamed_tensor_load','loaded':number,'total':len(expected)}),file=sys.stderr,flush=True)
    if any(p.is_meta for p in backbone.parameters()):
        raise RuntimeError('Uninitialised backbone parameter; no inference')
    backbone.eval()
    tokenizer=AutoTokenizer.from_pretrained(str(checkpoint),local_files_only=True,trust_remote_code=False)

    class BackboneModule(torch.nn.Module):
        def __init__(self):
            super().__init__();self.auto_model=backbone;self.tokenizer=tokenizer;self.max_seq_length=max_length
        def tokenize(self,texts,**kwargs):
            return self.tokenizer(list(texts),padding=True,truncation=True,
                                  return_tensors='pt',max_length=self.max_seq_length)
        def forward(self,features,**kwargs):
            inputs={key:features[key] for key in ('input_ids','attention_mask','token_type_ids') if key in features}
            output=self.auto_model(**inputs,return_dict=False)
            features['token_embeddings']=output[0]
            return features
        def get_word_embedding_dimension(self): return config.hidden_size

    pooling=models.Pooling.load(str(checkpoint/'1_Pooling'))
    normalize=True
    if (checkpoint/'modules.json').is_file():
        spec=json.loads((checkpoint/'modules.json').read_text(encoding='utf-8'))
        types=[m['type'] for m in spec]
        allowed=['sentence_transformers.models.Transformer','sentence_transformers.models.Pooling']
        if types not in (allowed,allowed+['sentence_transformers.models.Normalize']):
            raise ValueError('Unsupported published module graph; no inferred replacement')
        if spec[0]['path']!='' or spec[1]['path']!='1_Pooling':
            raise ValueError('Unexpected module paths')
        normalize=len(types)==3
    layers=[BackboneModule(),pooling]+([models.Normalize()] if normalize else [])
    encoder=SentenceTransformer(modules=layers,device=device)
    encoder.eval()
    print(json.dumps({'stage':'streamed_encoder_constructed','tensor_count':len(expected),
                      'dtype':str(dtype),'dimension':config.hidden_size}),file=sys.stderr,flush=True)
    return encoder
