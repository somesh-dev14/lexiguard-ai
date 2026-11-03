Write-Host "Starting LEDGAR DeBERTa-v3-base Training..." -ForegroundColor Cyan
python train.py `
  --max_seq_length 512 `
  --batch_size 2 `
  --grad_accum 8 `
  --learning_rate 1e-5 `
  --epochs 3 `
  --save_steps 500 `
  --eval_steps 500
