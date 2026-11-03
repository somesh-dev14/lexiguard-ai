import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TrainingConfig:
    # Model & Architecture
    model_name_or_path: str = "microsoft/deberta-v3-base"
    num_labels: int = 100
    dataset_name: str = "lighteval/lexglue"
    dataset_config: str = "ledgar"
    
    # Sequence Length & Batching
    max_seq_length: int = 512
    per_device_train_batch_size: int = 2
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 8  # effective batch size = 2 * 8 = 16
    
    # Optimization & Hyperparameters
    learning_rate: float = 1e-5
    weight_decay: float = 0.01
    max_grad_norm: float = 0.5
    num_train_epochs: int = 3
    warmup_ratio: float = 0.1
    seed: int = 42
    
    # Memory & Stability
    fp16: bool = False
    bf16: bool = False
    gradient_checkpointing: bool = True
    force_fp32: bool = True
    
    # Logging, Checkpointing & Output Paths
    output_dir: str = os.path.join(os.path.dirname(__file__), "checkpoints")
    final_model_dir: str = os.path.join(os.path.dirname(__file__), "final_model")
    logs_dir: str = os.path.join(os.path.dirname(__file__), "logs")
    results_dir: str = os.path.join(os.path.dirname(__file__), "results")
    
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 50
    save_total_limit: int = 2
    resume_from_checkpoint: Optional[str] = None
    
    # Pilot run controls
    max_train_samples: Optional[int] = None
    max_eval_samples: Optional[int] = None
    max_test_samples: Optional[int] = None
