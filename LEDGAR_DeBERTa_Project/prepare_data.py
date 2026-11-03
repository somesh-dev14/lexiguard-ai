import os
import json
from datasets import load_dataset, DatasetDict
from transformers import AutoTokenizer

def prepare_ledgar_data(dataset_name="lighteval/lexglue", dataset_config="ledgar", output_dir="results"):
    print(f"Loading dataset {dataset_name} ({dataset_config})...")
    raw_datasets = load_dataset(dataset_name, dataset_config)
    
    # Extract unique classes deterministically
    all_labels = set()
    for split in ["train", "validation", "test"]:
        for sample in raw_datasets[split]:
            gold = sample.get("gold")
            if gold and len(gold) > 0:
                all_labels.add(gold[0].strip())
    
    unique_labels = sorted(list(all_labels))
    print(f"Discovered {len(unique_labels)} unique classes.")
    
    label2id = {label: i for i, label in enumerate(unique_labels)}
    id2label = {i: label for i, label in enumerate(unique_labels)}
    
    # Save mappings
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "label2id.json"), "w", encoding="utf-8") as f:
        json.dump(label2id, f, indent=2)
    with open(os.path.join(output_dir, "id2label.json"), "w", encoding="utf-8") as f:
        json.dump(id2label, f, indent=2)
        
    print(f"Saved label mappings to {output_dir}")
    return raw_datasets, label2id, id2label

if __name__ == "__main__":
    prepare_ledgar_data()
