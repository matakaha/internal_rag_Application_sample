import { useState, useRef, useEffect } from 'react'
import './App.css'

// Get API endpoint from dynamically loaded config
const API_ENDPOINT = window.APP_CONFIG?.apiEndpoint || 'http://localhost:7071';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    // Add empty assistant message for streaming
    const assistantMessageIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch(`${API_ENDPOINT}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              break;
            }

            try {
              const parsed = JSON.parse(data);
              
              if (parsed.error) {
                throw new Error(parsed.error);
              }

              if (parsed.content) {
                assistantContent += parsed.content;
                
                // Update assistant message
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[assistantMessageIndex] = {
                    role: 'assistant',
                    content: assistantContent
                  };
                  return newMessages;
                });
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError);
            }
          }
        }
      }

    } catch (err) {
      console.error('Chat error:', err);
      setError(err.message || 'メッセージの送信中にエラーが発生しました');
      
      // Remove empty assistant message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🦜 レッドリスト検索チャット</h1>
        <p>環境省のレッドリスト（絶滅危惧種）について質問してください</p>
      </header>

      <div className="chat-container">
        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>ようこそ！</h2>
              <p>このチャットでは、環境省が公開している第4次レッドリストのデータに基づいて、絶滅危惧種に関する質問にお答えします。</p>
              <div className="example-questions">
                <h3>質問例：</h3>
                <ul>
                  <li>イリオモテヤマネコについて教えてください</li>
                  <li>絶滅危惧IA類（CR）に指定されている哺乳類を教えてください</li>
                  <li>ライチョウの生息地はどこですか？</li>
                  <li>汽水・淡水魚類で絶滅危惧種に指定されている種を教えてください</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="message-role">
                {msg.role === 'user' ? '👤 あなた' : '🤖 アシスタント'}
              </div>
              <div className="message-content">
                {msg.content || (isLoading && index === messages.length - 1 ? '考え中...' : '')}
              </div>
            </div>
          ))}

          {error && (
            <div className="error-message">
              <strong>エラー:</strong> {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="質問を入力してください..."
            disabled={isLoading}
            className="message-input"
          />
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()}
            className="send-button"
          >
            {isLoading ? '送信中...' : '送信'}
          </button>
        </form>
      </div>

      <footer className="footer">
        <p>データ提供: <a href="https://data.e-gov.go.jp/data/dataset/env_20140904_0456" target="_blank" rel="noopener noreferrer">e-Govデータポータル - 環境省レッドリスト</a></p>
      </footer>
    </div>
  )
}

export default App
