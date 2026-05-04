import argparse
import os
import glob
import gc
import traceback
import torch
# import wandb
from pytorch_lightning.loggers import WandbLogger as Logger
from mtl.datamodule import CROHMEDatamodule
from mtl.lit_mtl import LitMTL
from sconf import Config
import pytorch_lightning as pl


# ─── Safety: Use tensor cores, reduce fragmentation ────────────────────────
torch.set_float32_matmul_precision('medium')
torch.backends.cudnn.benchmark = False  # Stable memory usage


def find_latest_checkpoint(checkpoint_dir="checkpoints"):
    """Find the latest checkpoint to resume from."""
    if not os.path.exists(checkpoint_dir):
        return None
    ckpt_files = glob.glob(os.path.join(checkpoint_dir, "*.ckpt"))
    if not ckpt_files:
        return None
    latest = max(ckpt_files, key=os.path.getmtime)
    print(f"[Checkpoint] Found: {latest}")
    return latest


def safe_save_checkpoint(trainer, path):
    """Save checkpoint with error handling."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        trainer.save_checkpoint(path)
        # Verify the file was actually written
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"\n[✓ Checkpoint] Saved at step {trainer.global_step} → {path} ({os.path.getsize(path) / 1024 / 1024:.1f} MB)")
            return True
        else:
            print(f"\n[✗ Checkpoint] File missing or empty: {path}")
            return False
    except Exception as e:
        print(f"\n[✗ Checkpoint] Failed to save: {e}")
        return False


class SaveEveryNSteps(pl.Callback):
    """Save checkpoint every N training steps — crash-proof."""
    def __init__(self, save_dir="checkpoints", every_n_steps=500):
        super().__init__()
        self.save_dir = save_dir
        self.every_n_steps = every_n_steps
        os.makedirs(save_dir, exist_ok=True)

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        if trainer.global_step > 0 and trainer.global_step % self.every_n_steps == 0:
            safe_save_checkpoint(trainer, os.path.join(self.save_dir, "last.ckpt"))

    def on_train_epoch_end(self, trainer, pl_module):
        # Always save at end of every epoch too
        safe_save_checkpoint(trainer, os.path.join(self.save_dir, "last.ckpt"))
        # Keep a numbered backup every 10 epochs
        epoch = trainer.current_epoch
        if epoch % 10 == 0:
            safe_save_checkpoint(
                trainer,
                os.path.join(self.save_dir, f"epoch-{epoch:03d}.ckpt")
            )


class OOMSafeValidation(pl.Callback):
    """Catches OOM during validation so training continues."""
    def on_validation_batch_start(self, trainer, pl_module, batch, batch_idx, dataloader_idx=0):
        torch.cuda.empty_cache()
        gc.collect()

    def on_exception(self, trainer, pl_module, exception):
        if isinstance(exception, (torch.cuda.OutOfMemoryError, RuntimeError)):
            error_msg = str(exception).lower()
            if "out of memory" in error_msg or "cuda" in error_msg:
                print(f"\n[OOM Recovery] Caught: {type(exception).__name__}")
                print("[OOM Recovery] Clearing CUDA cache and continuing training...")
                torch.cuda.empty_cache()
                gc.collect()
                # Save what we have before anything else goes wrong
                safe_save_checkpoint(trainer, os.path.join("checkpoints", "last.ckpt"))
                return  # Don't re-raise — let training continue


class MemoryMonitor(pl.Callback):
    """Logs GPU memory usage periodically."""
    def __init__(self, log_every_n_steps=200):
        super().__init__()
        self.log_every_n_steps = log_every_n_steps

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        if trainer.global_step % self.log_every_n_steps == 0 and torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"\n[GPU Memory] Step {trainer.global_step}: "
                  f"{allocated:.2f}GB used / {reserved:.2f}GB reserved / {total:.1f}GB total "
                  f"({allocated/total*100:.0f}% utilization)")

    def on_validation_start(self, trainer, pl_module):
        # Force cleanup before validation to maximize available memory
        torch.cuda.empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            print(f"\n[GPU Memory] Before validation: {allocated:.2f}GB used")


def get_resume_checkpoint(resume_path=None):
    """Determine which checkpoint to resume from."""
    if resume_path and os.path.exists(resume_path):
        return resume_path

    last_ckpt = os.path.join("checkpoints", "last.ckpt")
    if os.path.exists(last_ckpt) and os.path.getsize(last_ckpt) > 0:
        return last_ckpt

    return find_latest_checkpoint("checkpoints")


def train(config, resume_path=None):
    pl.seed_everything(config.seed_everything, workers=True)

    model_module = LitMTL(
        d_model=config.model.d_model,
        growth_rate=config.model.growth_rate,
        num_layers=config.model.num_layers,
        nhead=config.model.nhead,
        num_decoder_layers=config.model.num_decoder_layers,
        dim_feedforward=config.model.dim_feedforward,
        dropout=config.model.dropout,
        dc=config.model.dc,
        cross_coverage=config.model.cross_coverage,
        self_coverage=config.model.self_coverage,
        lambda_1=config.model.lambda_1,
        lambda_2=config.model.lambda_2,
        beam_size=config.model.beam_size,
        max_len=config.model.max_len,
        alpha=config.model.alpha,
        early_stopping=config.model.early_stopping,
        temperature=config.model.temperature,
        learning_rate=config.model.learning_rate,
        patience=config.model.patience,
    )

    data_module = CROHMEDatamodule(
        zipfile_path=config.data.zipfile_path,
        test_year=config.data.test_year,
        train_batch_size=config.data.train_batch_size,
        eval_batch_size=config.data.eval_batch_size,
        num_workers=config.data.num_workers,
        scale_aug=config.data.scale_aug,
    )

    logger = Logger(
        name=config.wandb.name,
        project=config.wandb.project,
        log_model=config.wandb.log_model,
        config=dict(config),
    )
    logger.watch(model_module, log="all", log_freq=100)

    # --- Callbacks ---
    lr_callback = pl.callbacks.LearningRateMonitor(
        logging_interval=config.trainer.callbacks[0].init_args.logging_interval
    )

    best_checkpoint_callback = pl.callbacks.ModelCheckpoint(
        dirpath="checkpoints",
        save_top_k=config.trainer.callbacks[1].init_args.save_top_k,
        monitor=config.trainer.callbacks[1].init_args.monitor,
        mode=config.trainer.callbacks[1].init_args.mode,
        filename=config.trainer.callbacks[1].init_args.filename,
        save_last=True,
    )

    step_checkpoint = SaveEveryNSteps(save_dir="checkpoints", every_n_steps=500)
    oom_safe = OOMSafeValidation()
    mem_monitor = MemoryMonitor(log_every_n_steps=200)

    # --- Resume ---
    resume_ckpt = get_resume_checkpoint(resume_path)

    if resume_ckpt:
        print(f">>> RESUMING from checkpoint: {resume_ckpt}")
        print(f"    Checkpoint size: {os.path.getsize(resume_ckpt) / 1024 / 1024:.1f} MB")
    else:
        print(">>> Starting training from scratch")

    trainer = pl.Trainer(
        gpus=config.trainer.gpus,
        accelerator=config.trainer.accelerator,
        check_val_every_n_epoch=config.trainer.check_val_every_n_epoch,
        max_epochs=config.trainer.max_epochs,
        deterministic=config.trainer.deterministic,
        logger=logger,
        callbacks=[
            lr_callback,
            best_checkpoint_callback,
            step_checkpoint,
            oom_safe,
            mem_monitor,
        ],
        resume_from_checkpoint=resume_ckpt,
    )

    trainer.fit(model_module, data_module)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--resume", type=str, default=None,
    help="Path to checkpoint to resume from")
    args = parser.parse_args()
    config = Config(args.config)

    # Top-level crash recovery — if ANYTHING fails, try to explain why
    try:
        train(config, resume_path=args.resume)
    except torch.cuda.OutOfMemoryError:
        print("\n" + "=" * 60)
        print("[FATAL OOM] Training stopped due to GPU memory exhaustion")
        print("Your checkpoint should be in: checkpoints/last.ckpt")
        print("Fix: reduce train_batch_size or beam_size in config.yaml")
        print("Then re-run the same command — it will auto-resume.")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n[Interrupted] Training stopped by user.")
        print("Checkpoint should be in: checkpoints/last.ckpt")
        print("Re-run the same command to resume.")
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FATAL ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        print("=" * 60)
        print("Your checkpoint should be in: checkpoints/last.ckpt")
        print("Re-run the same command to resume.")
