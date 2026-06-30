from huggingface_hub import login
from sentence_transformers import SentenceTransformer

from backend.shared.config import HG_TOKEN


class HgClient:
    def __init__(self) -> None:
        self._models: dict[str, SentenceTransformer] = {}
        self._is_logged_in = False

    def _login_once(self) -> None:
        if self._is_logged_in:
            return

        if HG_TOKEN:
            login(token=HG_TOKEN)

        self._is_logged_in = True

    def get_model(self, model_name: str) -> SentenceTransformer:
        self._login_once()

        if model_name not in self._models:
            self._models[model_name] = SentenceTransformer(model_name)

        return self._models[model_name]

    def get_model_size(self, model_name: str) -> int:
        model = self.get_model(model_name)
        return model.get_embedding_dimension()