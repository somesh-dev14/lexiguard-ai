import os
import argparse
import numpy as np
import torch
from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, Trainer, TrainingArguments
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

from config import TrainingConfig
from utils import setup_logger, compute_metrics, save_json, load_json

def evaluate_model(model_path: str = None, results_dir: str = "results", max_test_samples: int = None):
    cfg = TrainingConfig()
    if model_path is None:
        model_path = cfg.final_model_dir
        
    logger = setup_logger(os.path.join(cfg.logs_dir, "evaluate.log"))
    logger.info(f"Evaluating model at: {model_path} on the untouched test split")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model directory not found at: {model_path}. Please train or download the model first.")
        
    label2id_path = os.path.join(results_dir, "label2id.json")
    id2label_path = os.path.join(results_dir, "id2label.json")
    label2id = load_json(label2id_path)
    id2label = {int(k): v for k, v in load_json(id2label_path).items()}
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    
    raw_datasets = load_dataset(cfg.dataset_name, cfg.dataset_config)
    test_data = raw_datasets["test"]
    
    if max_test_samples:
        test_data = test_data.select(range(min(len(test_data), max_test_samples)))
        logger.info(f"Subsampled test set to {len(test_data)} examples.")
        
    def preprocess_function(examples):
        texts = examples["input"]
        labels = [label2id[g[0].strip()] if (g and len(g) > 0 and g[0].strip() in label2id) else -100 for g in examples["gold"]]
        result = tokenizer(texts, truncation=True, max_length=cfg.max_seq_length)
        result["label"] = labels
        return result

    tokenized_test = test_data.map(preprocess_function, batched=True, remove_columns=test_data.column_names)
    tokenized_test = tokenized_test.filter(lambda x: x["label"] != -100)
    
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=os.path.join(results_dir, "eval_temp"),
            per_device_eval_batch_size=cfg.per_device_eval_batch_size,
            report_to="none"
        ),
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics
    )
    
    preds_output = trainer.predict(tokenized_test)
    preds = np.argmax(preds_output.predictions, axis=1)
    true_labels = preds_output.label_ids
    
    acc = float(accuracy_score(true_labels, preds))
    macro_f1 = float(f1_score(true_labels, preds, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(true_labels, preds, average="weighted", zero_division=0))
    
    target_names = [id2label[i] for i in range(len(id2label))]
    report = classification_report(true_labels, preds, target_names=target_names, output_dict=True, zero_division=0)
    cm = confusion_matrix(true_labels, preds).tolist()
    
    test_results = {
        "test_accuracy": acc,
        "test_macro_f1": macro_f1,
        "test_weighted_f1": weighted_f1,
        "classification_report": report,
        "confusion_matrix": cm,
        "historical_comparison": {
            "historical_validation_accuracy": 0.8428,
            "historical_validation_macro_f1": 0.7384,
            "historical_validation_weighted_f1": 0.8303,
            "note": "Historical metrics were validation results from a 3-epoch run on full LEDGAR. Compare cautiously with test results."
        }
    }
    
    out_file = os.path.join(results_dir, "test_evaluation_results.json")
    save_json(test_results, out_file)
    logger.info(f"Evaluation complete. Saved results to: {out_file}")
    print(f"Test Accuracy: {acc * 100:.2f}% | Test Macro F1: {macro_f1 * 100:.2f}% | Test Weighted F1: {weighted_f1 * 100:.2f}%")
    return test_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--results_dir", type=str, default="results")
    parser.add_argument("--max_test_samples", type=int, default=None)
    args = parser.parse_args()
    evaluate_model(args.model_path, args.results_dir, args.max_test_samples)
