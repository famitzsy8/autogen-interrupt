import React, { useState, useEffect } from 'react';
import { ToolCall, ToolResult } from '../lib/llm-processor';

interface ToolCallBoxProps {
  toolCall: ToolCall;
  result?: ToolResult;
  summary?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration?: string;
  dataPoints?: number;
}

const LoadingSpinner: React.FC = () => (
  <div style={{
    width: '16px',
    height: '16px',
    border: '2px solid #f3f3f3',
    borderTop: '2px solid #007bff',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  }}>
    <style jsx>{`
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      @keyframes resultPulse {
        0% { 
          transform: scale(1);
          box-shadow: 0 2px 8px rgba(40, 167, 69, 0.1);
        }
        50% { 
          transform: scale(1.05);
          box-shadow: 0 8px 32px rgba(40, 167, 69, 0.3), 0 0 0 3px rgba(40, 167, 69, 0.2);
        }
        100% { 
          transform: scale(1);
          box-shadow: 0 2px 8px rgba(40, 167, 69, 0.1);
        }
      }
    `}</style>
  </div>
);


const ToolCallBox: React.FC<ToolCallBoxProps> = ({
  toolCall,
  result,
  summary,
  status,
  duration,
  dataPoints
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showResultAnimation, setShowResultAnimation] = useState(false);
  const [zIndex, setZIndex] = useState(1);

  // Animate when results come in
  useEffect(() => {
    if (result && status === 'completed') {
      setShowResultAnimation(true);
      setZIndex(1000);
      
      // Reset z-index and animation after animation completes
      const timer = setTimeout(() => {
        setZIndex(1);
        setShowResultAnimation(false);
      }, 800);
      
      return () => clearTimeout(timer);
    }
  }, [result, status]);

  const getStatusColor = () => {
    switch (status) {
      case 'pending': return '#6c757d';
      case 'in_progress': return '#007bff';
      case 'completed': return '#28a745';
      case 'failed': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const getStatusIcon = () => {
    // If we have a result, always show completed state
    if (result) {
      return result.is_error ? '❌' : '✅';
    }
    
    // Otherwise show status-based icons
    switch (status) {
      case 'pending': return '⏳';
      case 'in_progress': return <LoadingSpinner />;
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return '📝';
    }
  };

  const getBackgroundColor = () => {
    // If we have a result, use result-based coloring
    if (result) {
      return result.is_error ? '#fff5f5' : '#f8fff8';
    }
    
    // Otherwise use status-based coloring
    switch (status) {
      case 'pending': return '#f8f9fa';
      case 'in_progress': return '#f8f9fa';
      case 'completed': return '#f8fff8';
      case 'failed': return '#fff5f5';
      default: return '#f8f9fa';
    }
  };

  const getBorderColor = () => {
    // If we have a result, use result-based coloring
    if (result) {
      return result.is_error ? '#dc3545' : '#28a745';
    }
    
    // Otherwise use status-based coloring
    switch (status) {
      case 'pending': return '#dee2e6';
      case 'in_progress': return '#007bff';
      case 'completed': return '#28a745';
      case 'failed': return '#dc3545';
      default: return '#dee2e6';
    }
  };

  // Calculate progress for loading state
  const getProgress = () => {
    if (status === 'completed') return 100;
    if (status === 'in_progress') return 60; // Simulate progress
    return 0;
  };

  return (
    <div style={{
      marginLeft: '2rem',
      marginTop: '0.5rem',
      marginBottom: '0.5rem',
      fontSize: '0.9rem'
    }}>
      {/* Connecting line */}
      <div style={{
        position: 'absolute',
        left: '2.5rem',
        marginTop: '0.5rem',
        width: '1.5rem',
        height: '1px',
        backgroundColor: '#dee2e6'
      }} />
      
      {/* Tool call box */}
      <div style={{
        backgroundColor: getBackgroundColor(),
        border: `1px solid ${getBorderColor()}`,
        borderRadius: '6px',
        padding: '0.75rem',
        marginLeft: '1.5rem',
        position: 'relative',
        zIndex: zIndex,
        transition: 'all 0.3s ease',
        animation: showResultAnimation ? 'resultPulse 0.8s ease-out' : 'none',
        boxShadow: status === 'completed' 
          ? '0 2px 8px rgba(40, 167, 69, 0.1)' 
          : '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: status === 'in_progress' ? '0.5rem' : '0'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              width: '20px',
              height: '20px'
            }}>
              {getStatusIcon()}
            </div>
            <span style={{
              fontWeight: '500',
              color: getStatusColor(),
              fontSize: '0.85rem'
            }}>
              🔧 {toolCall.name}
            </span>
            {status === 'completed' && dataPoints !== undefined && (
              <span style={{
                fontSize: '0.75rem',
                color: '#6c757d',
                backgroundColor: '#e9ecef',
                padding: '2px 6px',
                borderRadius: '10px'
              }}>
                {dataPoints} items
              </span>
            )}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {status === 'completed' && duration && (
              <span style={{
                fontSize: '0.75rem',
                color: '#6c757d'
              }}>
                {duration}
              </span>
            )}
            {(summary || result) && status === 'completed' && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                style={{
                  background: 'none',
                  border: `1px solid ${getStatusColor()}`,
                  color: getStatusColor(),
                  borderRadius: '3px',
                  padding: '2px 6px',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px'
                }}
              >
                {isExpanded ? '▼ Less' : '▶ More'}
              </button>
            )}
          </div>
        </div>


        {/* Summary and quick result preview for completed state */}
        {(result || (status === 'completed' && summary)) && (
          <div style={{ marginTop: '0.5rem' }}>
            {summary && (
              <div style={{
                fontSize: '0.8rem',
                color: '#495057',
                fontStyle: 'italic',
                marginBottom: result ? '0.5rem' : '0'
              }}>
                {summary}
              </div>
            )}
            
            {result && !isExpanded && (
              <div style={{
                padding: '0.5rem',
                backgroundColor: result.is_error ? '#fff5f5' : '#f0f9ff',
                borderRadius: '4px',
                border: `1px solid ${result.is_error ? '#fecaca' : '#bfdbfe'}`,
                fontSize: '0.75rem'
              }}>
                <div style={{
                  fontWeight: '500',
                  color: result.is_error ? '#dc2626' : '#1d4ed8',
                  marginBottom: '0.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}>
                  {result.is_error ? '❌' : '✅'} Result Preview
                </div>
                <div style={{
                  color: result.is_error ? '#991b1b' : '#1e40af',
                  maxHeight: '60px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {typeof result.content === 'string' 
                    ? result.content.length > 100 
                      ? result.content.substring(0, 100) + '...'
                      : result.content
                    : JSON.stringify(result.content).substring(0, 100) + '...'
                  }
                </div>
              </div>
            )}
          </div>
        )}

        {/* Expanded details */}
        {isExpanded && (result || status === 'completed') && (
          <div style={{ marginTop: '0.75rem' }}>
            {summary && (
              <div style={{
                padding: '0.5rem',
                backgroundColor: '#e8f5e8',
                borderRadius: '4px',
                marginBottom: '0.5rem'
              }}>
                <div style={{ fontWeight: '500', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                  Summary:
                </div>
                <div style={{ fontSize: '0.8rem', color: '#155724' }}>
                  {summary}
                </div>
              </div>
            )}

            {toolCall.arguments && (
              <div style={{
                padding: '0.5rem',
                backgroundColor: '#f1f3f4',
                borderRadius: '4px',
                marginBottom: '0.5rem'
              }}>
                <div style={{ fontWeight: '500', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                  Arguments:
                </div>
                <pre style={{
                  fontSize: '0.75rem',
                  margin: 0,
                  color: '#495057',
                  overflow: 'auto',
                  maxHeight: '100px'
                }}>
                  {JSON.stringify(toolCall.arguments, null, 2)}
                </pre>
              </div>
            )}

            {result && (
              <div style={{
                padding: '0.5rem',
                backgroundColor: result.is_error ? '#f8d7da' : '#d1edff',
                borderRadius: '4px'
              }}>
                <div style={{ 
                  fontWeight: '500', 
                  fontSize: '0.8rem', 
                  marginBottom: '0.25rem',
                  color: result.is_error ? '#721c24' : '#0c5460'
                }}>
                  Result:
                </div>
                <div style={{
                  fontSize: '0.75rem',
                  color: result.is_error ? '#721c24' : '#0c5460',
                  maxHeight: '150px',
                  overflow: 'auto'
                }}>
                  {typeof result.content === 'string' 
                    ? result.content.length > 200 
                      ? result.content.substring(0, 200) + '...'
                      : result.content
                    : JSON.stringify(result.content, null, 2)
                  }
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ToolCallBox;