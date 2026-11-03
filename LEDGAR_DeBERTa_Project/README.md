# LEDGAR DeBERTa-v3-base 100-Class Legal Clause Classifier

A production-grade, reproducible fine-tuning pipeline for legal clause classification using `microsoft/deberta-v3-base` on the LEDGAR dataset (`lighteval/lexglue`).

---

## 1. Project Overview

- **Task**: 100-class legal clause classification.
- **Dataset**: `lighteval/lexglue` configuration `ledgar` (60,000 train / 10,000 validation / 10,000 test).
- **Model**: `microsoft/deberta-v3-base` (Sequence Classification head with 100 outputs).
- **Historical Baseline (Colab Run - Reference Only)**:
  - Validation Accuracy: **84.28%**
  - Validation Macro F1: **73.84%**
  - Validation Weighted F1: **83.03%**
  - *Note: These are historical targets, not current run results.*

---

## 2. Directory Structure

```text
LEDGAR_DeBERTa_Project/
├── README.md               # Documentation and execution guide
├── requirements.txt        # Dependencies
├── config.py               # Hyperparameter and environment configuration
├── prepare_data.py         # Dataset inspection and deterministic label mapping
├── train.py                # Main training script (FP32 baseline, gradient checkpointing)
├── evaluate.py             # Evaluation on untouched official test split
├── predict.py              # Top-3 clause prediction inference CLI
├── utils.py                # Metrics, logging, seed, and stability checkers
├── setup_windows.ps1       # Windows setup script
├── run_training.ps1        # Execution script for training
├── resume_training.ps1     # Resumption script for training from checkpoint
├── checkpoints/            # Optimizer, scheduler, model checkpoints
├── final_model/            # Best model weights and tokenizer
├── logs/                   # Training logs
└── results/                # label2id.json, id2label.json, metrics, reports
```

---

## 3. Environment & Hardware Assessment

### Local Laptop Findings:
- **GPU**: NVIDIA GeForce RTX 2050 (4 GB VRAM).
- **Available VRAM**: ~2.7 GB free (display and background tasks consume ~1.3 GB).
- **Current PyTorch**: CPU-only build (`2.11.0+cpu`). CUDA is unavailable in this environment until a CUDA-enabled PyTorch build is installed.
- **System RAM**: 16 GB DDR5.
- **Free Disk Space**: 7.0 GB remaining on `C:\`.
- **Hardware Limitation**: DeBERTa-v3-base has 86M backbone parameters + embeddings + attention layers. With 100 classification output classes, 512 sequence length, full FP32 training, optimizer states (AdamW FP32 requires 8 bytes per parameter), and activation gradients, full fine-tuning requires 8–12 GB VRAM. Training on a 4 GB GPU (with 2.7 GB free) and only 7 GB disk remaining will cause Out-Of-Memory (OOM) and disk space exhaustion during checkpointing.

---

## 4. Execution Instructions

### A. Dataset Label Preparation
Extract and verify the 100 deterministic classes:
```bash
python prepare_data.py
```

### B. Launch Training (Local Pilot or Remote GPU)
To run with memory optimization:
```bash
python train.py --max_seq_length 512 --batch_size 1 --grad_accum 16 --learning_rate 1e-5 --epochs 3 --save_steps 500 --eval_steps 500
```
For a fast sanity check / pilot run:
```bash
python train.py --max_train_samples 100 --max_eval_samples 50 --max_seq_length 256 --epochs 1 --eval_steps 20 --save_steps 20
```

### C. Resume from Checkpoint
```bash
python train.py --resume_from_checkpoint checkpoints/checkpoint-500
```

### D. Evaluate on Untouched Official Test Split
```bash
python evaluate.py --model_path final_model --results_dir results
```

### E. Predict Legal Clause Category
```bash
python predict.py --text "The Company shall indemnify and hold harmless the Executive..."
```
