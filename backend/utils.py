import os
import glob
from typing import List, Dict, Optional

from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

# --- Configuration ---
# Using Sentence Transformers is generally recommended for open-source/local embeddings
# If you prefer OpenAI, uncomment the line below and ensure OPENAI_API_KEY is set
# embedding_function = OpenAIEmbeddings()
# For this example, let's stick with OpenAI as requested
# Remove module-level instantiation and check for OpenAI API Key here.
# It will be checked implicitly when OpenAIEmbeddings() is called within functions.

# Using Chroma as the vector store
vector_store_path = "./chroma_db"
collection_name = "ai_pdf_docs"

# --- Document Loading ---
LOADER_MAPPING = {
    ".pdf": (PyPDFLoader, {}),
    ".txt": (TextLoader, {"encoding": "utf8"}),
    ".doc": (Docx2txtLoader, {}),
    ".docx": (Docx2txtLoader, {}),
    # '.docs' is not a standard extension, assuming it might be a typo for .docx or similar
    # Add other loaders as needed, e.g., for CSV, JSON, HTML
}

def load_single_document(file_path: str) -> Optional[List[Document]]:
    """Loads a single document using the appropriate loader based on its extension."""
    ext = "." + file_path.rsplit(".", 1)[-1].lower()
    if ext in LOADER_MAPPING:
        loader_class, loader_args = LOADER_MAPPING[ext]
        try:
            loader = loader_class(file_path, **loader_args)
            return loader.load()
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    else:
        print(f"Unsupported file extension: {ext} for file {file_path}")
        return None

def load_documents_from_folder(folder_path: str) -> List[Document]:
    """Loads all supported documents from a specified folder."""
    if not os.path.isdir(folder_path):
        raise ValueError(f"Folder not found: {folder_path}")

    all_files = []
    for ext in LOADER_MAPPING:
        # Use glob to find files recursively
        all_files.extend(
            glob.glob(os.path.join(folder_path, f"**/*{ext}"), recursive=True)
        )

    # Filter out duplicates if any
    unique_files = list(set(all_files))
    print(f"Found {len(unique_files)} unique supported documents in {folder_path}")

    docs = []
    for file_path in unique_files:
        loaded_doc = load_single_document(file_path)
        if loaded_doc:
            # Add source metadata
            for doc in loaded_doc:
                doc.metadata["source"] = os.path.basename(file_path)
            docs.extend(loaded_doc)

    print(f"Successfully loaded {len(docs)} document sections.")
    return docs

# --- Text Splitting ---
def split_documents(docs: List[Document]) -> List[Document]:
    """Splits documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(docs)
    print(f"Split {len(docs)} documents into {len(split_docs)} chunks.")
    return split_docs

# --- Vector Store Operations ---
def create_vector_store(chunks: List[Document]) -> Chroma:
    """Creates a Chroma vector store from document chunks."""
    print(f"Creating vector store with {len(chunks)} chunks...")
    # Instantiate embedding function here, just before use
    # This ensures .env is loaded before the API key is needed.
    embedding_function = OpenAIEmbeddings()
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_function,
        collection_name=collection_name,
        persist_directory=vector_store_path # Ensure persistence
    )
    vector_store.persist()
    print(f"Vector store created and persisted at {vector_store_path}")
    return vector_store

def get_vector_store() -> Optional[Chroma]:
    """Loads an existing Chroma vector store."""
    if os.path.exists(vector_store_path) and os.listdir(vector_store_path): # Check if dir exists and is not empty
        print(f"Loading existing vector store from {vector_store_path}")
        try:
            # Instantiate embedding function here, just before use
            # This ensures .env is loaded before the API key is needed.
            embedding_function = OpenAIEmbeddings()
            vector_store = Chroma(
                persist_directory=vector_store_path,
                embedding_function=embedding_function,
                collection_name=collection_name
            )
            return vector_store
        except Exception as e:
            print(f"Error loading vector store: {e}")
            # Handle potential issues like index corruption or version mismatch
            # Optionally, you could try deleting the existing store and asking user to reprocess
            return None
    else:
        print("Vector store not found or is empty.")
        return None

# --- Main Processing Function ---
def process_documents_in_folder(folder_path: str) -> bool:
    """Loads, splits, and creates a vector store for documents in a folder."""
    try:
        docs = load_documents_from_folder(folder_path)
        if not docs:
            print("No documents were loaded. Processing stopped.")
            return False
        chunks = split_documents(docs)
        create_vector_store(chunks)
        return True
    except ValueError as ve:
        print(f"Value Error during processing: {ve}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")
        return False
