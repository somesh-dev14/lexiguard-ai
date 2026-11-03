"""
Legal Clause Classifier Module
Loads pretrained model weights and labels locally from `pretrained_model/`
Supports CPU and CUDA, returning top 3 legal clause categories with probability scores.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch
import torch.nn.functional as F
from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification


class LegalClauseClassifier:
    def __init__(self, model_dir: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the legal clause classifier.
        
        Args:
            model_dir: Path to the local directory containing model.safetensors, config.json, etc.
                       Defaults to '<project_root>/pretrained_model'.
            device: 'cuda', 'cpu', or None (auto-detect).
        """
        if model_dir is None:
            # Default to <project_root>/pretrained_model
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent
            model_dir = str(project_root / "pretrained_model")

        self.model_path = Path(model_dir)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model directory not found at: {self.model_path}")

        # Determine compute device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Check required files
        required_files = ["config.json", "model.safetensors", "tokenizer.json", "labels.json"]
        for f in required_files:
            if not (self.model_path / f).is_file():
                raise FileNotFoundError(f"Required model file missing: {self.model_path / f}")

        # Load label specification
        labels_spec = json.loads((self.model_path / "labels.json").read_text(encoding="utf-8"))
        self.labels: List[str] = labels_spec["labels"]
        self.decision_type = labels_spec.get("decision", "softmax_argmax")
        self.max_length = labels_spec.get("max_length", 512)

        # Load tokenizer and configuration strictly offline
        self.config = AutoConfig.from_pretrained(
            self.model_path,
            local_files_only=True,
            trust_remote_code=False
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            local_files_only=True,
            trust_remote_code=False
        )

        assert self.config.num_labels == len(self.labels), (
            f"Config labels count ({self.config.num_labels}) does not match labels.json ({len(self.labels)})"
        )

        # Load model weights
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_path,
            local_files_only=True,
            trust_remote_code=False,
            dtype=torch.float32,
            attn_implementation="eager"
        ).to(self.device)
        self.model.eval()

    def classify_clause(self, text: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Classifies a contract clause and returns top-K predicted categories.
        
        Args:
            text: Contract clause passage text.
            top_k: Number of highest ranking predictions to return (default: 3).
            
        Returns:
            Dictionary containing:
                - top_predictions: List of dicts with 'label', 'confidence', and 'percentage'
                - predicted_category: Top-1 label name
                - device: Device used ('cpu' or 'cuda')
        """
        if not text or not text.strip():
            raise ValueError("Input clause text cannot be empty.")

        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        ).to(self.device)

        with torch.inference_mode():
            outputs = self.model(**inputs)
            logits = outputs.logits[0].float()
            probs = F.softmax(logits, dim=-1)

        k = min(top_k, len(self.labels))
        top_scores, top_indices = torch.topk(probs, k=k)

        predictions = []
        for score, idx in zip(top_scores.tolist(), top_indices.tolist()):
            label_name = self.labels[idx]
            predictions.append({
                "label": label_name,
                "confidence": round(float(score), 4),
                "percentage": f"{score * 100:.2f}%"
            })

        return {
            "predicted_category": predictions[0]["label"],
            "top_predictions": predictions,
            "device": str(self.device)
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Legal Clause Classifier using local pretrained_model")
    parser.add_argument("--text", type=str, default=None, help="Contract clause text")
    parser.add_argument("--top_k", type=int, default=3, help="Number of predictions")
    args = parser.parse_args()

    sample_clause = args.text or (
        "Except as otherwise set forth in this Debenture, the Company, for itself and its legal representatives, "
        "hereby expressly waives presentment, demand, notice, protest and all other demands and notices in connection "
        "with the delivery, acceptance, performance, default or enforcement of this Debenture."
    )

    print("Initializing LegalClauseClassifier from local pretrained_model...")
    classifier = LegalClauseClassifier()
    result = classifier.classify_clause(sample_clause, top_k=args.top_k)

    print("\n=== Legal Clause Classification Result ===")
    print(f"Clause preview: {sample_clause[:100]}...")
    print(f"Device: {result['device']}")
    print(f"Predicted Category: {result['predicted_category']}\n")
    print(f"Top {args.top_k} Categories:")
    for i, p in enumerate(result["top_predictions"], 1):
        print(f"  {i}. {p['label']}: {p['percentage']} (confidence: {p['confidence']})")
