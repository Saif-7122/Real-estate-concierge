import os
import logging
import threading
from functools import lru_cache

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_astradb import AstraDBVectorStore

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
COLLECTION_NAME = "brochure_chunks"

# ---------------------------------------------------------------------------
# Process-level singletons — created at most once per gunicorn worker process.
# A threading.Lock guards the lazy-init path so concurrent first requests in a
# multi-threaded worker don't each try to load the model simultaneously.
# ---------------------------------------------------------------------------
_singleton_lock = threading.Lock()
_retriever_singleton = None


@lru_cache(maxsize=1)
def _get_embeddings_singleton():
    """
    Load the HuggingFace embeddings exact once per process.
    If HF_API_TOKEN is set, it uses the remote Inference API to save memory.
    Otherwise, it falls back to a local model (used for local ingestion).
    """
    model_name = os.getenv("HF_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    hf_token = os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    
    if hf_token:
        logger.info("Loading HuggingFaceEndpointEmbeddings (Remote API) for model: %s (one-time per process)", model_name)
        return HuggingFaceEndpointEmbeddings(model=model_name, huggingfacehub_api_token=hf_token)
    else:
        logger.warning("No HF_API_TOKEN found. Falling back to local HuggingFaceEmbeddings. THIS WILL CONSUME ~400MB RAM.")
        from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=model_name)


@lru_cache(maxsize=1)
def _get_vector_store_singleton() -> AstraDBVectorStore:
    """
    Create the AstraDBVectorStore connection exactly once per process.

    Reuses the already-cached embeddings singleton, so the model is never
    reloaded regardless of how many times this is called.
    """
    api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
    token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
    namespace = os.getenv("ASTRA_DB_KEYSPACE")

    if not api_endpoint or not token:
        raise ValueError(
            "Missing Astra DB credentials. Please ensure ASTRA_DB_API_ENDPOINT and "
            "ASTRA_DB_APPLICATION_TOKEN are set in your environment or .env file."
        )

    logger.info("Initialising AstraDBVectorStore singleton (one-time per process)")
    kwargs = {
        "collection_name": COLLECTION_NAME,
        "embedding": _get_embeddings_singleton(),
        "api_endpoint": api_endpoint,
        "token": token,
    }
    if namespace:
        kwargs["namespace"] = namespace

    return AstraDBVectorStore(**kwargs)


def get_brochure_retriever(k: int = 4):
    """
    Returns a retriever for brochure chunks from the Astra DB vector store.

    The underlying HuggingFaceEmbeddings model and AstraDBVectorStore are
    instantiated **once per process** (module-level singletons via lru_cache).
    Subsequent calls — including every /chat request that hits the brochure
    route — reuse the already-loaded objects with zero reloading overhead,
    which eliminates the OOM crashes caused by repeated model loads under load.

    The public signature is unchanged; callers in nodes.py continue to call
    ``get_brochure_retriever()`` exactly as before.

    Args:
        k (int): Number of document chunks to retrieve (default: 4).

    Returns:
        A LangChain VectorStoreRetriever backed by the singleton AstraDB store.
    """
    return _get_vector_store_singleton().as_retriever(search_kwargs={"k": k})


# ---------------------------------------------------------------------------
# The functions below are kept for backwards compatibility with any code that
# calls them directly (e.g. ingestion scripts, tests).  They now delegate to
# the cached singletons rather than constructing new instances each time.
# ---------------------------------------------------------------------------

from langchain_core.embeddings import Embeddings

def get_embeddings(model_name: str = None) -> Embeddings:
    """Returns the shared HuggingFaceEmbeddings singleton.

    The ``model_name`` argument is accepted for API compatibility but is only
    respected on the very first call (when the singleton is built).  Pass
    ``None`` to use the value from the ``HF_EMBEDDING_MODEL`` env var.
    """
    if model_name and model_name != os.getenv("HF_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL):
        # Caller wants a *different* model — fall back to a fresh instance so
        # ingestion scripts can still override the model name explicitly.
        logger.warning(
            "get_embeddings() called with model_name=%r which differs from the "
            "singleton model.  Creating a separate instance (not cached).",
            model_name,
        )
        from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=model_name)
    return _get_embeddings_singleton()


def get_vector_store(collection_name: str = COLLECTION_NAME) -> AstraDBVectorStore:
    """Returns the shared AstraDBVectorStore singleton.

    The ``collection_name`` argument is accepted for API compatibility; the
    singleton always targets ``COLLECTION_NAME``.  Pass a different name only
    from ingestion scripts that genuinely need a separate collection.
    """
    if collection_name != COLLECTION_NAME:
        # Caller targets a different collection — build a one-off instance.
        logger.warning(
            "get_vector_store() called with collection_name=%r which differs from "
            "the singleton collection %r.  Creating a separate instance (not cached).",
            collection_name,
            COLLECTION_NAME,
        )
        api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        namespace = os.getenv("ASTRA_DB_KEYSPACE")
        kwargs = {
            "collection_name": collection_name,
            "embedding": _get_embeddings_singleton(),
            "api_endpoint": api_endpoint,
            "token": token,
        }
        if namespace:
            kwargs["namespace"] = namespace
        return AstraDBVectorStore(**kwargs)

    return _get_vector_store_singleton()
