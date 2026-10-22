"""Backend registry. Each backend exposes `extract(pdf, page_index, **opts) -> DocumentPrediction`.

Model-backed backends import heavy dependencies lazily and run in the optional venv
(`.venv-docling`); `findoclens.runner` dispatches to the right interpreter.
"""
import importlib

REGISTRY = {
    "native_v2": ("findoclens.backends.native_v2", "extract"),
    "native_grid": ("findoclens.backends.native_grid", "extract"),
    "docling": ("findoclens.backends.docling_backend", "extract"),
    "ocr_rapid": ("findoclens.backends.docling_backend", "extract_ocr"),
    "docling_regions": ("findoclens.backends.docling_backend", "extract_regions"),
}
# Backends that need the optional model environment
MODEL_BACKENDS = {"docling", "ocr_rapid", "docling_regions"}


def get(name):
    mod, fn = REGISTRY[name]
    return getattr(importlib.import_module(mod), fn)
