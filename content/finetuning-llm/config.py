from datetime import datetime


class Config:
    """Configuration class for model training parameters and settings."""

    dataset_name = "Salesforce/dialogstudio"
    dataset_config = "TweetSumm"

    model_id = "meta-llama/Llama-2-70b-hf"
    lora_target_modules = [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "lm_head",
    ]

    output_dir = f"./results/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    training_args = {
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 3,
        "optim": "adamw_8bit",
        "save_steps": 10,
        "logging_steps": 1,
        "learning_rate": 2e-4,
        "max_grad_norm": 0.3,
        "max_steps": 300,
        "warmup_ratio": 0.1,
        "lr_scheduler_type": "cosine",
    }
