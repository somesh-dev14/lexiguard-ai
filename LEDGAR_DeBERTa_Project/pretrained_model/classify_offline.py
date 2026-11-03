"""Offline CPU inference for a complete checkpoint and an explicit label map."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True,help='Existing complete local checkpoint directory; no download is attempted.')
    parser.add_argument('--input',default=str(Path(__file__).parent/'example_input.json'))
    parser.add_argument('--labels',default=str(Path(__file__).parent/'labels.json'))
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    for k,v in {'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false','CUDA_VISIBLE_DEVICES':''}.items():os.environ[k]=v
    model_path=Path(args.model)
    spec=json.loads(Path(args.labels).read_text())
    data=json.loads(Path(args.input).read_text())
    for name in ['config.json','model.safetensors','tokenizer.json','tokenizer_config.json']:
        if not (model_path/name).is_file():raise SystemExit('Required local file absent: '+name)
    from transformers import AutoConfig,AutoTokenizer
    config=AutoConfig.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
    assert config.num_labels==len(spec['labels']), 'Label count does not match checkpoint'
    enc=tokenizer(data['text'],data.get('text_pair'),truncation=True,max_length=spec['max_length'],return_tensors='pt')
    if args.validate_only:
        print(json.dumps({'validation':'passed','labels':config.num_labels,'tokens':int(enc['input_ids'].shape[-1]),'model_loaded':False,'downloads':0}))
        return
    import torch
    from transformers import AutoModelForSequenceClassification
    torch.set_num_threads(4)
    model=AutoModelForSequenceClassification.from_pretrained(model_path,local_files_only=True,trust_remote_code=False,dtype=torch.float32,attn_implementation='eager').to('cpu').eval()
    with torch.inference_mode():logits=model(**enc).logits[0].float()
    scores=logits.sigmoid() if spec['decision']=='sigmoid_threshold' else logits.softmax(-1)
    labels=spec['labels']
    selected=[labels[i] for i,p in enumerate(scores.tolist()) if p>=spec['threshold']] if spec['decision']=='sigmoid_threshold' else [labels[int(scores.argmax())]]
    print(json.dumps({'labels':selected,'scores':dict(zip(labels,scores.tolist())),'score_type':spec['decision'],'threshold':spec.get('threshold'),'device':'cpu','logits':logits.tolist()},indent=2))


if __name__=='__main__':main()
