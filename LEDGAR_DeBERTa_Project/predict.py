import os
import sys
import argparse
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from utils import load_json

def predict_clause(text: str, model_path: str = "final_model", results_dir: str = "results", top_k: int = 3):
    if not os.path.exists(model_path) or not os.path.exists(os.path.join(model_path, "config.json")):
        raise FileNotFoundError(
            f"Error: Model not found at '{model_path}'.\n"
            "Please ensure you have trained the model or specified the correct path via --model_path."
        )
        
    id2label_path = os.path.join(results_dir, "id2label.json")
    if not os.path.exists(id2label_path):
        id2label_path = os.path.join(model_path, "config.json")
        if not os.path.exists(id2label_path):
            raise FileNotFoundError(f"Label map not found at '{id2label_path}'.")
            
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]
        
    top_probs, top_indices = torch.topk(probs, k=top_k)
    
    id2label = {int(k): v for k, v in model.config.id2label.items()}
    
    predictions = []
    for prob, idx in zip(top_probs, top_indices):
        label_name = id2label.get(idx.item(), f"Class_{idx.item()}")
        predictions.append({
            "label": label_name,
            "confidence": float(prob.item()),
            "percentage": f"{prob.item() * 100:.2f}%"
        })
        
    return predictions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict top 3 legal clause categories for a contract passage.")
    parser.add_argument("--text", type=str, default=None, help="Input contract clause text")
    parser.add_argument("--model_path", type=str, default="final_model")
    parser.add_argument("--top_k", type=int, default=3)
    args = parser.parse_args()
    
    sample_text = args.text or (
        "Except as otherwise set forth in this Debenture, the Company, for itself and its legal representatives, "
        "hereby expressly waives presentment, demand, notice, protest and all other demands and notices in connection "
        "with the delivery, acceptance, performance, default or enforcement of this Debenture."
    )
    
    try:
        results = predict_clause(sample_text, model_path=args.model_path, top_k=args.top_k)
        print("\n=== Legal Clause Prediction Results ===")
        print(f"Input: {sample_text[:120]}...\n")
        for i, res in enumerate(results, 1):
            print(f"{i}. {res['label']} ({res['percentage']})")
    except Exception as e:
        print(f"\n[INFORMATIVE ERROR]: {e}")
