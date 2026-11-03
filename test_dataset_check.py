import sys
import traceback
from datasets import load_dataset

print("Testing Hugging Face LEDGAR dataset download/check...")
try:
    ds = load_dataset("lighteval/lexglue", "ledgar")
    print("Dataset successfully loaded!")
    print("Splits:", list(ds.keys()))
    for split_name in ds.keys():
        print(f"  {split_name}: {len(ds[split_name])} examples")
    sample = ds["train"][0]
    print("Sample keys:", list(sample.keys()))
    print("Sample input preview:", sample["text"][:100] if "text" in sample else sample.get("input", "")[:100])
    print("Sample gold:", sample.get("gold", sample.get("label", "N/A")))
except Exception as e:
    print("Failed to load dataset:", e)
    traceback.print_exc()
