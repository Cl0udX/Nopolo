import os
import torch

from fairseq import checkpoint_utils


def get_index_path_from_model(sid):
    return next(
        (
            f
            for f in [
                os.path.join(root, name)
                for root, _, files in os.walk(os.getenv("index_root"), topdown=False)
                for name in files
                if name.endswith(".index") and "trained" not in name
            ]
            if str(sid).split(".")[0] in f
        ),
        "",
    )


def load_hubert(config, hubert_path: str):
    # PyTorch 2.6+ requiere weights_only=False para modelos antiguos
    # Guardar la función original
    original_load = torch.load
    
    # Crear wrapper que fuerza weights_only=False
    def load_with_legacy_support(*args, **kwargs):
        kwargs['weights_only'] = False
        return original_load(*args, **kwargs)
    
    # Monkey-patch temporal
    torch.load = load_with_legacy_support
    
    try:
        models, _, _ = checkpoint_utils.load_model_ensemble_and_task(
            [hubert_path],
            suffix="",
        )
        hubert_model = models[0]
        hubert_model = hubert_model.to(config.device)
        hubert_model = hubert_model.half() if config.is_half else hubert_model.float()
        return hubert_model.eval()
    finally:
        # Restaurar torch.load original
        torch.load = original_load
