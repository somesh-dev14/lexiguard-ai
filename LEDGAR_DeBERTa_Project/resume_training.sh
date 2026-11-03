#!/usr/bin/env bash
# Resume LEDGAR DeBERTa-v3-base training
CHECKPOINT="${1:-auto}"
echo "Resuming training from: ${CHECKPOINT}"

cd /workspace/LEDGAR_DeBERTa_Project
nohup python train.py \
  --max_seq_length 512 \
  --batch_size 2 \
  --grad_accum 8 \
  --learning_rate 1e-5 \
  --epochs 3 \
  --save_steps 500 \
  --eval_steps 500 \
  --resume_from_checkpoint "${CHECKPOINT}" > logs/remote_train.log 2>&1 &

echo "Training resumption started in background. Monitor with: tail -f logs/remote_train.log"
