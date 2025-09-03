import React, { useState } from 'react';

interface CongressMember {
  rank: number;
  name: string;
  party: string;
  state: string;
  district?: string;
  involvement_score: number;
  role: string;
  key_actions: string[];
  reason: string;
  industry_connections: string;
  lobbying_interactions: string;
}

interface FinalResultsTableProps {
  investigationData: {
    investigation_summary: {
      company: string;
      bill: string;
      bill_title: string;
      investigation_date: string;
      total_members_analyzed: number;
      key_findings: string[];
    };
    congress_member_rankings: CongressMember[];
    summary_statistics: {
      democrats_supporting: number;
      republicans_supporting: number;
      committee_chairs_involved: number;
      energy_state_representatives: number;
      average_involvement_score: number;
      lobbying_meetings_documented: number;
    };
  };
}

const FinalResultsTable: React.FC<FinalResultsTableProps> = ({ investigationData }) => {
  const [selectedMember, setSelectedMember] = useState<CongressMember | null>(null);
  const [sortField, setSortField] = useState<keyof CongressMember>('rank');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const { investigation_summary, congress_member_rankings, summary_statistics } = investigationData;

  const getPartyColor = (party: string) => {
    switch (party) {
      case 'D': return '#2563eb';
      case 'R': return '#dc2626';
      default: return '#6b7280';
    }
  };

  const getInvolvementColor = (score: number) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#ef4444';
    return '#6b7280';
  };

  const sortedMembers = [...congress_member_rankings].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortDirection === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
  });

  const handleSort = (field: keyof CongressMember) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  return (
    <div style={{
      marginTop: '2rem',
      backgroundColor: 'white',
      borderRadius: '12px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        padding: '2.5rem',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: '-50px',
          right: '-50px',
          width: '200px',
          height: '200px',
          background: 'radial-gradient(circle, rgba(255,255,255,0.1), transparent 70%)',
          borderRadius: '50%'
        }} />
        <div style={{
          position: 'absolute',
          bottom: '-30px',
          left: '-30px',
          width: '150px',
          height: '150px',
          background: 'radial-gradient(circle, rgba(255,255,255,0.05), transparent 70%)',
          borderRadius: '50%'
        }} />
        
        <h2 style={{ 
          margin: '0 0 0.5rem 0', 
          fontSize: '2.2rem', 
          fontWeight: '700',
          textShadow: '0 2px 4px rgba(0,0,0,0.3)',
          position: 'relative',
          zIndex: 1
        }}>
          🏛️ Investigation Results
        </h2>
        <p style={{ 
          margin: 0, 
          opacity: 0.95, 
          fontSize: '1.2rem',
          fontWeight: '300',
          textShadow: '0 1px 2px rgba(0,0,0,0.2)',
          position: 'relative',
          zIndex: 1
        }}>
          {investigation_summary.company} Lobbying Analysis • {investigation_summary.bill_title}
        </p>
      </div>

      {/* Summary Stats */}
      <div style={{
        padding: '2rem',
        borderBottom: '1px solid #e5e7eb',
        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)'
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1.5rem'
        }}>
          <div style={{ 
            textAlign: 'center',
            padding: '1.5rem',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1))',
            borderRadius: '12px',
            border: '1px solid rgba(99, 102, 241, 0.2)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#4338ca' }}>
              {congress_member_rankings.length}
            </div>
            <div style={{ fontSize: '0.95rem', color: '#6b7280', fontWeight: '500' }}>Members Analyzed</div>
          </div>
          <div style={{ 
            textAlign: 'center',
            padding: '1.5rem',
            background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(59, 130, 246, 0.1))',
            borderRadius: '12px',
            border: '1px solid rgba(37, 99, 235, 0.2)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#2563eb' }}>
              {summary_statistics.democrats_supporting}
            </div>
            <div style={{ fontSize: '0.95rem', color: '#6b7280', fontWeight: '500' }}>Democrats Supporting</div>
          </div>
          <div style={{ 
            textAlign: 'center',
            padding: '1.5rem',
            background: 'linear-gradient(135deg, rgba(220, 38, 38, 0.1), rgba(248, 113, 113, 0.1))',
            borderRadius: '12px',
            border: '1px solid rgba(220, 38, 38, 0.2)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#dc2626' }}>
              {summary_statistics.republicans_supporting}
            </div>
            <div style={{ fontSize: '0.95rem', color: '#6b7280', fontWeight: '500' }}>Republicans Supporting</div>
          </div>
          <div style={{ 
            textAlign: 'center',
            padding: '1.5rem',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(52, 211, 153, 0.1))',
            borderRadius: '12px',
            border: '1px solid rgba(16, 185, 129, 0.2)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#10b981' }}>
              {Math.round(summary_statistics.average_involvement_score)}%
            </div>
            <div style={{ fontSize: '0.95rem', color: '#6b7280', fontWeight: '500' }}>Avg Involvement</div>
          </div>
        </div>
      </div>

      {/* Key Findings */}
      <div style={{ padding: '1.5rem', borderBottom: '1px solid #e5e7eb' }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', color: '#1f2937' }}>
          🔍 Key Findings
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {investigation_summary.key_findings.map((finding, index) => (
            <div key={index} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.75rem',
              backgroundColor: '#f3f4f6',
              borderRadius: '8px',
              borderLeft: '4px solid #3b82f6'
            }}>
              <span style={{ color: '#3b82f6', fontWeight: 'bold' }}>•</span>
              <span style={{ fontSize: '0.95rem', color: '#374151' }}>{finding}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ padding: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', color: '#1f2937' }}>
          📊 Congressional Member Rankings
        </h3>
        
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.9rem'
          }}>
            <thead>
              <tr style={{ 
                background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
                borderBottom: '2px solid #cbd5e0'
              }}>
                {[
                  { key: 'rank', label: 'Rank' },
                  { key: 'name', label: 'Member' },
                  { key: 'party', label: 'Party' },
                  { key: 'state', label: 'State' },
                  { key: 'involvement_score', label: 'Score' },
                  { key: 'role', label: 'Role' }
                ].map((column) => (
                  <th
                    key={column.key}
                    onClick={() => handleSort(column.key as keyof CongressMember)}
                    style={{
                      padding: '1rem 0.75rem',
                      textAlign: 'left',
                      fontWeight: '600',
                      color: '#374151',
                      cursor: 'pointer',
                      borderBottom: '2px solid #e5e7eb',
                      position: 'sticky',
                      top: 0,
                      backgroundColor: '#f9fafb'
                    }}
                  >
                    {column.label} {sortField === column.key && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedMembers.map((member, index) => (
                <tr
                  key={member.rank}
                  onClick={() => setSelectedMember(member)}
                  style={{
                    cursor: 'pointer',
                    backgroundColor: index % 2 === 0 ? 'white' : '#f9fafb',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = index % 2 === 0 ? 'white' : '#f9fafb'}
                >
                  <td style={{ padding: '1rem 0.75rem', borderBottom: '1px solid #e5e7eb' }}>
                    <div style={{
                      width: '2rem',
                      height: '2rem',
                      borderRadius: '50%',
                      backgroundColor: member.rank <= 3 ? '#fbbf24' : '#e5e7eb',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 'bold',
                      color: member.rank <= 3 ? 'white' : '#6b7280'
                    }}>
                      {member.rank}
                    </div>
                  </td>
                  <td style={{ padding: '1rem 0.75rem', borderBottom: '1px solid #e5e7eb' }}>
                    <div style={{ fontWeight: '600', color: '#1f2937' }}>{member.name}</div>
                    {member.district && (
                      <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>District {member.district}</div>
                    )}
                  </td>
                  <td style={{ padding: '1rem 0.75rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{
                      backgroundColor: getPartyColor(member.party),
                      color: 'white',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {member.party}
                    </span>
                  </td>
                  <td style={{ padding: '1rem 0.75rem', borderBottom: '1px solid #e5e7eb' }}>
                    {member.state}
                  </td>
                  <td style={{ padding: '1rem 0.75rem', borderBottom: '1px solid #e5e7eb' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{
                        width: '60px',
                        height: '6px',
                        backgroundColor: '#e5e7eb',
                        borderRadius: '3px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${member.involvement_score}%`,
                          height: '100%',
                          backgroundColor: getInvolvementColor(member.involvement_score),
                          borderRadius: '3px'
                        }} />
                      </div>
                      <span style={{
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        color: getInvolvementColor(member.involvement_score)
                      }}>
                        {member.involvement_score}%
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '1rem 0.75rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{
                      fontSize: '0.8rem',
                      color: '#6b7280',
                      backgroundColor: '#f3f4f6',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px'
                    }}>
                      {member.role}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Member Detail Modal */}
      {selectedMember && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '2rem'
        }}
        onClick={() => setSelectedMember(null)}
        >
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '2rem',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 20px 40px rgba(0,0,0,0.3)'
          }}
          onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.5rem', color: '#1f2937' }}>
                {selectedMember.name}
              </h3>
              <button
                onClick={() => setSelectedMember(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: '#6b7280'
                }}
              >
                ×
              </button>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <strong>Involvement Score:</strong> {selectedMember.involvement_score}%
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <strong>Role:</strong> {selectedMember.role}
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <strong>Key Actions:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                {selectedMember.key_actions.map((action, index) => (
                  <li key={index} style={{ marginBottom: '0.25rem' }}>{action}</li>
                ))}
              </ul>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <strong>Analysis:</strong>
              <p style={{ marginTop: '0.5rem', lineHeight: '1.6' }}>{selectedMember.reason}</p>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <strong>Industry Connections:</strong>
              <p style={{ marginTop: '0.5rem', lineHeight: '1.6' }}>{selectedMember.industry_connections}</p>
            </div>
            
            <div>
              <strong>Lobbying Interactions:</strong>
              <p style={{ marginTop: '0.5rem', lineHeight: '1.6' }}>{selectedMember.lobbying_interactions}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinalResultsTable;