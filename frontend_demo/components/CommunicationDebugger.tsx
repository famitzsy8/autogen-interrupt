import React, { useState, useEffect, useRef } from 'react';
import { AgentCommunication } from '../lib/llm-processor';

interface DebugEvent {
  timestamp: string;
  type: 'websocket_received' | 'realtime_processed' | 'dashboard_received' | 'timeline_rendered' | 'box_displayed';
  data: any;
  communicationId?: string;
  agentName?: string;
  messageType?: string;
  details?: string;
}

interface CommunicationDebuggerProps {
  isVisible: boolean;
  onToggle: () => void;
  communications: AgentCommunication[];
}

const CommunicationDebugger: React.FC<CommunicationDebuggerProps> = ({ 
  isVisible, 
  onToggle, 
  communications 
}) => {
  const [debugEvents, setDebugEvents] = useState<DebugEvent[]>([]);
  const [boxStates, setBoxStates] = useState<{ [id: string]: any }>({});
  const debugRef = useRef<HTMLDivElement>(null);

  // Monitor communications array changes
  useEffect(() => {
    communications.forEach(comm => {
      const existingEvent = debugEvents.find(
        event => event.communicationId === comm.id && event.type === 'dashboard_received'
      );
      
      if (!existingEvent) {
        const debugEvent: DebugEvent = {
          timestamp: new Date().toISOString(),
          type: 'dashboard_received',
          data: comm,
          communicationId: comm.id,
          agentName: comm.agent,
          messageType: comm.type,
          details: `Agent: ${comm.agent}, Type: ${comm.type}, Status: ${comm.status}`
        };
        
        setDebugEvents(prev => [...prev, debugEvent].slice(-100)); // Keep last 100 events
        
        // Track box state
        setBoxStates(prev => ({
          ...prev,
          [comm.id]: {
            agent: comm.agent,
            type: comm.type,
            status: comm.status,
            simplified: comm.simplified,
            receivedAt: new Date().toISOString(),
            shouldDisplay: true
          }
        }));
      }
    });
  }, [communications, debugEvents]);

  // Add event logging method
  const addDebugEvent = (type: DebugEvent['type'], data: any, details?: string) => {
    const debugEvent: DebugEvent = {
      timestamp: new Date().toISOString(),
      type,
      data,
      details
    };
    setDebugEvents(prev => [...prev, debugEvent].slice(-100));
  };

  // Expose addDebugEvent to global scope for other components to use
  useEffect(() => {
    (window as any).addCommunicationDebugEvent = addDebugEvent;
    return () => {
      delete (window as any).addCommunicationDebugEvent;
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (debugRef.current) {
      debugRef.current.scrollTop = debugRef.current.scrollHeight;
    }
  }, [debugEvents]);

  if (!isVisible) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: 'fixed',
          bottom: '1rem',
          left: '1rem',
          padding: '0.75rem',
          background: 'linear-gradient(135deg, #667eea, #764ba2)',
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          cursor: 'pointer',
          fontSize: '1.2rem',
          boxShadow: '0 4px 16px rgba(102, 126, 234, 0.4)',
          zIndex: 1001,
          transition: 'all 0.3s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        🐛
      </button>
    );
  }

  const getEventColor = (type: DebugEvent['type']) => {
    const colors = {
      'websocket_received': '#28a745',
      'realtime_processed': '#007bff', 
      'dashboard_received': '#ffc107',
      'timeline_rendered': '#fd7e14',
      'box_displayed': '#dc3545'
    };
    return colors[type] || '#6c757d';
  };

  const getEventIcon = (type: DebugEvent['type']) => {
    const icons = {
      'websocket_received': '📡',
      'realtime_processed': '⚙️',
      'dashboard_received': '📥',
      'timeline_rendered': '🎨',
      'box_displayed': '📦'
    };
    return icons[type] || '📝';
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: '1rem',
      left: '1rem',
      width: '500px',
      height: '600px',
      background: 'rgba(0, 0, 0, 0.95)',
      color: 'white',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      backdropFilter: 'blur(10px)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '1rem',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600' }}>
          🐛 Communication Debug Console
        </h3>
        <button
          onClick={onToggle}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            fontSize: '1.2rem',
            padding: '0.25rem'
          }}
        >
          ✕
        </button>
      </div>

      {/* Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '0.5rem',
        padding: '1rem',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#28a745' }}>
            {communications.length}
          </div>
          <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>Communications</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#007bff' }}>
            {debugEvents.length}
          </div>
          <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>Debug Events</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ffc107' }}>
            {Object.keys(boxStates).length}
          </div>
          <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>Tracked Boxes</div>
        </div>
      </div>

      {/* Box States */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
        maxHeight: '200px',
        overflowY: 'auto'
      }}>
        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#ffc107' }}>
          Current Box States:
        </h4>
        {Object.entries(boxStates).map(([id, state]) => (
          <div key={id} style={{
            fontSize: '0.75rem',
            padding: '0.25rem 0.5rem',
            margin: '0.25rem 0',
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            borderLeft: `3px solid ${getEventColor('dashboard_received')}`
          }}>
            <div style={{ fontWeight: 'bold' }}>{state.agent}</div>
            <div style={{ opacity: 0.8 }}>{state.simplified}</div>
            <div style={{ opacity: 0.6, fontSize: '0.7rem' }}>
              Status: {state.status} | {new Date(state.receivedAt).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>

      {/* Debug Events */}
      <div style={{ flex: 1, padding: '1rem', overflowY: 'auto' }} ref={debugRef}>
        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#28a745' }}>
          Debug Events:
        </h4>
        {debugEvents.map((event, index) => (
          <div key={index} style={{
            fontSize: '0.75rem',
            padding: '0.5rem',
            margin: '0.25rem 0',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '4px',
            borderLeft: `3px solid ${getEventColor(event.type)}`
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.25rem'
            }}>
              <span style={{ fontWeight: 'bold', color: getEventColor(event.type) }}>
                {getEventIcon(event.type)} {event.type}
              </span>
              <span style={{ opacity: 0.6, fontSize: '0.7rem' }}>
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            </div>
            {event.details && (
              <div style={{ opacity: 0.8, marginBottom: '0.25rem' }}>
                {event.details}
              </div>
            )}
            {event.communicationId && (
              <div style={{ opacity: 0.6, fontSize: '0.7rem' }}>
                ID: {event.communicationId}
              </div>
            )}
            {event.data && typeof event.data === 'object' && (
              <details style={{ marginTop: '0.25rem' }}>
                <summary style={{ cursor: 'pointer', opacity: 0.7 }}>Data</summary>
                <pre style={{ 
                  fontSize: '0.65rem', 
                  margin: '0.25rem 0', 
                  padding: '0.25rem',
                  background: 'rgba(0, 0, 0, 0.3)',
                  borderRadius: '2px',
                  maxHeight: '100px',
                  overflow: 'auto'
                }}>
                  {JSON.stringify(event.data, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
        {debugEvents.length === 0 && (
          <div style={{ opacity: 0.5, textAlign: 'center', padding: '2rem' }}>
            No debug events yet...
          </div>
        )}
      </div>

      {/* Clear button */}
      <div style={{
        padding: '1rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.2)',
        textAlign: 'center'
      }}>
        <button
          onClick={() => {
            setDebugEvents([]);
            setBoxStates({});
          }}
          style={{
            background: 'rgba(220, 53, 69, 0.2)',
            border: '1px solid #dc3545',
            color: '#dc3545',
            padding: '0.5rem 1rem',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.8rem'
          }}
        >
          Clear Debug Data
        </button>
      </div>
    </div>
  );
};

export default CommunicationDebugger;