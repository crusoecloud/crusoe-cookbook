# Getting Started
Ensure that you have configured your VM according to the README in the root of this repository before proceeding.

## Dependencies
Initialize a virtualenv with `virtualenv venv` and activate it with `source venv/bin/activate`. First, run `pip install packaging` which is required for flash attention. Then, install core dependencies with `pip install -r requirements.txt`.

## vllm_example.py
The simplest example, pulled from the vLLM repo, only requires a couple of lines to work with with our setup. We point the model and tokenizer paths to our local directories and set `tensor_parallel_size` to 8 when initializing our `LLM` to shard the model across GPUs in our L40S node.

## OpenAI API Server
With our virtual environment activated, run `pip install openai`. Now, start a tmux session with `tmux new -s vllm`. After executing the previous command, you'll be automatically attached to the session and can detach at any time with `CTRL+b` then `d`. To re-attach to that session, do `tmux a -t vllm`. 

Now, we'll split our tmux session into two panes (one for the client and one for the server). Make sure you are attached to the tmux session, then do `ctrl+b` then `%`. This will split our tmux session into two vertical panes. If you wish to navigate between the two, simply do `ctrl+b` then press the corresponding arrow key to switch between left/right. In both sessions, activate the virtual environment.

Activate the right pane and run this command to start the server: `python -m vllm.entrypoints.openai.api_server --model /workspace/models/dbrx-instruct --tokenizer /workspace/models/dbrx-instruct-tokenizer --dtype auto --tensor-parallel-size 8 --trust-remote-code`. Switch back to the left pane with `ctrl+b` and the left arrow key. After the server has started (you'll see logs indicating that the Uvicorn server is running on http://0.0.0.0:8000), run `python client.py`.

In the server pane, you'll see running metrics for throughput average and resource usage. On the left, you'll see a print-out of the server response.

*Congrats!* You have a scalable backend with continuous batching capable of serving concurrent users with DBRX-Instruct. Note that this defaults to 4k context length and requires some modifications to reach 32k. In the next part of this tutorial, we'll look at how to optimize inference.
