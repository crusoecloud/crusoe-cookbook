# Getting Started
Ensure that your environment is set up according to the instructions in the root of this repository. To run text-generation-inference, we'll use Docker which is pre-installed in our disk image.

## Configure tmux
Same as for vllm, we'll set up two panes to monitor our client and server. Create a tmux session with `tmux new -s tgi` which will automatically attach. Create a split vertical pane with `ctrl+b` then `%`. Navigate to the right pane where we will start the server. Run the below command to download and run the docker container.

```bash
docker run --gpus all --shm-size 1g -p 8080:80 -v /workspace/models:/models ghcr.io/huggingface/text-generation-inference:latest --model-id /models/dbrx-instruct --tokenizer-config-path /models/dbrx-instruct-tokenizer/tokenizer_config.json --num-shard 8
```

Now, navigate back to the left pane and create a virtual environment with `virtualenv venv && source venv/bin/activate`. Install requirements with `pip install -r requirements.txt` and run our client with `python client.py`. Opening up this file, you'll see that we modify the OpenAI Python client to point at our TGI server with just a couple of lines while reusing the familiar OpenAI Messages API.
