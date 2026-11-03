---
model_name: "LiTiL Clause Classifier"
base_model: answerdotai/ModernBERT-large
base_model_relation: finetune
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
language:
  - en
datasets:
  - coastalcph/lex_glue
metrics:
  - accuracy
  - f1
tags:
  - litil-labs
  - legal
  - clause-classification
  - ledgar
---

# LiTiL Clause Classifier

## What this model does

LiTiL Clause Classifier assigns one category from a contract taxonomy to a contract provision and returns a score for every available category. It gives contract systems a consistent label for clauses whose wording may vary widely across agreements.

Place it after contract parsing and clause segmentation. The selected label can be written to a clause index, used as a search filter, shown in a review interface, or mapped to a category-specific playbook. The score distribution also lets an application send close or low-scoring classifications to a reviewer instead of forcing every clause through the same path.

- **Useful for:** organizing agreements, making clauses easier to search, and routing provisions for review
- **Give it:** one contract clause
- **It returns:** the selected label and a score for every category

| At a glance | Detail |
|---|---|
| Release repository | `litillabs/litil-clause-classifier` |
| Model format | Complete ModernBERT sequence-classification checkpoint |
| Base | `answerdotai/ModernBERT-large` |
| Input → output | One provision → one label and 100 softmax scores |
| Input policy | Maximum 512 tokens, truncation enabled |
| Tested runtime | CPU float32 · PyTorch 2.12.0 · Transformers 5.9.0 |

## Input and output contract

Input JSON accepts a required `text` string and optional `text_pair` string. The classifier applies softmax across 100 mutually exclusive labels and selects `argmax`; there is no multilabel threshold.

```json
{
  "text": "The receiving party shall keep all confidential information secret.",
  "text_pair": null
}
```

The full ordered label map ships as `labels.json` and must remain aligned with the classification head. Output scores are useful for ranking alternatives, but they have not been calibrated as probabilities.

## Practical use

1. Segment a contract into individual provisions.
2. Classify each provision independently with the 512-token policy above.
3. Retain the top label and score, and optionally the next few labels for review.
4. Route the provision using the exact LEDGAR label map.

Multi-topic provisions still receive one label. For full-contract processing, segment first and preserve the source location of every provision.

## Training data and method

ModernBERT-large was fine-tuned on **60,000 public LEDGAR contract provisions** from the LexGLUE dataset. The bound dataset revision is `c23fdff1a6bf74e0e1a71cb86f1e781d37da888c`; its published license is CC BY 4.0. No private client or user data was used in the reviewed post-training set.

## Evaluation

| Evaluation | Accuracy | Macro F1 |
|---|---:|---:|
| Public LEDGAR test set, 10,000 provisions | **88.82%** | **83.17%** |

The retained test receipt reports this 100-label aggregate for the selected checkpoint.

A separate CPU interface check on September 10, 2026 produced the expected category on four synthetic provisions: confidentiality, governing law, severability and counterparts.

## Runtime and version

The repository contains a complete model; no base-model download or PEFT merge is required. The selected `model.safetensors` is 1,583,753,448 bytes with SHA-256 `0c33bae20ce7edf1e0a2d5a71c5bb93aa30e5dd729564c12b585ddfde18293e3`.

- Selected checkpoint commit: `136c5138e3b40b43b192b965fdee48fb9591784f`
- Tested base snapshot: `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13`
- Dataset revision: `c23fdff1a6bf74e0e1a71cb86f1e781d37da888c`
- Card version: September 11, 2026
- Organization: LiTiL Labs

## Use the model

```bash
python -m pip install "torch==2.12.0" "transformers==5.9.0"
```

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "litillabs/litil-clause-classifier"
text = (
    "This agreement shall be governed by and construed in accordance with "
    "the laws of the State of Oregon, without regard to conflict of laws rules."
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).eval()
inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")

with torch.inference_mode():
    probabilities = model(**inputs).logits[0].float().softmax(-1)

class_id = int(probabilities.argmax())
print({"label": model.config.id2label[class_id], "score": float(probabilities[class_id])})
```

Expected result for the example:

```json
{"label": "Governing Laws", "score": 0.963958}
```

The prepared offline package also includes an explicit label map and runner:

```bash
python classify_offline.py --model ./model --validate-only
python classify_offline.py --model ./model --input example_input.json
```

## Citation

When using this checkpoint, cite the release repository, LEDGAR/LexGLUE and ModernBERT.
