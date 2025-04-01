# Efficient Training of Large Language Models (LLMs) with LoRA and 4-Bit Quantization

In this guide, we will explore an efficient approach to training LLMs using Low-Rank Adaptation (LoRA) and 4-bit quantization with `bitsandbytes`. These techniques significantly reduce GPU memory requirements while maintaining model performance. Additionally, we will leverage data parallelism to accelerate training across multiple GPUs.

## Hardware Requirements

For optimal performance, your system should meet the following hardware specifications:

- **2× NVIDIA A100 GPUs** (80GB VRAM each)
- **300GB of mounted storage** (for model weights and training artifacts)

## Storage Configuration

### Mounting Storage

To set up storage on your virtual machine, execute the following commands:

```bash
mkfs.ext4 /dev/vdb
mkdir /scratch
sudo mount -t ext4 /dev/vdb /scratch
```

Verify that the storage has been mounted correctly and check for sufficient capacity:

```bash
df -h /scratch
```

### Cloning the Cookbook Repository

Clone the repository containing this guide and navigate to the relevant directory:

```bash
git clone https://github.com/crusoecloud/crusoe-cookbook.git
cd crusoe-cookbook/content/finetuning-llms
```

Project Structure
```
src/
├── config.py
├── main.py      
├── data_processing/
│   ├── processor.py
```

## Install Dependencies

To begin, update your system and install the Python development headers:

```bash
sudo apt-get update
sudo apt-get install python3-dev -y
sudo apt-get install python3-pip -y
```

Next, install the necessary Python libraries. If you've just created your environment, use the following command:

```bash
pip install torch==2.6.0 transformers==4.50.1 datasets==3.4.1 peft==0.15.1 bitsandbytes==0.45.4 trl==0.12.0 accelerate==1.5.2
```

### Exporting Environment Variables

To optimize storage and prevent issues during training, export the required environment variables:

```bash
export HF_HOME=/scratch
export HF_TOKEN=<your_hf_token>
```

The `HF_HOME` variable points to the mounted storage where models and datasets will be stored, and the `HF_TOKEN` ensures that you can access gated datasets from Hugging Face. 

**Note:** You can generate an HF token by following the instructions provided on the Hugging Face website: [How to generate a Hugging Face token](https://huggingface.co/docs/hub/security-tokens).

### Running the Training Script

The training process is contained in the `main.py` script. Run it with:

```bash
accelerate launch --mixed_precision 'bf16' main.py
```

This command launches the training script using the `accelerate` library, which is optimized for multi-GPU and distributed training. The `--mixed_precision 'bf16'` argument ensures that the training uses bfloat16 precision, optimizing memory usage and improving training speed without sacrificing model performance.

By running this command, the script will initialize all components (like the model, tokenizer, dataset, and trainer) and start the training process as described earlier.

Now that we know how to run training script, let's take a closer look at it. This script orchestrates the entire training pipeline, including model initialization, dataset preparation, and fine-tuning with LoRA and 4-bit quantization. Understanding its structure will help us grasp how these techniques work in practice.

## Preparing the Dataset

### Loading the Dataset

We will use the [TweetSumm](https://huggingface.co/datasets/Salesforce/dialogstudio) dataset, which includes conversation summaries. To load the dataset, run the following code:

```python
from datasets import load_dataset

dataset = load_dataset(
    "Salesforce/dialogstudio", 
    "TweetSumm", 
    trust_remote_code=True
)
```

### Loading the Tokenizer

Before processing the dataset, load the tokenizer from Hugging Face. This ensures that input text is properly tokenized before being passed to the model.

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        padding_side="left",
        add_eos_token=True,
        add_bos_token=True,
    )
tokenizer.pad_token = tokenizer.eos_token
```

### Preprocessing the Dataset

The core of dataset preprocessing involves transforming raw conversations into a format suitable for training. Each sample will be structured into an instruction, input, and response format, enabling the model to learn from structured data. The `Processor` class handles this by extracting the conversation, removing irrelevant content (like URLs and mentions), and creating training prompts. The conversation is then tokenized.

```python
processor = Processor(tokenizer=tokenizer)
processed_dataset = processor.process_dataset(dataset, tokenize=True)
```

This ensures that each conversation is formatted as follows:

```
### Instruction: Below is a conversation between a human and an AI agent. Write a summary of the conversation.

### Input:
user: How do I check in for my flight?
agent: You can check in online through our website or mobile app.

### Response:
The user is asking about the process for checking in for a flight. The agent suggests checking in online.
```

This format makes it easier for the model to learn the relationship between user queries and AI responses, while also maintaining the necessary structure for summarization tasks.

## Loading the model

To load a pre-trained model with 4-bit quantization, we'll use the `AutoModelForCausalLM` class from Hugging Face, with the necessary configuration for 4-bit quantization. Specifically, we'll use the `BitsAndBytesConfig` to enable 4-bit quantization and configure the relevant settings. This reduces memory consumption and speeds up model inference, making it suitable for training LLMs.

You can initialize the model using the following code:

```python
from transformers import AutoModelForCausalLM
from bitsandbytes import BitsAndBytesConfig
import torch
import os

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf",
    quantization_config=bnb_config,
    trust_remote_code=True,
    use_cache=False,
    device_map={"": "cuda:" + str(int(os.environ.get("LOCAL_RANK") or 0))}
)
```

Once the model is loaded, it will be placed on the appropriate GPU using the `device_map` argument. If you're training across multiple GPUs, this will automatically assign the model to the correct device based on the environment variable `LOCAL_RANK`.

## Configuring PEFT (Low-Rank Adaptation)

To further optimize the training of LLMs, we use Low-Rank Adaptation (LoRA), a technique that modifies only a subset of model parameters while leaving the rest intact. LoRA helps achieve good performance with less computational overhead and reduced memory requirements. The `LoraConfig` class from the PEFT library configures LoRA parameters for the model.

### LoRA Configuration

You can configure LoRA with the following parameters:

```python
from peft import LoraConfig

peft_config = LoraConfig(
    r=32,
    lora_alpha=64,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "lm_head",
    ]
    bias="none",
    lora_dropout=0.05,
    task_type="CAUSAL_LM"
)
```
Once the LoRA configuration is set up, it can be applied to the model during training, allowing for efficient fine-tuning with minimal computational cost.

## Training the Model

Now that the dataset is processed, the model is loaded, and PEFT (Low-Rank Adaptation) is configured, we can proceed with training the model. We will use the `TrainingArguments` class to define important training parameters, such as batch sizes, evaluation strategies, gradient checkpointing, and checkpoint saving. These settings are crucial for ensuring the stability of training and efficient management of system resources.

### Training Arguments Configuration

The `TrainingArguments` class specifies all the hyperparameters and settings for the training process. This includes optimizer configurations, batch sizes, evaluation strategies, gradient accumulation, and more. Below is an example configuration for our training:

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    # Output and logging
    output_dir=config.output_dir,
    logging_steps=config.training_args["logging_steps"],
    report_to=None,

    # Optimization and training dynamics  
    optim=config.training_args["optim"],
    learning_rate=config.training_args["learning_rate"],
    max_grad_norm=config.training_args["max_grad_norm"],
    num_train_epochs=2,
    warmup_ratio=config.training_args["warmup_ratio"],
    warmup_steps=2,

    # Batch and gradient settings  
    per_device_train_batch_size=config.training_args["per_device_train_batch_size"],
    gradient_accumulation_steps=config.training_args["gradient_accumulation_steps"],
    gradient_checkpointing=True,
    bf16=True,

    # Distributed training  
    ddp_find_unused_parameters=False,
    group_by_length=True,

    # Checkpointing and evaluation  
    save_strategy="steps",
    save_steps=100,
    evaluation_strategy="steps",
    eval_steps=50,
    do_eval=True,
    )
```

### Starting the Training with the Trainer

To begin training, we use the `SFTTrainer` class, which is designed for training supervised fine-tuning models. We will pass the processed dataset and the model along with the training arguments and PEFT configuration:

```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    train_dataset=processed_dataset["train"],
    eval_dataset=processed_dataset["validation"],
    peft_config=peft_config,
    args=training_args,
)
```

### Handling Potential Issues During Training

With the checkpointing system in place, training can resume from the most recent checkpoint if anything unexpected happens. The model will be periodically saved and evaluated, giving us the ability to monitor performance in real-time. If the model starts to overfit or underperform, adjustments to hyperparameters like learning rate, batch size, and gradient accumulation steps can be made dynamically.

Additionally, the use of `gradient_checkpointing` ensures that large models can still be trained on GPUs with limited memory. This, combined with the use of 4-bit quantization, helps manage GPU memory constraints and keeps training manageable even with large datasets and models.


### Training the Model with `trainer.train()`

Once the `SFTTrainer` is set up with the model, datasets, training arguments, and PEFT configuration, we can start the actual training process by calling the `train()` method:

```python
trainer.train()
```

## Saving and Loading the Fine-Tuned Model

After training, the fine-tuned model is saved in the ./results directory. You can reload it for inference or further fine-tuning as follows:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf",
    device_map="auto",
)

finetuned_model = PeftModel.from_pretrained(model, "./results")
```

This ensures that your fine-tuned model is properly loaded with all LoRA adapters and ready for inference or further training.

## Conclusion

By combining **LoRA**, **4-bit quantization**, and **multi-GPU training**, we achieved efficient fine-tuning of LLMs while minimizing resource usage. This setup enables scalable, cost-effective training without sacrificing performance.

Next steps? Experiment with hyperparameters and datasets to tailor models to your needs. Happy training! 🚀