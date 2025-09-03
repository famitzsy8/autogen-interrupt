import React, { useState, useEffect, useRef } from 'react';
import { AgentCommunication } from '../lib/llm-processor';
import ExpandableStep from './ExpandableStep';
import FinalResultsTable from './FinalResultsTable';
import InvestigationResultsTable from './InvestigationResultsTable';
import toolSummaries from '../data/tool-summaries.json';
import { ParsedTable } from '../lib/table-parser';

interface EnhancedCommunicationTimelineProps {
  communications: AgentCommunication[];
  isRunning: boolean;
  billId?: string;
  companyName?: string;
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

const EnhancedCommunicationTimeline: React.FC<EnhancedCommunicationTimelineProps> = ({ 
  communications, 
  isRunning,
  billId = '',
  companyName = ''
}) => {
  const [isAutoCenter, setIsAutoCenter] = useState(true);
  const [showLatestButton, setShowLatestButton] = useState(false);
  const [isScrollingUp, setIsScrollingUp] = useState(false);
  const timelineRef = useRef<HTMLDivElement>(null);
  const latestItemRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to center when new communication arrives and auto-center is enabled
  useEffect(() => {
    if (isAutoCenter && communications.length > 0 && latestItemRef.current) {
      // Restore gradient when new message arrives and we auto-scroll
      setIsScrollingUp(false);
      
      setTimeout(() => {
        latestItemRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }, 100);
    }
    
    // Add debug event for timeline rendering
    if ((window as any).addCommunicationDebugEvent) {
      (window as any).addCommunicationDebugEvent(
        'timeline_rendered',
        { 
          communicationCount: communications.length,
          latestAgent: communications[communications.length - 1]?.agent,
          autoCenter: isAutoCenter
        },
        `Rendered ${communications.length} communications, latest: ${communications[communications.length - 1]?.agent || 'none'}`
      );
    }
  }, [communications.length, isAutoCenter]);

  // Handle scroll detection
  useEffect(() => {
    let lastScrollTop = 0;
    
    const handleScroll = () => {
      if (!timelineRef.current || !latestItemRef.current) return;

      const currentScrollTop = timelineRef.current.scrollTop;
      const isScrollingUpwards = currentScrollTop < lastScrollTop;
      setIsScrollingUp(isScrollingUpwards && currentScrollTop > 0);
      lastScrollTop = currentScrollTop;

      const timelineRect = timelineRef.current.getBoundingClientRect();
      const latestRect = latestItemRef.current.getBoundingClientRect();
      
      const timelineCenter = timelineRect.top + timelineRect.height / 2;
      const latestCenter = latestRect.top + latestRect.height / 2;
      
      const distanceFromCenter = Math.abs(timelineCenter - latestCenter);
      const threshold = 200; // pixels
      
      if (distanceFromCenter > threshold) {
        setIsAutoCenter(false);
        setShowLatestButton(true);
      } else {
        setShowLatestButton(false);
      }
    };

    const timelineElement = timelineRef.current;
    if (timelineElement) {
      timelineElement.addEventListener('scroll', handleScroll);
      return () => timelineElement.removeEventListener('scroll', handleScroll);
    }
  }, []);

  const handleLatestClick = () => {
    setIsAutoCenter(true);
    setShowLatestButton(false);
    if (latestItemRef.current) {
      latestItemRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  };

  const getOpacity = (index: number, total: number) => {
    if (total <= 5) return 1;
    
    const distanceFromLatest = total - 1 - index;
    if (distanceFromLatest <= 2) return 1;
    if (distanceFromLatest <= 4) return 0.7;
    if (distanceFromLatest <= 6) return 0.4;
    return 0.2;
  };

  const getScale = (index: number, total: number) => {
    if (total <= 5) return 1;
    
    const distanceFromLatest = total - 1 - index;
    if (distanceFromLatest <= 2) return 1;
    if (distanceFromLatest <= 4) return 0.98;
    if (distanceFromLatest <= 6) return 0.95;
    return 0.92;
  };

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
      position: 'relative',
      background: 'rgba(255,255,255,0.98)',
      borderRadius: '16px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
      border: '1px solid rgba(255,255,255,0.5)',
      backdropFilter: 'blur(10px)',
      overflow: 'hidden',
      transition: 'background 0.3s ease'
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '2rem 2rem 1rem 2rem'
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

      {/* Timeline Container */}
      <div 
        ref={timelineRef}
        style={{ 
          height: '70vh', 
          overflowY: 'auto',
          padding: '1rem 2rem 2rem 2rem',
          position: 'relative'
        }}
      >
        {communications.map((comm, index) => {
          const isLatest = index === communications.length - 1;
          const opacity = isAutoCenter ? getOpacity(index, communications.length) : 1;
          const scale = isAutoCenter ? getScale(index, communications.length) : 1;
          
          // Check if this is the table results communication
          if (comm.type === 'table_results' || comm.id.includes('final_table')) {
            // Use the new tableData field from our parser
            if (comm.tableData && comm.tableData.members) {
              const parsedTable = comm.tableData as ParsedTable;
              
              // Convert to the format expected by InvestigationResultsTable
              const tableData = {
                members: parsedTable.members.map(member => ({
                  name: member.name,
                  party: member.party || 'Unknown',
                  state: member.state,
                  district: member.district || '',
                  ranking: member.rank.toString(),
                  reason: member.reason,
                  chamber: member.chamber
                })),
                summary: `Investigation Results - ${parsedTable.members.length} members analyzed`,
                table_type: 'congress_involvement'
              };
              
              return (
                <div 
                  key={comm.id} 
                  ref={isLatest ? latestItemRef : undefined}
                  style={{ 
                    marginTop: '2rem',
                    opacity,
                    transform: `scale(${scale})`,
                    transition: 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
                    animation: isLatest ? 'slideInCenter 0.8s cubic-bezier(0.4, 0, 0.2, 1)' : undefined
                  }}
                >
                  <InvestigationResultsTable 
                    tableData={tableData}
                    billId={parsedTable.billId || billId}
                    companyName={companyName}
                  />
                </div>
              );
            } else {
              // Fallback: try to parse from fullContent for backward compatibility
              try {
                const tableData = JSON.parse(comm.fullContent || '{}');
                return (
                  <div 
                    key={comm.id} 
                    ref={isLatest ? latestItemRef : undefined}
                    style={{ 
                      marginTop: '2rem',
                      opacity,
                      transform: `scale(${scale})`,
                      transition: 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
                      animation: isLatest ? 'slideInCenter 0.8s cubic-bezier(0.4, 0, 0.2, 1)' : undefined
                    }}
                  >
                    <InvestigationResultsTable 
                      tableData={tableData}
                      billId={billId}
                      companyName={companyName}
                    />
                  </div>
                );
              } catch (e) {
                console.error('Failed to parse table data:', e);
                // Fallback to regular display will happen below
              }
            }
          }

          // Add debug event for individual box display
          if ((window as any).addCommunicationDebugEvent) {
            (window as any).addCommunicationDebugEvent(
              'box_displayed',
              {
                id: comm.id,
                agent: comm.agent,
                type: comm.type,
                simplified: comm.simplified,
                isLatest,
                opacity,
                scale
              },
              `Displaying box for ${comm.agent}: ${comm.simplified?.substring(0, 50) || 'No summary'}`
            );
          }

          return (
            <div
              key={comm.id}
              ref={isLatest ? latestItemRef : undefined}
              style={{
                opacity,
                transform: `scale(${scale})`,
                transition: 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
                animation: isLatest ? 'slideInCenter 0.8s cubic-bezier(0.4, 0, 0.2, 1)' : undefined,
                marginBottom: index === communications.length - 1 ? 0 : '1rem'
              }}
            >
              <ExpandableStep
                communication={comm}
                agentColor={getAgentColor(comm.agent)}
                typeIcon={getTypeIcon(comm.type)}
                isLast={index === communications.length - 1}
                toolCallSummaries={toolSummaries}
              />
            </div>
          );
        })}
        
        {isRunning && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            padding: '1rem',
            background: 'rgba(255,255,255,0.95)',
            borderRadius: '12px',
            border: '2px dashed #10b981',
            marginTop: communications.length > 0 ? '1rem' : 0,
            animation: 'pulse 2s infinite'
          }}>
            <div style={{
              width: '3rem',
              height: '3rem',
              borderRadius: '50%',
              background: '#10b981',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              animation: 'bounce 1.5s infinite'
            }}>
              ⏳
            </div>
            <span style={{ color: '#10b981', fontStyle: 'italic', fontWeight: '500' }}>
              Waiting for next agent communication...
            </span>
          </div>
        )}
      </div>

      {/* Latest Button */}
      {showLatestButton && (
        <button
          onClick={handleLatestClick}
          style={{
            position: 'absolute',
            bottom: '2rem',
            right: '2rem',
            padding: '0.75rem 1.5rem',
            background: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: '25px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: '600',
            boxShadow: '0 4px 16px rgba(102, 126, 234, 0.4)',
            transition: 'all 0.3s ease',
            zIndex: 1000,
            animation: 'slideInButton 0.3s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 16px rgba(102, 126, 234, 0.4)';
          }}
        >
          ⬇️ Latest
        </button>
      )}

      <style jsx>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
        
        @keyframes bounce {
          0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-10px); }
          60% { transform: translateY(-5px); }
        }
        
        @keyframes slideInCenter {
          0% {
            opacity: 0;
            transform: translateY(30px) scale(0.95);
          }
          100% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        
        @keyframes slideInButton {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
};

export default EnhancedCommunicationTimeline;