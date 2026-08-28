import os

root = r'd:\Realestate coincerge\real-estate-concierge'
pyproject_path = os.path.join(root, 'pyproject.toml')
vector_store_path = os.path.join(root, 'backend', 'retrieval', 'vector_store.py')

# 1. Update pyproject.toml
content = open(pyproject_path, encoding='utf-8').read()
old_deps = '"python-dotenv>=1.2.3",\n    "sentence-transformers>=6.0.0",\n]'
new_deps = '"python-dotenv>=1.2.3",\n]\n\n[project.optional-dependencies]\ningest = [\n    "sentence-transformers>=6.0.0",\n]'
if 'sentence-transformers' in content and '[project.optional-dependencies]' not in content:
    updated = content.replace(old_deps, new_deps)
    open(pyproject_path, 'w', encoding='utf-8').write(updated)
    print('Updated pyproject.toml')

# 2. Update vector_store.py
content = open(vector_store_path, encoding='utf-8').read()
old_import = 'from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpointEmbeddings'
new_import = 'from langchain_huggingface import HuggingFaceEndpointEmbeddings'

old_local = 'return HuggingFaceEmbeddings(model_name=model_name)'
new_local = 'from langchain_huggingface import HuggingFaceEmbeddings\n    return HuggingFaceEmbeddings(model_name=model_name)'

if old_import in content:
    updated = content.replace(old_import, new_import)
    updated = updated.replace(old_local, new_local)
    open(vector_store_path, 'w', encoding='utf-8').write(updated)
    print('Updated vector_store.py')
