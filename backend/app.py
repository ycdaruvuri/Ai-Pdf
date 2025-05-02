import os 

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

# Import functions from utils
from utils import process_documents_in_folder, get_vector_store

# Langchain imports for QA
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
load_dotenv() # Load environment variables from .env file in the current working directory or parents

# --- FastAPI App Initialization ---
app = FastAPI(
    title="AiPdf Backend API",
    description="API for processing documents and answering queries using Langchain and OpenAI.",
    version="1.0.0"
)

# # --- CORS Middleware ---
# # Allow requests from your React frontend (adjust origins as needed)
# origins = [
#     "http://localhost:3000",  # Default React dev server port
#     "http://127.0.0.1:3000",
#     # Add other origins if your frontend is hosted elsewhere
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
#     allow_headers=["*"],  # Allows all headers
# )

# --- Pydantic Models for Request Bodies ---
class ProcessRequest(BaseModel):
    folder_path: str

class QueryRequest(BaseModel):
    query: str

# --- Global Variables ---
# Cache the QA chain and vector store to avoid reloading on every query
qa_chain = None
vector_store = None

def initialize_qa_chain():
    """Initializes the QA chain by loading the vector store."""
    global vector_store, qa_chain
    print("Attempting to load vector store...")
    vector_store = get_vector_store()
    if vector_store:
        print("Vector store loaded successfully. Initializing QA chain...")
        # Use a standard, robust LLM
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

        # Define a prompt template
        prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Provide a concise answer.

        Context: {context}

        Question: {question}
        Answer:"""
        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        # Create the RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # "stuff" packs context into one prompt
            retriever=vector_store.as_retriever(search_kwargs={"k": 3}), # Retrieve top 3 relevant chunks
            return_source_documents=True, # Optionally return source chunks
            chain_type_kwargs={"prompt": PROMPT}
        )
        print("QA chain initialized.")
    else:
        print("Failed to load vector store. QA chain not initialized.")
        qa_chain = None

# Initialize the QA chain on startup
# This might take a moment if the vector store is large
# Consider moving this to a background task or lazy loading if startup time is critical
initialize_qa_chain()


# --- API Endpoints ---

@app.post("/process-documents", status_code=200)
async def process_docs_endpoint(request: ProcessRequest = Body(...)):
    """
    Processes documents in the specified folder, creates embeddings, and stores them.
    """
    global qa_chain # Allow modification of the global chain
    print(f"Received request to process documents in: {request.folder_path}")
    if not os.path.isdir(request.folder_path):
         print(f"Error: Folder not found at {request.folder_path}")
         raise HTTPException(status_code=400, detail=f"Folder not found: {request.folder_path}")

    success = process_documents_in_folder(request.folder_path)

    if success:
        print("Document processing successful. Re-initializing QA chain...")
        # Re-initialize the chain with the new/updated vector store
        initialize_qa_chain()
        if qa_chain:
            return {"message": "Documents processed successfully and QA chain initialized."}
        else:
            # This might happen if the folder was valid but contained no processable files
             print("Warning: Documents processed, but QA chain initialization failed (likely no vector store created).")
             raise HTTPException(status_code=500, detail="Documents processed, but failed to initialize QA chain (Vector store might be empty).")
    else:
        print("Error during document processing.")
        raise HTTPException(status_code=500, detail="Failed to process documents.")


@app.post("/query", status_code=200)
async def query_endpoint(request: QueryRequest = Body(...)):
    """
    Answers a query based on the processed documents using the QA chain.
    """
    global qa_chain
    print(f"Received query: {request.query}")

    if qa_chain is None:
        print("Error: QA chain is not initialized. Have documents been processed?")
        raise HTTPException(status_code=400, detail="QA chain not initialized. Please process documents first via the /process-documents endpoint.")

    try:
        print("Invoking QA chain...")
        # Invoke the chain - Langchain v0.1+ uses invoke
        result = qa_chain.invoke({"query": request.query})
        answer = result.get("result", "No answer found.")
        source_documents = result.get("source_documents", [])

        sources = []
        if source_documents:
            sources = list(set([doc.metadata.get("source", "Unknown source") for doc in source_documents])) # Get unique source filenames

        print(f"Query answered successfully. Answer: {answer[:100]}... Sources: {sources}")
        return {"answer": answer, "sources": sources}

    except Exception as e:
        print(f"Error during query processing: {e}")
        # Log the full error for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during query processing: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint providing basic API info."""
    return {"message": "Welcome to the AiPdf Backend API. Use /docs for API documentation."}

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    print("Starting backend server...")
    # Make sure OPENAI_API_KEY is set before starting
    if os.getenv("OPENAI_API_KEY") is None:
        print("\n--- WARNING ---")
        print("OPENAI_API_KEY environment variable not set.")
        print("Please create a .env file in the 'backend' directory with your key:")
        print("OPENAI_API_KEY='your-api-key-here'")
        print("---------------\n")
        # Optionally exit if key is mandatory for basic operation
        # exit(1)

    # Run the FastAPI app using uvicorn
    # host="0.0.0.0" makes it accessible on the network
    # reload=True automatically restarts the server on code changes (useful for development)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
