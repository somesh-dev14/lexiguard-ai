import sys
import subprocess

print("=== Python Details ===")
print("Python Executable:", sys.executable)
print("Python Version:", sys.version)

try:
    import torch
    print("\n=== PyTorch & CUDA ===")
    print("PyTorch Version:", torch.__version__)
    print("CUDA Available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Device Count:", torch.cuda.device_count())
        print("Device Name:", torch.cuda.get_device_name(0))
        print("Device Capability:", torch.cuda.get_device_capability(0))
        print("CUDA Version PyTorch was built with:", torch.version.cuda)
        free_mem, total_mem = torch.cuda.mem_get_info(0)
        print(f"VRAM Free: {free_mem / (1024**2):.2f} MB / Total: {total_mem / (1024**2):.2f} MB")
    else:
        print("CUDA is NOT available in this PyTorch installation.")
except ImportError:
    print("\nPyTorch is not installed in the global python environment.")
except Exception as e:
    print("\nError checking PyTorch:", e)

print("\n=== Check Ollama Service ===")
try:
    import urllib.request
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
    with urllib.request.urlopen(req, timeout=3) as resp:
        print("Ollama HTTP API responded:", resp.status, resp.read().decode('utf-8'))
except Exception as e:
    print("Ollama HTTP API not responding (http://127.0.0.1:11434):", e)
