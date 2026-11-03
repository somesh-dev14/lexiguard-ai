"""
Classifier Service for LexiGuard AI
Loads the LEDGAR DeBERTa/ModernBERT classifier once per application lifecycle.
Uses the verified local model directory and handles sys.path imports safely.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger("lexiguard.classifier")


class ClassifierService:
    def __init__(self):
        self._classifier = None
        self._is_loaded = False
        self._load_error: Optional[str] = None

    def load_model(self, force: bool = False) -> None:
        """
        Loads the classifier model once into memory.
        """
        if self._is_loaded and not force:
            return

        # Ensure system site-packages (containing PyTorch/Transformers) are in sys.path
        system_site_packages = r"C:\Users\warso\AppData\Local\Programs\Python\Python312\Lib\site-packages"
        if Path(system_site_packages).exists() and system_site_packages not in sys.path:
            sys.path.append(system_site_packages)

        # Ensure classifier module directory is in sys.path
        classifier_src = str(Path(settings.CLASSIFIER_SRC_DIR).resolve())
        if classifier_src not in sys.path:
            sys.path.insert(0, classifier_src)

        model_dir = str(Path(settings.MODEL_DIR).resolve())
        if not Path(model_dir).exists():
            self._load_error = f"Pretrained model directory not found at: {model_dir}"
            logger.error(self._load_error)
            raise FileNotFoundError(self._load_error)

        try:
            logger.info("Initializing LegalClauseClassifier from %s...", model_dir)
            from legal_clause_classifier import LegalClauseClassifier
            self._classifier = LegalClauseClassifier(model_dir=model_dir)
            self._is_loaded = True
            self._load_error = None
            logger.info("LegalClauseClassifier successfully loaded on %s", self._classifier.device)
        except Exception as e:
            self._load_error = f"Failed to load classifier: {str(e)}"
            self._is_loaded = False
            self._classifier = None
            logger.exception(self._load_error)
            raise RuntimeError(self._load_error) from e

    def is_available(self) -> bool:
        return self._is_loaded and self._classifier is not None

    def classify(self, text: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        Classifies clause text and returns top predictions.
        """
        if not self.is_available():
            self.load_model()

        k = top_k or settings.CLASSIFIER_TOP_K
        return self._classifier.classify_clause(text=text, top_k=k)


# Singleton instance
classifier_service = ClassifierService()
