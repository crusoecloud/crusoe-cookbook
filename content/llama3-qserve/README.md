# Getting Started
Before we jump in, ensure that you have the [Crusoe CLI](https://docs.crusoecloud.com/quickstart/installing-the-cli/index.html) installed and configured to work with your account. We’ll use this tool to provision our resources and tear them down at the end.

Navigate to the root directory of this repository. Then, provision resources with:
```bash
crusoe storage disks create \
  --name qserve-disk-1 \
  --size 200GiB \
  --location us-east1-a

crusoe compute vms create \
  --name qserve-vm \
  --type l40s-48gb.1x \
  --disk name=qserve-disk-1,mode=read-write \
  --location us-east1-a \
  --image ubuntu22.04-nvidia-pcie-docker \
  --keyfile ~/.ssh/id_ed25519.pub \
  --startup-script startup.sh
```

The startup script will take care of creating a filesystem and mounting the disk as well as dependency installation. After the creation has completed, ssh into the public IP address in the output of `crusoe compute vms create`.

Once in the VM, check on the startup script's status by running `journalctl -u lifecycle-script.service -f`. If you see `Finished Run lifecycle scripts.` at the bottom, then you're ready to proceed. Otherwise, wait until setup has completed. It can take ~10 minutes, as kernels are being compiled for the GPU and large model files are being downloaded.

# Benchmarking
After setup has completed, let's run a quick benchmark! Navigate to `/workspace/llama3-qserve/qserve` and run the below commands:

```bash
export MODEL=qserve_checkpoints/Llama-3-8B-Instruct-QServe-g128 GLOBAL_BATCH_SIZE=128 NUM_GPU_PAGE_BLOCKS=3200
python qserve_benchmark.py --model $MODEL --benchmarking --precision w4a8kv4 --group-size 128
```

This will run a few rounds of benchmarking with 1024 sequence length, 512 output length, and 128 batch size. The throughput is logged to stdout and the results will be saved to `results.csv`. Once completed, you should see `Round 2 Throughput: 3568.7845477930728 tokens / second.` (though your numbers may be slightly different).

# Chat.py
We've included a simple chat script to show how to use the QServe Python library. To use the script, move it into the `qserve` root directory, then run the below command:

```bash
python chat.py --model $MODEL_PATH --ifb-mode --precision w4a8kv4 --quant-path $MODEL_PATH --group-size 128
```

This will bring up a command line chat interface, simply type a prompt and hit enter to send it to the QServe engine. You'll see the assistant's response in `stdout` and can continue the conversation. Type `exit` and hit enter when you want to terminate the script.

Within `chat.py`, you can see that we begin by parsing the engine arguments which dictate the model being used, quantization configuration, etc.

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Demo on using the LLMEngine class directly"
    )
    parser = EngineArgs.add_cli_args(parser)
    args = parser.parse_args()
    main(args)
```

Then, we instantiate the engine.

```python
def initialize_engine(args: argparse.Namespace) -> LLMEngine:
    """Initialize the LLMEngine from the command line arguments."""
    engine_args = EngineArgs.from_cli_args(args)
    return LLMEngine.from_engine_args(engine_args)
```

In main, we register a conversation template (in this case, Llama3-8B-Instruct) and configure our sampling parameters.

```python
def main(args: argparse.Namespace):
    """Main function that sets up and runs the prompt processing."""
    engine = initialize_engine(args)
    conv_t = get_conv_template_name(args.model)
    conv = get_conv_template(conv_t)
    sampling_params = SamplingParams(temperature=0.7, top_p=1.0, stop_token_ids=[128001, 128009], max_tokens=1024)
```

Then, we enter a loop where the bulk of the functionality is defined. To send a request to the engine, we first append the message to our conversation which takes care of formatting and applying the model's template. By calling `get_prompt()`, we receive the conversation history in an appropriate format for the LLM to generate from. Finally, we add the request by sending a `request_id` 

```python
conv.append_message(conv.roles[0], user_input)
conv.append_message(conv.roles[1], "")
prompt = conv.get_prompt()
engine.add_request(0, prompt, sampling_params)
```

If `ifb_mode` is on, the engine will automatically schedule and pack requests for continuous/in-flight batching with no changes to the code. For this application, you won't notice any changes however it is a drastic improvement when serving multiple concurrent users.

To progress the engine, we call `engine.step()` and log the current outputs. We then check their status and see if any have finished. If we were serving concurrent users, we would want to use the request identifier in order to match results and route back to the correct user.

```python
request_outputs = engine.step()
for request_output in request_outputs:
    if request_output["finished"]:
        response = request_output["text"]
        ext_response = extract_llama3_assistant(response)
        print(f"Assistant: {ext_response}")
        conv.update_last_message(ext_response)
```



# Clean Up
To clean up the resources used, run the below commands:

```bash
crusoe compute vms stop qserve-vm
crusoe compute vms delete qserve-vm
crusoe storage disks delete qserve-disk-1
```
