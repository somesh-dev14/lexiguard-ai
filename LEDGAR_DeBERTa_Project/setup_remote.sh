#!/usr/bin/env bash
set -e

echo "=== LEDGAR DeBERTa-v3-base Remote GPU Setup ==="

# 1. Ensure persistent directory
WORKSPACE_DIR="/workspace/LEDGAR_DeBERTa_Project"
if [ ! -d "/workspace" ]; then
    echo "Notice: /workspace directory not found. Using current working directory."
    WORKSPACE_DIR="$(pwd)"
fi

mkdir -p "${WORKSPACE_DIR}/checkpoints"
mkdir -p "${WORKSPACE_DIR}/final_model"
mkdir -p "${WORKSPACE_DIR}/logs"
mkdir -p "${WORKSPACE_DIR}/results"

cd "${WORKSPACE_DIR}"

# 2. Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run Pre-flight Smoke Test
echo "Running Pre-flight Smoke Test..."
python remote_smoke_test.py

echo "=== Setup & Pre-flight Verification Complete ==="
echo "To start training in the background with persistent logging, run:"
echo "nohup python train.py --max_seq_length 512 --batch_size 2 --grad_accum 8 --learning_rate 1e-5 --epochs 3 > logs/remote_train.log 2>&1 &"
