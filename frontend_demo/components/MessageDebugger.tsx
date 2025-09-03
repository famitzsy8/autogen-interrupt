import React, { useState, useEffect } from 'react';

interface RawMessage {
  timestamp: string;
  type: string;
  data: any;
  [key: string]: any;
}

interface MessageDebuggerProps {
  isVisible: boolean;
  onToggle: () => void;
}

const MessageDebugger: React.FC<MessageDebuggerProps> = ({ isVisible, onToggle }) => {
  const [messages, setMessages] = useState<RawMessage[]>([]);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    if (!isVisible) return;

    // Listen to WebSocket messages
    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);
        const debugMessage: RawMessage = {
          timestamp: new Date().toISOString(),
          ...message
        };
        
        setMessages(prev => [debugMessage, ...prev.slice(0, 49)]); // Keep last 50 messages
        console.log('🐛 Raw WebSocket Message:', debugMessage);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    // Try to access the WebSocket connection
    // This is a hack to intercept messages - in production you'd do this differently
    const originalWebSocket = window.WebSocket;
    let wsInstance: WebSocket | null = null;

    window.WebSocket = class extends WebSocket {
      constructor(url: string | URL, protocols?: string | string[]) {
        super(url, protocols);
        wsInstance = this;
        this.addEventListener('message', handleMessage);
      }
    };

    return () => {
      window.WebSocket = originalWebSocket;
      if (wsInstance) {
        wsInstance.removeEventListener('message', handleMessage);
      }
    };
  }, [isVisible]);

  const filteredMessages = messages.filter(msg => 
    !filter || 
    JSON.stringify(msg).toLowerCase().includes(filter.toLowerCase())
  );

  if (!isVisible) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          background: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          width: '60px',
          height: '60px',
          fontSize: '24px',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 1000
        }}
        title="Show Message Debugger"
      >
        🐛
      </button>
    );
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      width: '600px',
      height: '500px',
      background: 'rgba(0,0,0,0.95)',
      color: '#00ff00',
      fontFamily: 'monospace',
      fontSize: '12px',
      borderRadius: '8px',
      border: '2px solid #00ff00',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header */}
      <div style={{
        padding: '10px',
        borderBottom: '1px solid #00ff00',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(0,255,0,0.1)'
      }}>
        <span>🐛 WebSocket Message Debugger ({messages.length})</span>
        <button
          onClick={onToggle}
          style={{
            background: 'transparent',
            color: '#00ff00',
            border: '1px solid #00ff00',
            borderRadius: '4px',
            padding: '4px 8px',
            cursor: 'pointer'
          }}
        >
          ✕
        </button>
      </div>

      {/* Filter */}
      <div style={{ padding: '8px' }}>
        <input
          type="text"
          placeholder="Filter messages..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            width: '100%',
            background: 'rgba(0,0,0,0.8)',
            color: '#00ff00',
            border: '1px solid #00ff00',
            borderRadius: '4px',
            padding: '4px 8px',
            fontFamily: 'monospace'
          }}
        />
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '8px'
      }}>
        {filteredMessages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#666', padding: '20px' }}>
            No messages yet...
          </div>
        ) : (
          filteredMessages.map((msg, index) => (
            <div key={index} style={{
              marginBottom: '12px',
              padding: '8px',
              border: '1px solid #333',
              borderRadius: '4px',
              background: 'rgba(0,0,0,0.3)'
            }}>
              <div style={{ 
                color: '#ffff00', 
                fontWeight: 'bold',
                marginBottom: '4px',
                display: 'flex',
                justifyContent: 'space-between'
              }}>
                <span>{msg.type}</span>
                <span style={{ fontSize: '10px', color: '#888' }}>
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
              
              {msg.data?.agent && (
                <div style={{ color: '#ff6600', marginBottom: '4px' }}>
                  Agent: {msg.data.agent}
                </div>
              )}
              
              {msg.data?.simplified && (
                <div style={{ color: '#00ffff', marginBottom: '4px' }}>
                  Simplified: "{msg.data.simplified}"
                </div>
              )}
              
              {msg.data?.name && (
                <div style={{ color: '#ff00ff', marginBottom: '4px' }}>
                  Tool: {msg.data.name}
                </div>
              )}
              
              <details style={{ marginTop: '4px' }}>
                <summary style={{ cursor: 'pointer', color: '#ccc' }}>
                  Raw Data ({JSON.stringify(msg).length} chars)
                </summary>
                <pre style={{
                  marginTop: '4px',
                  fontSize: '10px',
                  color: '#aaa',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {JSON.stringify(msg, null, 2)}
                </pre>
              </details>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MessageDebugger;