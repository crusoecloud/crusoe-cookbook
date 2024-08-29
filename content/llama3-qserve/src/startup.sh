#!/bin/bash

mkfs.ext4 /dev/vdb
mkdir /workspace
mount -t ext4 /dev/vdb /workspace

cd /workspace
git clone git@github.com:crusoecloud/llama3-qserve.git
cd llama3-qserve/

mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh

eval "$(~/miniconda3/bin/conda init bash)"
eval "$(~/miniconda3/bin/conda shell.bash hook)"

git clone https://github.com/mit-han-lab/qserve.git
cd qserve
sed -i 's/xformers/xformers==0.0.26.post1/' pyproject.toml

# Create and activate conda environment
conda create -n QServe python=3.10 -y
conda activate QServe

pip install --upgrade pip
pip install -e .
pip install flash-attn --no-build-isolation

cd kernels
python setup.py install

cd ..
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install git-lfs

mkdir -p qserve_checkpoints && cd qserve_checkpoints
git clone https://huggingface.co/mit-han-lab/Llama-3-8B-Instruct-QServe-g128
cd ..
