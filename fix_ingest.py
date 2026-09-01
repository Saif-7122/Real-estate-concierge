import os

path = r"d:\Realestate coincerge\real-estate-concierge\backend\ingestion\ingest_brochure.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add TextLoader to imports
content = content.replace(
    "from langchain_community.document_loaders import PyPDFLoader",
    "from langchain_community.document_loaders import PyPDFLoader, TextLoader"
)

# Update DEFAULT_PDF_PATH to text file
content = content.replace(
    '"data", "brochure_sample.pdf"',
    '"data", "brochure_sample.txt"'
)

# Update parameter name
content = content.replace(
    "def ingest_brochure(pdf_path: str = DEFAULT_PDF_PATH",
    "def ingest_brochure(file_path: str = DEFAULT_PDF_PATH"
)

# Update loading logic
old_load = """    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

    api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
    token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
    namespace = os.getenv("ASTRA_DB_KEYSPACE")

    if not api_endpoint or not token:
        raise ValueError(
            "Missing Astra DB credentials in environment variables. "
            "Please check ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN."
        )

    print(f"Loading PDF from: {pdf_path} ...")
    loader = PyPDFLoader(pdf_path)"""

new_load = """    if not os.path.exists(file_path):
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
        loader = PyPDFLoader(file_path)"""

content = content.replace(old_load, new_load)

# Update main invocation
content = content.replace(
    "ingest_brochure(pdf_path=target_path)",
    "ingest_brochure(file_path=target_path)"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("ingest_brochure.py updated to support txt.")
