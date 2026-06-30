import logging
from typing import Optional

from sentence_transformers import SentenceTransformer
from transformers import pipeline

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google/gemma-4-27b-it"


class LlmClient:
    """Client for HuggingFace models — generative via transformers pipeline""
    ""embeddings via SentenceTransformer."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        embedding_model: Optional[SentenceTransformer] = None,
        device: str = "cpu",
    ):
        self.model_name = model
        self.embedding_model = embedding_model
        self.device = device
        self._pipeline = None

    def get_embedding_dimension(self) -> int:
        """Return embedding vector dimension for the injected SentenceTransformer."""
        if self.embedding_model is None:
            raise ValueError(
                "No embedding model provided — pass a SentenceTransformer to "
                "LlmClient(embedding_model=...)"
            )

        dimension = self.embedding_model.get_sentence_embedding_dimension()

        if dimension is None:
            # Fallback for unusual/custom models
            dimension = len(self.embed("dimension probe"))

        return int(dimension)

    @property
    def _generator(self):
        if self._pipeline is None:
            logger.info("Loading generative model: %s", self.model_name)
            self._pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                device=self.device,
            )
        return self._pipeline

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using the HuggingFace text-generation pipeline."""
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        results = self._generator(
            full_prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
        )
        generated: str = results[0]["generated_text"]
        # Strip the echoed prompt
        #  that transformers pipelines include by default.
        return generated[len(full_prompt):]

    def embed(self, text: str) -> list:
        """Return a float embedding vector for *text* via the injected SentenceTransformer."""
        if self.embedding_model is None:
            raise ValueError(
                "No embedding model provided — pass a SentenceTransformer to LlmClient(embedding_model=...)"
            )
        return self.embedding_model.encode(text).tolist()
