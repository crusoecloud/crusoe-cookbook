# Getting Started

## Crusoe CLI
In this tutorial, we will be running DBRX-Instruct on L40S instances provided by Crusoe Cloud using the CLI. First, ensure that you have the CLI installed by following the instructions [here](https://docs.crusoecloud.com/quickstart/installing-the-cli/index.html) and verify your installation with `crusoe whoami`.

## Starting a VM
We'll run DBRX-Instruct on an L40S.8x instance with our batteries-included NVIDIA image. To create the VM using the CLI, run the following command:

```bash
crusoe compute vms create \
  --name dbrx-inference \
  --type l40s-48gb.8x \
  --location us-east1-a \
  --image ubuntu22.04-nvidia-sxm-docker:latest \
  --keyfile ~/.ssh/id_ed25519.pub
```

Wait a few minutes for the VM to be created, then note the public IP. Verify that you are able to access the instance with `ssh ubuntu@<public ip address>`. Then, exit the VM and we'll set up a storage disk to load our massive MoE model. If you didn't log the public IP, simply open up your Instances tab on the Crusoe Console and copy the address from there.

## Creating and Attaching a Persistent Disk
It's always recommended to create a disk to avoid misusing the boot disk (128 GiB), but particularly with LLMs we can run out of storage very quickly. The DBRX-Instruct repo is 490 GiB, so we'll create a 1TiB disk for some breathing room. Back on your local machine with the crusoe CLI installed, run the following to create a disk:

```bash
crusoe storage disks create \
  --name dbrx-data \
  --size 1TiB \
  --location us-east1-a
```

Now, let's attach the disk to our instance with:

```bash
crusoe compute vms attach-disks dbrx-inference --disk name=dbrx-data,mode=read-write
```

SSH into your instance (`ssh ubuntu@<public ip address>`) and run `lsblk`. The persistent disk will show up as `vd[b-z]`. Now, create the filesystem by running:

```bash
sudo mkfs.ext4 /dev/vdb
```

Create a directory to mount the volume. For this tutorial, we'll run `sudo mkdir /workspace/`. Finally, mount the volume by running:

```bash
sudo mount -t ext4 /dev/vdb /workspace && sudo chown -R ubuntu:ubuntu /workspace
```

You can verify that the volume was mounted by running `lsblk` again and seeing `/workspace` attached to vdb under MOUNTPOINTS.

## Clone DBRX-Instruct and DBRX-Instruct-Tokenizer
For simplicity, we will clone the repos for both the instruct model and tokenizer (as opposed to letting HF handle caching) and provide local paths when loading our resources. Navigate to `/workspace` and run the command `mkdir models && cd models/`.

DBRX-Instruct is a gated model, so you will need to request permission in order to interact with the model. Please refer to the [DBRX-Instruct repo for steps](https://huggingface.co/databricks/dbrx-instruct#:~:text=DBRX%20Instruct%20is%20a%20mixture,it%2C%20under%20an%20open%20license.) on how to do so.

### Git LFS
HuggingFace uses lfs to manage large files, so we'll have to run a couple commands to get it set up:

```bash
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash

sudo apt-get install git-lfs
```
You can verify git lfs is set up with `git lfs --version`.

### Clone DBRX-Instruct
Now, clone the repository with `git clone https://huggingface.co/databricks/dbrx-instruct`. NOTE: you will be prompted for your hugging face username and password, provide your ACCESS TOKEN when prompted for your password.

This will kick off the download for the entire repo which is ~490 GiB. Luckily, this is running on our VM on a site with high-speed networking 😁. Even so, download speed can be limited by demand on the host server so feel free to go grab coffee and come back when the download is done.

### Clone DBRX-Instruct-Tokenizer
We'll use the fast tokenizer provided by Xenova, so again navigate to `/workspace/models/` and clone [this repository](https://huggingface.co/Xenova/dbrx-instruct-tokenizer/tree/main).

## Clone this Repo
We'll make a directory to hold code on our boot disk. Run `mkdir ~/dev && cd ~/dev` and clone into this repository with `git clone git@github.com:crusoecloud/dbrx_inference_tutorial.git && cd dbrx_inference_tutorial/`.

## Peripherals
Before we jump into our inference tutorials, let's install some quality-of-life peripherals. First, run `apt-get update` then `apt-get install tmux`. We'll often have two or more processes running, so it'll be nice to have multiple windows to monitor each and tmux is a great solution for session and window management.

To manage dependencies, we'll use `virtualenv` which can be installed with `apt install python3-virtualenv`.

If you run into issues with storage, `ncdu` is a useful tool for easy navigation.

Additionally, I recommend using [ssh-remote](https://code.visualstudio.com/docs/remote/ssh#_connect-to-a-remote-host) with VSCode to connect and interact with remote code (unless you're a vim wizard).

# vLLM
The fastest way to get up and running with DBRX-Instruct is [vLLM](https://github.com/vllm-project/vllm). In a few steps, we'll have a high-performance, OpenAI-API compatible server up and running. For more details, reference the README in `vLLM/` in this repo.

# TGI
To serve DBRX-Instruct through `text-generation-inference` by HuggingFace, refer to the README in `tgi/` in this repo.

# Cleaning Up
To delete our VM and the disk, we can simply run the following commands using the CLI:

```bash
crusoe compute vms delete --name dbrx-inference && crusoe storage disks delete dbrx-data
```
