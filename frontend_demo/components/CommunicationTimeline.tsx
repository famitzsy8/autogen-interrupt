import React from 'react';
import { AgentCommunication } from '../lib/llm-processor';
import ExpandableStep from './ExpandableStep';
import FinalResultsTable from './FinalResultsTable';
import toolSummaries from '../data/tool-summaries.json';

interface CommunicationTimelineProps {
  communications: AgentCommunication[];
  isRunning: boolean;
}

const getAgentColor = (agent: string): string => {
  const colors: { [key: string]: string } = {
    'orchestrator': '#6f42c1',
    'committee_specialist': '#007bff',
    'bill_specialist': '#28a745',
    'actions_specialist': '#ffc107',
    'amendment_specialist': '#fd7e14',
    'congress_member_specialist': '#dc3545'
  };
  return colors[agent] || '#6c757d';
};

const getTypeIcon = (type: string): string => {
  const icons: { [key: string]: string } = {
    'message': '💬',
    'tool_call': '🔧',
    'reflection': '🤔',
    'handoff': '🔄'
  };
  return icons[type] || '📝';
};

const formatTime = (timestamp: string): string => {
  return new Date(timestamp).toLocaleTimeString();
};


const CommunicationTimeline: React.FC<CommunicationTimelineProps> = ({ 
  communications, 
  isRunning 
}) => {
  if (communications.length === 0 && !isRunning) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '4rem',
        color: '#6c757d',
        background: 'rgba(255,255,255,0.95)',
        borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
        border: '1px solid rgba(255,255,255,0.5)'
      }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
        <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
          Ready to Investigate
        </h3>
        <p style={{ fontSize: '1.1rem', opacity: 0.8 }}>
          Click "Run Investigation" to begin the multi-agent analysis
        </p>
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,0.98)',
      padding: '2rem',
      borderRadius: '16px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
      border: '1px solid rgba(255,255,255,0.5)',
      backdropFilter: 'blur(10px)'
    }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '2rem',
        padding: '0 0.5rem'
      }}>
        <h3 style={{ 
          margin: 0, 
          color: '#1a1a1a',
          fontSize: '1.5rem',
          fontWeight: '700'
        }}>
          🤖 Agent Communications
        </h3>
        {isRunning && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.75rem',
            color: '#10b981',
            fontSize: '1rem',
            fontWeight: '500',
            padding: '0.5rem 1rem',
            background: 'rgba(16, 185, 129, 0.1)',
            borderRadius: '20px',
            border: '1px solid rgba(16, 185, 129, 0.2)'
          }}>
            <div style={{
              width: '10px',
              height: '10px',
              backgroundColor: '#10b981',
              borderRadius: '50%',
              animation: 'pulse 1.5s infinite'
            }} />
            Investigation in progress...
          </div>
        )}
      </div>

      <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
        {communications.map((comm, index) => {
          // Check if this is the final table communication
          if (comm.id.includes('final_table')) {
            try {
              const tableData = JSON.parse(comm.fullContent || '{}');
              return (
                <div key={comm.id} style={{ marginTop: '2rem' }}>
                  <FinalResultsTable investigationData={tableData} />
                </div>
              );
            } catch (e) {
              // Fallback to regular display if JSON parsing fails
              return (
                <ExpandableStep
                  key={comm.id}
                  communication={comm}
                  agentColor={getAgentColor(comm.agent)}
                  typeIcon={getTypeIcon(comm.type)}
                  isLast={index === communications.length - 1}
                  toolCallSummaries={toolSummaries}
                />
              );
            }
          }

          return (
            <ExpandableStep
              key={comm.id}
              communication={comm}
              agentColor={getAgentColor(comm.agent)}
              typeIcon={getTypeIcon(comm.type)}
              isLast={index === communications.length - 1}
              toolCallSummaries={toolSummaries}
            />
          );
        })}
        
        {isRunning && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            padding: '1rem',
            backgroundColor: 'white',
            borderRadius: '8px',
            border: '2px dashed #28a745',
            marginTop: communications.length > 0 ? '1rem' : 0
          }}>
            <div style={{
              width: '3rem',
              height: '3rem',
              borderRadius: '50%',
              backgroundColor: '#28a745',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              animation: 'pulse 1.5s infinite'
            }}>
              ⏳
            </div>
            <span style={{ color: '#28a745', fontStyle: 'italic' }}>
              Waiting for next agent communication...
            </span>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default CommunicationTimeline;