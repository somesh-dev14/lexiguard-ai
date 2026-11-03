import os
import sys
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from utils import verify_finite_tensors, load_json

def run_remote_smoke_test(project_root: str = "."):
    root = Path(project_root).resolve()
    print("=" * 60)
    print("RUNNING PRE-FLIGHT SMOKE TEST FOR REMOTE GPU ENVIRONMENT")
    print("=" * 60)
    
    # 1. PyTorch & CUDA Visibility
    print(f"PyTorch Version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    if cuda_available:
        device_name = torch.cuda.get_device_name(0)
        vram_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_gb = vram_bytes / (1024 ** 3)
        print(f"Detected GPU: {device_name} ({vram_gb:.2f} GB VRAM)")
        if vram_gb < 15.0:
            print(f"WARNING: VRAM ({vram_gb:.2f} GB) is lower than recommended (>=16 GB)!")
        else:
            print("VRAM capacity check: PASSED (>= 16 GB).")
    else:
        print("NOTE: Running in CPU mode (Smoke test will verify code logic without CUDA).")

    device = torch.device("cuda:0" if cuda_available else "cpu")
    
    # 2. Check Directory Structure and Writable Storage
    for folder in ["checkpoints", "final_model", "logs", "results"]:
        target_dir = root / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        test_file = target_dir / ".write_test"
        try:
            test_file.write_text("ok")
            test_file.unlink()
            print(f"Storage writable check [{folder}]: PASSED")
        except Exception as e:
            print(f"Storage writable check [{folder}]: FAILED ({e})")
            return False

    # 3. Label Map Verification
    label2id_file = root / "results" / "label2id.json"
    if not label2id_file.exists():
        print("Generating deterministic label mapping from LEDGAR...")
        from prepare_data import prepare_ledgar_data
        prepare_ledgar_data(output_dir=str(root / "results"))
        
    label2id = load_json(str(label2id_file))
    num_classes = len(label2id)
    print(f"Label map check: {num_classes} classes loaded. (Expected: 100) -> {'PASSED' if num_classes == 100 else 'FAILED'}")
    assert num_classes == 100, f"Expected 100 classes, found {num_classes}"

    # 4. Model Architecture & Explicit FP32 Loading
    model_name = "microsoft/deberta-v3-base"
    print(f"\nLoading tokenizer and model ({model_name}) in explicit float32...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=100,
        torch_dtype=torch.float32
    ).to(device)
    model.train()

    # Dtype verification
    param_dtypes = set(p.dtype for p in model.parameters())
    print(f"Model parameter dtypes: {param_dtypes}")
    assert all(d == torch.float32 for d in param_dtypes), "Model parameters are not all FP32!"
    print("Model parameter FP32 verification: PASSED")

    # 5. Forward / Backward Pass Stability & Finite Tensors
    print("\nExecuting forward and backward pass on batch_size=2, seq_length=512...")
    sample_texts = [
        "Except as otherwise set forth in this Debenture, the Company hereby expressly waives presentment, demand, notice, and protest.",
        "The Executive shall be entitled to indemnification to the fullest extent permitted by the laws of the State of Delaware."
    ]
    inputs = tokenizer(sample_texts, padding="max_length", truncation=True, max_length=512, return_tensors="pt").to(device)
    labels = torch.tensor([0, 1], dtype=torch.long, device=device)

    outputs = model(**inputs, labels=labels)
    loss = outputs.loss
    print(f"Sample loss value: {loss.item():.4f}")
    assert torch.isfinite(loss).item(), "Loss is NaN or Infinite!"

    loss.backward()
    is_finite, msg = verify_finite_tensors(loss, model)
    print(f"Finite gradient check: {msg}")
    assert is_finite, f"Stability test failed: {msg}"

    # 6. Checkpoint Save and Reload Test
    print("\nTesting checkpoint save and reload...")
    test_ckpt_dir = root / "checkpoints" / "test_smoke_ckpt"
    test_ckpt_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(test_ckpt_dir))
    tokenizer.save_pretrained(str(test_ckpt_dir))
    
    reloaded_model = AutoModelForSequenceClassification.from_pretrained(str(test_ckpt_dir)).to(device)
    reloaded_model.eval()
    with torch.no_grad():
        reloaded_out = reloaded_model(**inputs)
    diff = (outputs.logits.detach().cpu() - reloaded_out.logits.cpu()).abs().max().item()
    print(f"Reloaded model logits absolute diff: {diff:.6e} (Should be ~0.0)")
    assert diff < 1e-4, "Reloaded checkpoint outputs do not match!"
    print("Checkpoint save and reload: PASSED")

    # Clean up test checkpoint
    import shutil
    shutil.rmtree(str(test_ckpt_dir), ignore_errors=True)

    print("\n" + "=" * 60)
    print("ALL SMOKE TESTS COMPLETED SUCCESSFULLY!")
    print("Environment is verified and ready for full training.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    run_remote_smoke_test()
