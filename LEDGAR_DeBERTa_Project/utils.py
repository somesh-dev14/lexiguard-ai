import os
import json
import logging
import random
import numpy as np
import torch
from typing import Dict, Any, Tuple
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

def setup_logger(log_file: str = None) -> logging.Logger:
    logger = logging.getLogger("LEDGAR_DeBERTa")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
    return logger

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def compute_metrics(eval_pred) -> Dict[str, float]:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    acc = accuracy_score(labels, preds)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    weighted_f1 = f1_score(labels, preds, average="weighted", zero_division=0)
    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1)
    }

def verify_finite_tensors(loss: torch.Tensor, model: torch.nn.Module) -> Tuple[bool, str]:
    if not torch.isfinite(loss).item():
        return False, f"Loss is non-finite (NaN or Inf): {loss.item()}"
    for name, param in model.named_parameters():
        if param.grad is not None:
            if not torch.isfinite(param.grad).all():
                return False, f"Gradient for {name} is non-finite (NaN or Inf)"
        if not torch.isfinite(param).all():
            return False, f"Parameter {name} contains non-finite values (NaN or Inf)"
    return True, "All parameters, gradients, and loss are finite"

def save_json(data: Any, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
