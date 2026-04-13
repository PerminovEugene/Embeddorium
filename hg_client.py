from huggingface_hub import login
from sentence_transformers import SentenceTransformer

from config import HG_TOKEN


class HgClient:
    def get_model(self, model_name) -> SentenceTransformer:
        login(HG_TOKEN)
        return SentenceTransformer(model_name)
