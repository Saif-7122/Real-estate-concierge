# Real Estate Concierge

A specialized AI concierge system designed to answer complex real estate inquiries by intelligently routing between structured property data and unstructured brochure content. By combining SQL-based logic for inventory management with vector-based semantic search for narrative details, the system provides accurate, multi-faceted answers to prospective buyers without relying on general LLM knowledge.

## Why this is different

Most real estate chatbots ingest everything into a single vector database, which leads to hallucinations when users ask logic-based questions (e.g., "Which 3-bedroom units are available under $800k?"). This project solves that by implementing a strict **hallucination guardrail**: a LangGraph routing layer that intercepts incoming queries and directs them to the appropriate retrieval mechanism. Hard data questions are queried deterministically against a structured SQLite database, while questions about amenities, neighborhood vibes, or building policies are sent to an AstraDB vector store. This ensures the AI only answers based on explicit, grounded data.

## Architecture

The system is built on a **LangGraph** routing architecture:
1. **Query Router:** Analyzes the user's intent to determine if the question requires structured data (inventory, pricing, availability) or unstructured data (amenities, policies, neighborhood).
2. **Structured Path:** Queries a SQLite database using deterministic logic to pull precise inventory data.
3. **Unstructured Path:** Embeds the query using HuggingFace inference (bge-small-en-v1.5) and performs a similarity search against DataStax AstraDB, which holds chunked PDFs of property brochures.
4. **Synthesis:** An LLM (powered by Groq) synthesizes the retrieved context into a natural, conversational response.

## How it's deployed

This system is designed for both local orchestration and cloud-native portability:
- **Local/Kubernetes:** The architecture was originally containerized and tested locally using Minikube, with GCP-portable manifests ensuring readiness for scalable Kubernetes environments.
- **Public Demo:** The live application is deployed as a lightweight web service on Render's Free Tier. To accommodate memory constraints (512MB RAM), the production build dynamically strips heavy embedding libraries (like PyTorch) and relies on HuggingFace's remote Inference API for vectorization.

## Tech Stack

- **Frameworks:** LangGraph, LangChain, Flask
- **LLM / Inference:** Groq (Llama 3), HuggingFace Inference API
- **Databases:** DataStax AstraDB (Vector), SQLite (Structured relational)
- **Monitoring:** Prometheus, Grafana (Local K8s configuration)
- **Deployment:** Docker, Minikube, Render
- **Package Management:** `uv`

## Setup Instructions

### Prerequisites
- Python 3.12+
- `uv` package manager
- API Keys: Groq, HuggingFace (with Inference permissions), and DataStax AstraDB (Token, Endpoint, Keyspace)

### 1. Local Installation

Clone the repository and install the dependencies:
```bash
git clone https://github.com/Saif-7122/Real-estate-concierge.git
cd real-estate-concierge

# Install base dependencies
uv sync

# If you intend to run local PDF ingestion, install the heavy ML dependencies:
uv pip install -e .[ingest]
```

### 2. Environment Variables
Create a `.env` file in the root directory based on `.env.example`:
```env
# LLM & Embeddings
GROQ_API_KEY=your_groq_key
HF_API_TOKEN=your_hf_token

# Astra DB
ASTRA_DB_APPLICATION_TOKEN=your_astra_token
ASTRA_DB_API_ENDPOINT=your_astra_endpoint
ASTRA_DB_KEYSPACE=your_keyspace
```

### 3. Ingesting Data (Optional)
If you need to populate your vector database with a new property brochure:
```bash
python backend/ingestion/ingest_brochure.py
```
*(Note: Requires the `[ingest]` dependencies installed.)*

### 4. Running the Server
Start the local development server:
```bash
python backend/app.py
```
The API and frontend will be available at `http://127.0.0.1:5000`.
