import os
import sys
import argparse
import logging
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    TrainerCallback
)
from datasets import load_dataset
import torch

from config import TrainingConfig
from utils import setup_logger, set_seed, compute_metrics, save_json, load_json

class StabilityCallback(TrainerCallback):
    """Callback to monitor finite loss and numerical stability during training."""
    def __init__(self, logger):
        self.logger = logger

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is not None and "loss" in logs:
            loss_val = logs["loss"]
            if not (loss_val == loss_val) or loss_val == float('inf') or loss_val == float('-inf'):
                self.logger.error(f"NUMERICAL INSTABILITY DETECTED! Non-finite loss: {loss_val}")
                control.should_training_stop = True

def run_training(cfg: TrainingConfig):
    os.makedirs(cfg.logs_dir, exist_ok=True)
    os.makedirs(cfg.output_dir, exist_ok=True)
    os.makedirs(cfg.results_dir, exist_ok=True)
    
    logger = setup_logger(os.path.join(cfg.logs_dir, "train.log"))
    logger.info("Initializing LEDGAR DeBERTa-v3-base training workflow")
    logger.info(f"Configuration: {cfg}")
    
    set_seed(cfg.seed)
    
    # 1. Load label mappings
    label2id_path = os.path.join(cfg.results_dir, "label2id.json")
    id2label_path = os.path.join(cfg.results_dir, "id2label.json")
    if not (os.path.exists(label2id_path) and os.path.exists(id2label_path)):
        logger.info("Label mappings not found. Building them from dataset...")
        from prepare_data import prepare_ledgar_data
        prepare_ledgar_data(cfg.dataset_name, cfg.dataset_config, cfg.results_dir)
        
    label2id = load_json(label2id_path)
    id2label = {int(k): v for k, v in load_json(id2label_path).items()}
    logger.info(f"Loaded {len(label2id)} classes successfully.")
    
    # 2. Tokenizer
    logger.info(f"Loading tokenizer: {cfg.model_name_or_path}")
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name_or_path)
    
    # 3. Dataset
    logger.info(f"Loading dataset: {cfg.dataset_name} ({cfg.dataset_config})")
    raw_datasets = load_dataset(cfg.dataset_name, cfg.dataset_config)
    
    def preprocess_function(examples):
        texts = examples["input"]
        labels = [label2id[g[0].strip()] if (g and len(g) > 0 and g[0].strip() in label2id) else -100 for g in examples["gold"]]
        result = tokenizer(texts, truncation=True, max_length=cfg.max_seq_length)
        result["label"] = labels
        return result

    train_data = raw_datasets["train"]
    val_data = raw_datasets["validation"]
    
    if cfg.max_train_samples:
        train_data = train_data.select(range(min(len(train_data), cfg.max_train_samples)))
        logger.info(f"Subset train dataset to {len(train_data)} samples.")
    if cfg.max_eval_samples:
        val_data = val_data.select(range(min(len(val_data), cfg.max_eval_samples)))
        logger.info(f"Subset validation dataset to {len(val_data)} samples.")

    logger.info("Tokenizing train and validation splits...")
    tokenized_train = train_data.map(preprocess_function, batched=True, remove_columns=raw_datasets["train"].column_names)
    tokenized_val = val_data.map(preprocess_function, batched=True, remove_columns=raw_datasets["validation"].column_names)
    
    # Filter any invalid labels
    tokenized_train = tokenized_train.filter(lambda x: x["label"] != -100)
    tokenized_val = tokenized_val.filter(lambda x: x["label"] != -100)
    
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    
    # 4. Model Setup (Enforce FP32 baseline to avoid known DeBERTa-v3 NaN issues)
    logger.info(f"Loading model architecture: {cfg.model_name_or_path}")
    config = AutoConfig.from_pretrained(
        cfg.model_name_or_path,
        num_labels=len(label2id),
        id2label=id2label,
        label2id=label2id
    )
    
    torch_dtype = torch.float32 if cfg.force_fp32 else None
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.model_name_or_path,
        config=config,
        torch_dtype=torch_dtype
    )
    
    # Verify dtype
    param_types = set(p.dtype for p in model.parameters())
    logger.info(f"Model parameters loaded with dtypes: {param_types}")
    if cfg.force_fp32:
        for p in model.parameters():
            if p.dtype != torch.float32:
                model = model.to(torch.float32)
                break
        logger.info("Confirmed all parameters explicitly set to torch.float32.")
        
    if cfg.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        logger.info("Gradient checkpointing enabled.")

    # 5. Training Arguments
    training_args = TrainingArguments(
        output_dir=cfg.output_dir,
        learning_rate=cfg.learning_rate,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        per_device_eval_batch_size=cfg.per_device_eval_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        num_train_epochs=cfg.num_train_epochs,
        weight_decay=cfg.weight_decay,
        max_grad_norm=cfg.max_grad_norm,
        warmup_ratio=cfg.warmup_ratio,
        eval_strategy="steps",
        eval_steps=cfg.eval_steps,
        save_strategy="steps",
        save_steps=cfg.save_steps,
        save_total_limit=cfg.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_dir=cfg.logs_dir,
        logging_steps=cfg.logging_steps,
        fp16=cfg.fp16,
        bf16=cfg.bf16,
        seed=cfg.seed,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[StabilityCallback(logger)]
    )

    # 6. Execute Training / Resumption
    logger.info("Starting / Resuming training run...")
    
    resume_target = cfg.resume_from_checkpoint
    if resume_target == "auto" or resume_target == "latest":
        import glob
        existing_ckpts = glob.glob(os.path.join(cfg.output_dir, "checkpoint-*"))
        if existing_ckpts:
            def extract_step(path):
                try:
                    return int(path.split("-")[-1])
                except ValueError:
                    return -1
            latest_ckpt = max(existing_ckpts, key=extract_step)
            logger.info(f"Auto-resume detected latest checkpoint: {latest_ckpt}")
            resume_target = latest_ckpt
        else:
            logger.info("Auto-resume requested but no checkpoints found. Starting from scratch.")
            resume_target = None
    elif resume_target and not os.path.exists(resume_target):
        logger.warning(f"Specified checkpoint '{resume_target}' does not exist on disk! Starting from scratch.")
        resume_target = None

    train_result = trainer.train(resume_from_checkpoint=resume_target)
    
    logger.info("Training complete. Saving final model and artifacts...")
    os.makedirs(cfg.final_model_dir, exist_ok=True)
    trainer.save_model(cfg.final_model_dir)
    tokenizer.save_pretrained(cfg.final_model_dir)
    
    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)
    trainer.save_state()
    
    logger.info(f"Final model and tokenizer successfully saved to: {cfg.final_model_dir}")

def parse_args():
    parser = argparse.ArgumentParser(description="Train DeBERTa-v3 on LEDGAR")
    parser.add_argument("--max_seq_length", type=int, default=512)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=1e-5)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--fp16", action="store_true", default=False)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--resume_from_checkpoint", type=str, default=None)
    parser.add_argument("--max_train_samples", type=int, default=None)
    parser.add_argument("--max_eval_samples", type=int, default=None)
    parser.add_argument("--save_steps", type=int, default=500)
    parser.add_argument("--eval_steps", type=int, default=500)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    cfg = TrainingConfig()
    cfg.max_seq_length = args.max_seq_length
    cfg.per_device_train_batch_size = args.batch_size
    cfg.gradient_accumulation_steps = args.grad_accum
    cfg.learning_rate = args.learning_rate
    cfg.num_train_epochs = args.epochs
    cfg.fp16 = args.fp16
    cfg.save_steps = args.save_steps
    cfg.eval_steps = args.eval_steps
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.resume_from_checkpoint:
        cfg.resume_from_checkpoint = args.resume_from_checkpoint
    if args.max_train_samples:
        cfg.max_train_samples = args.max_train_samples
    if args.max_eval_samples:
        cfg.max_eval_samples = args.max_eval_samples
        
    run_training(cfg)
