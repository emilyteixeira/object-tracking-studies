"""
Exporta o modelo YOLO para TensorRT FP16 (RTX 4060).

Execute UMA única vez antes de iniciar o backend:
    python export_tensorrt.py

Requisitos:
    - NVIDIA driver + CUDA instalados
    - TensorRT instalado (pip install tensorrt ou via NVIDIA TensorRT SDK)
    - ultralytics >= 8.x

O arquivo gerado (yolo11n.engine) é específico da GPU e SO atuais.
Se trocar de máquina ou atualizar drivers, rode este script novamente.
"""

from ultralytics import YOLO

SOURCE_MODEL = "yolo11n.pt"
OUTPUT_ENGINE = "yolo11n.engine"

print(f"Carregando {SOURCE_MODEL} ...")
model = YOLO(SOURCE_MODEL)

print("Exportando para TensorRT FP16 (isso pode levar alguns minutos) ...")
model.export(
    format="engine",
    device=0,       # GPU 0 (RTX 4060)
    half=True,      # FP16
    imgsz=640,
    batch=1,
    workspace=4,    # GB de workspace para o otimizador TensorRT
    verbose=False,
)

print(f"\nPronto! Modelo exportado: {OUTPUT_ENGINE}")
print("O backend/config.py já aponta para yolo11n.engine — pode iniciar o servidor.")
