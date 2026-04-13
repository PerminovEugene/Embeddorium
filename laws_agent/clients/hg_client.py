from huggingface_hub import login
from sentence_transformers import SentenceTransformer

from laws_agent.config import HG_TOKEN


class HgClient:
    def get_model(self, model_name: str) -> SentenceTransformer:
        login(HG_TOKEN)
        return SentenceTransformer(model_name)
