import os
import sys
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore

load_dotenv()

DEFAULT_PDF_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "brochure_sample.txt")
)
COLLECTION_NAME = "brochure_chunks"
EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


def ingest_brochure(file_path: str = DEFAULT_PDF_PATH, collection_name: str = COLLECTION_NAME):
    """
    Loads a brochure PDF, splits into chunks, tags metadata, embeds with HuggingFace,
    and inserts into an AstraDBVectorStore collection.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: {file_path}")

    api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
    token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
    namespace = os.getenv("ASTRA_DB_KEYSPACE")

    if not api_endpoint or not token:
        raise ValueError(
            "Missing Astra DB credentials in environment variables. "
            "Please check ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN."
        )

    print(f"Loading file from: {file_path} ...")
    if file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        loader = PyPDFLoader(file_path)
    docs = loader.load()
    print(f"Loaded {len(docs)} page(s).")

    print("Splitting documents into chunks (chunk_size=800, overlap=120)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Generated {len(chunks)} chunk(s).")

    # Tag each chunk's metadata with source="brochure"
    for chunk in chunks:
        chunk.metadata["source"] = "brochure"

    print(f"Initializing embedding model: {EMBEDDING_MODEL} ...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f"Connecting to Astra DB collection: '{collection_name}' ...")
    store_kwargs = {
        "collection_name": collection_name,
        "embedding": embeddings,
        "api_endpoint": api_endpoint,
        "token": token,
    }
    if namespace:
        store_kwargs["namespace"] = namespace

    vector_store = AstraDBVectorStore(**store_kwargs)

    print(f"Pushing {len(chunks)} chunks to Astra DB...")
    inserted_ids = vector_store.add_documents(chunks)
    print(f"Successfully indexed {len(inserted_ids)} chunks into collection '{collection_name}'!")
    return inserted_ids


if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF_PATH
    try:
        ingest_brochure(file_path=target_path)
    except Exception as e:
        print(f"Error during brochure ingestion: {e}", file=sys.stderr)
        sys.exit(1)
