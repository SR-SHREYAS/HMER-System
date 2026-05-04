import os
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import io
import gc

from latex_formatter import format_sequence_as_latex
from mtl.datamodule import vocab
from mtl.lit_mtl import LitMTL
from torchvision.transforms import ToTensor
import torch

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.set_float32_matmul_precision("medium")

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "hmer_ux"


def resolve_checkpoint() -> str:
    candidates = [
        os.getenv("HMER_CKPT"),
        str(ROOT / "epoch=91-step=69091-val_ExpRate=0.6355.ckpt"),
        str(ROOT / "checkpoints" / "last.ckpt"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("No checkpoint found for demo server.")


def load_model() -> LitMTL:
    ckpt = resolve_checkpoint()
    try:
        model = LitMTL.load_from_checkpoint(ckpt)
    except TypeError:
        model = LitMTL.load_from_checkpoint(ckpt, lambda_1=1.0, lambda_2=1.0)
    print(f"Loaded checkpoint: {ckpt}")
    return model.eval().to(DEVICE)


model = load_model()

origins = [
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500",
    "http://localhost:63342",
    "http://localhost:8000",
    "http://localhost:5500",
    "*",  # Allow all for local dev
]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=UI_DIR), name="assets")


@app.get("/")
async def index():
    return FileResponse(UI_DIR / "index.html")


@app.post("/predict")
async def predict_sequence(
        image: UploadFile = File(...)
):
    contents = await image.read()

    img, mask = await pipe(contents)
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        with torch.inference_mode():
            hyp = await model.async_approximate_joint_search(img.unsqueeze(0), mask)
            hyp = hyp[0]
    except torch.cuda.OutOfMemoryError as e:
        print("CUDA OOM error:", e)
        return JSONResponse(
            content={"error": "Can not parse this image"},
            status_code=422
        )

    pred_sequence = vocab.indices2label(hyp.seq)
    pred_latex = format_sequence_as_latex(pred_sequence)
    del img, mask, hyp
    torch.cuda.empty_cache()
    gc.collect()
    print(pred_sequence)
    return JSONResponse(
        content={"sequence": pred_sequence, "latex": pred_latex},
        status_code=200
    )


@app.get("/health")
async def health():
    return {"status": "ok", "device": str(DEVICE)}


async def pipe(contents):
    img = Image.open(io.BytesIO(contents)).convert("L").resize((200, 100))
    img.save('test.jpg')
    tensor = ToTensor()(img).to(DEVICE)
    mask = torch.zeros_like(tensor, dtype=torch.bool).to(DEVICE)
    return tensor, mask
# fastapi run demo.py
# fastapi run demo.py
