param(
    [string]$CheckpointPath = "auto"
)

Write-Host "Resuming LEDGAR DeBERTa-v3-base Training from $CheckpointPath..." -ForegroundColor Cyan
python train.py `
  --max_seq_length 512 `
  --batch_size 2 `
  --grad_accum 8 `
  --learning_rate 1e-5 `
  --epochs 3 `
  --resume_from_checkpoint $CheckpointPath
