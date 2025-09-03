import React, { useState } from 'react';
import { AgentCommunication, ToolCall, ToolResult } from '../lib/llm-processor';
import ToolCallBox from './ToolCallBox';

interface ExpandableStepProps {
  communication: AgentCommunication;
  agentColor: string;
  typeIcon: string;
  isLast: boolean;
  toolCallSummaries?: any[];
  toolCallResults?: any[];
}

const ExpandableStep: React.FC<ExpandableStepProps> = ({ 
  communication, 
  agentColor, 
  typeIcon, 
  isLast,
  toolCallSummaries = [],
  toolCallResults = []
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const formatTime = (timestamp: string): string => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'pending': return '⏳';
      case 'in_progress': return '🔄';
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return '📝';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending': return '#ffc107';
      case 'in_progress': return '#17a2b8';
      case 'completed': return '#28a745';
      case 'failed': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const renderToolCalls = (toolCalls: ToolCall[]) => {
    return (
      <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
        <h5 style={{ margin: '0 0 0.5rem 0', color: '#495057' }}>Tool Calls:</h5>
        {toolCalls.map((call, index) => (
          <div key={call.id} style={{ 
            marginBottom: '0.5rem', 
            padding: '0.5rem',
            backgroundColor: 'white',
            borderRadius: '4px',
            border: '1px solid #dee2e6'
          }}>
            <div style={{ fontWeight: 'bold', color: '#495057' }}>
              🔧 {call.name}
            </div>
            <div style={{ fontSize: '0.9rem', color: '#6c757d', marginTop: '0.25rem' }}>
              <strong>Arguments:</strong>
              <pre style={{ 
                fontSize: '0.8rem', 
                margin: '0.25rem 0 0 0',
                padding: '0.5rem',
                backgroundColor: '#f1f3f4',
                borderRadius: '4px',
                overflow: 'auto'
              }}>
                {JSON.stringify(call.arguments, null, 2)}
              </pre>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderResults = (results: ToolResult[]) => {
    return (
      <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#e8f5e8', borderRadius: '4px' }}>
        <h5 style={{ margin: '0 0 0.5rem 0', color: '#155724' }}>Results:</h5>
        {results.map((result, index) => (
          <div key={result.call_id} style={{ 
            marginBottom: '0.5rem',
            padding: '0.5rem',
            backgroundColor: 'white',
            borderRadius: '4px',
            border: result.is_error ? '1px solid #dc3545' : '1px solid #28a745'
          }}>
            <div style={{ 
              fontWeight: 'bold', 
              color: result.is_error ? '#dc3545' : '#28a745',
              marginBottom: '0.25rem'
            }}>
              {result.is_error ? '❌ Error' : '✅ Success'}
            </div>
            <div style={{ fontSize: '0.9rem', color: '#495057' }}>
              <strong>Content:</strong>
              <div style={{ 
                fontSize: '0.8rem', 
                margin: '0.25rem 0 0 0',
                padding: '0.5rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
                maxHeight: '200px',
                overflow: 'auto'
              }}>
                {typeof result.content === 'string' ? result.content : JSON.stringify(result.content, null, 2)}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ 
      display: 'flex', 
      marginBottom: isLast ? 0 : '1rem',
      position: 'relative'
    }}>
      {/* Timeline line */}
      {!isLast && (
        <div
          style={{
            position: 'absolute',
            left: '1.5rem',
            top: '3rem',
            bottom: '-1rem',
            width: '2px',
            backgroundColor: '#e9ecef'
          }}
        />
      )}
      
      {/* Agent indicator */}
      <div
        style={{
          width: '3rem',
          height: '3rem',
          borderRadius: '50%',
          backgroundColor: agentColor,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: '0.8rem',
          fontWeight: 'bold',
          flexShrink: 0,
          marginRight: '1rem',
          zIndex: 1,
          position: 'relative'
        }}
      >
        {communication.agent.charAt(0).toUpperCase()}
      </div>

      {/* Communication content */}
      <div
        style={{
          flex: 1,
          backgroundColor: 'white',
          padding: '1rem',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          border: `2px solid ${agentColor}20`
        }}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.2rem' }}>{typeIcon}</span>
            <span style={{ 
              fontWeight: 'bold', 
              color: agentColor,
              textTransform: 'capitalize'
            }}>
              {communication.agent.replace('_', ' ')}
            </span>
            <span style={{ 
              fontSize: '0.8rem',
              padding: '0.2rem 0.5rem',
              backgroundColor: agentColor + '20',
              color: agentColor,
              borderRadius: '12px',
              textTransform: 'capitalize'
            }}>
              {communication.type.replace('_', ' ')}
            </span>
            <span style={{
              fontSize: '1rem',
              color: getStatusColor(communication.status)
            }}>
              {getStatusIcon(communication.status)}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ 
              fontSize: '0.8rem', 
              color: '#6c757d' 
            }}>
              {formatTime(communication.timestamp)}
            </span>
            {(communication.fullContent || communication.toolCalls) && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                style={{
                  background: 'none',
                  border: `1px solid ${agentColor}`,
                  color: agentColor,
                  borderRadius: '4px',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                {isExpanded ? '▼' : '▶'} Details
              </button>
            )}
          </div>
        </div>
        
        <p style={{ 
          margin: 0,
          color: '#333',
          lineHeight: '1.5'
        }}>
          {communication.simplified}
        </p>

        {/* Tool calls as nested items */}
        {communication.toolCalls && communication.toolCalls.map((toolCall, index) => {
          const toolSummary = toolCallSummaries.find(s => 
            s.toolCallId.includes(toolCall.name)
          );
          const toolResult = communication.results?.find(r => 
            r.call_id === toolCall.id
          );
          
          return (
            <ToolCallBox
              key={toolCall.id}
              toolCall={toolCall}
              result={toolResult}
              summary={toolSummary?.summary}
              status={communication.status}
              duration={toolSummary?.duration}
              dataPoints={toolSummary?.dataPoints}
            />
          );
        })}

        {/* Expandable content */}
        {isExpanded && (
          <div style={{ marginTop: '1rem' }}>
            {communication.fullContent && (
              <div style={{ 
                padding: '1rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
                marginBottom: '1rem'
              }}>
                <h5 style={{ margin: '0 0 0.5rem 0', color: '#495057' }}>Full Details:</h5>
                <div style={{ 
                  fontSize: '0.9rem',
                  color: '#495057',
                  whiteSpace: 'pre-wrap',
                  lineHeight: '1.4'
                }}>
                  {communication.fullContent}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ExpandableStep;