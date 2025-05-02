import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // We'll add some basic styling

function App() {
  const [folderPath, setFolderPath] = useState('');
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [isProcessed, setIsProcessed] = useState(false); // Track if docs are processed

  // Backend API endpoint
  const backendUrl = ''; // Ensure this matches your backend host/port

  const handleProcess = async () => {
    if (!folderPath) {
      setStatusMessage('Please enter a folder path.');
      return;
    }
    setIsLoading(true);
    setStatusMessage('Processing documents... This may take a while.');
    setAnswer('');
    setSources([]);
    setIsProcessed(false);

    try {
      // Send POST request to the backend endpoint
      // Use relative path - the proxy in package.json will handle forwarding
      const response = await axios.post('/process-documents', {
        folder_path: folderPath
      });
      setStatusMessage(response.data.message || 'Documents processed successfully!');
      setIsProcessed(true); // Enable querying
    } catch (error) {
      console.error("Error processing documents:", error);
      const detail = error.response?.data?.detail || 'Failed to process documents.';
      setStatusMessage(`Error: ${detail}`);
      setIsProcessed(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!query) {
      setStatusMessage('Please enter a query.');
      return;
    }
     if (!isProcessed) {
      setStatusMessage('Please process documents before asking a query.');
      return;
    }
    setIsLoading(true);
    setStatusMessage('Getting answer...');
    setAnswer('');
    setSources([]);

    try {
      // Send POST request to the backend query endpoint
      // Use relative path - the proxy in package.json will handle forwarding
      const response = await axios.post('/query', { query: query });
      setAnswer(response.data.answer || 'No answer found.');
      setSources(response.data.sources || []);
      setStatusMessage('Query successful.');
    } catch (error) {
      console.error("Error querying:", error);
       const detail = error.response?.data?.detail || 'Failed to get answer.';
      setStatusMessage(`Error: ${detail}`);
      setAnswer('');
      setSources([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AiPdf - Chat with your Documents</h1>
      </header>
      <main className="App-main">
        <section className="section">
          <h2>1. Process Documents</h2>
          <div className="input-group">
            <label htmlFor="folderPath">Folder Path:</label>
            <input
              type="text"
              id="folderPath"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="e.g., C:\\Users\\YourUser\\Documents\\PDFs"
              disabled={isLoading}
            />
          </div>
          <button onClick={handleProcess} disabled={isLoading}>
            {isLoading && statusMessage.startsWith('Processing') ? 'Processing...' : 'Process Documents'}
          </button>
        </section>

        <section className="section">
          <h2>2. Ask a Question</h2>
           <p className="info">
             {isProcessed
               ? 'Document processing complete. You can now ask questions.'
               : 'Please process documents first.'}
           </p>
          <div className="input-group">
            <label htmlFor="query">Your Question:</label>
            <textarea
              id="query"
              rows="3"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask something about the documents..."
              disabled={isLoading || !isProcessed} // Disable if loading or not processed
            />
          </div>
          <button onClick={handleQuery} disabled={isLoading || !isProcessed}>
             {isLoading && statusMessage.startsWith('Getting') ? 'Answering...' : 'Ask Query'}
          </button>
        </section>

         {statusMessage && (
          <section className="section status-message">
            <p>{statusMessage}</p>
          </section>
        )}

        {(answer || sources.length > 0) && (
          <section className="section results">
            <h2>Answer</h2>
            <div className="answer-box">
              <p>{answer || "No answer provided."}</p>
            </div>
            {sources.length > 0 && (
              <div className="sources-box">
                <h3>Sources:</h3>
                <ul>
                  {sources.map((source, index) => (
                    <li key={index}>{source}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
