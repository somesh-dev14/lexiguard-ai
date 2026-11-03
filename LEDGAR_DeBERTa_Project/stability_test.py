import sys
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from utils import verify_finite_tensors

def run_stability_test():
    print("=== DeBERTa-v3 Forward/Backward Stability & Precision Test ===")
    model_name = "microsoft/deberta-v3-base"
    print(f"Loading tokenizer: {model_name}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    except Exception as e:
        print("Tokenizer loading error:", e)
        return
        
    print(f"Loading model {model_name} in explicit float32...")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=100,
        torch_dtype=torch.float32
    )
    model.train()
    
    # Verify parameter types
    dtypes = set(p.dtype for p in model.parameters())
    print("Model parameter dtypes:", dtypes)
    assert all(d == torch.float32 for d in dtypes), "Model parameters are not FP32!"
    
    # Create sample batch
    sample_text = ["This agreement shall be governed by the laws of the State of Delaware."] * 2
    inputs = tokenizer(sample_text, padding=True, truncation=True, max_length=128, return_tensors="pt")
    labels = torch.tensor([0, 1], dtype=torch.long)
    
    # Forward pass
    print("Running forward pass...")
    outputs = model(**inputs, labels=labels)
    loss = outputs.loss
    logits = outputs.logits
    print(f"Computed loss: {loss.item():.4f}")
    
    # Backward pass
    print("Running backward pass...")
    loss.backward()
    
    # Verify finite tensors
    is_finite, msg = verify_finite_tensors(loss, model)
    print("Stability Check Result:", msg)
    if is_finite:
        print("PASSED: Model, gradients, and loss are numerically stable and finite in FP32.")
    else:
        print("FAILED: Numerical instability detected.")

if __name__ == "__main__":
    run_stability_test()
