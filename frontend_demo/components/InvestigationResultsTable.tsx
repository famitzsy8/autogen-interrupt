import React, { useState } from 'react';

interface CongressMember {
  name: string;
  party: string;
  state: string;
  district: string;
  ranking: string;
  reason: string;
  chamber: string;
}

interface TableData {
  members: CongressMember[];
  summary: string;
  table_type: string;
  // New dual table support
  has_dual_tables?: boolean;
  aligned_members?: CongressMember[];
  opposed_members?: CongressMember[];
}

interface InvestigationResultsTableProps {
  tableData: TableData;
  billId: string;
  companyName: string;
}

const InvestigationResultsTable: React.FC<InvestigationResultsTableProps> = ({
  tableData,
  billId,
  companyName
}) => {
  const [sortField, setSortField] = useState<keyof CongressMember>('ranking');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Format bill ID to proper display format
  const formatBillId = (billId: string): string => {
    const parts = billId.split('-');
    if (parts.length !== 2) return billId;
    
    const [chamber_number, congress] = parts;
    let chamber = '';
    let number = '';
    
    if (chamber_number.startsWith('hr')) {
      chamber = 'H.R.';
      number = chamber_number.substring(2);
    } else if (chamber_number.startsWith('s')) {
      chamber = 'S.';
      number = chamber_number.substring(1);
    } else if (chamber_number.startsWith('hjres')) {
      chamber = 'H.J.Res.';
      number = chamber_number.substring(5);
    } else if (chamber_number.startsWith('sconres')) {
      chamber = 'S.Con.Res.';
      number = chamber_number.substring(7);
    } else if (chamber_number.startsWith('sres')) {
      chamber = 'S.Res.';
      number = chamber_number.substring(4);
    } else {
      return billId.toUpperCase();
    }
    
    return `${chamber} ${number} (${congress}th)`;
  };

  // Format district display
  const formatLocation = (member: CongressMember): string => {
    if (member.chamber === 'House' && member.district) {
      return `${member.state}-${member.district}`;
    }
    return member.state;
  };

  // Get party color
  const getPartyColor = (party: string): string => {
    if (party.toLowerCase().includes('democrat') || party === 'D') {
      return '#2563eb'; // Blue
    } else if (party.toLowerCase().includes('republican') || party === 'R') {
      return '#dc2626'; // Red
    }
    return '#6b7280'; // Gray for unknown
  };

  // Get chamber icon
  const getChamberIcon = (chamber: string): string => {
    if (chamber === 'House') return '🏛️';
    if (chamber === 'Senate') return '🏛️';
    return '📍';
  };

  // Sort members
  const sortedMembers = [...tableData.members].sort((a, b) => {
    const aRaw = a[sortField] ?? '';
    const bRaw = b[sortField] ?? '';

    let aVal: string | number = aRaw as string;
    let bVal: string | number = bRaw as string;

    // Handle numeric ranking (treat missing as large number)
    if (sortField === 'ranking') {
      const aNum = typeof aRaw === 'number' ? aRaw : parseInt(String(aRaw), 10);
      const bNum = typeof bRaw === 'number' ? bRaw : parseInt(String(bRaw), 10);
      aVal = Number.isFinite(aNum) ? aNum : 999;
      bVal = Number.isFinite(bNum) ? bNum : 999;
    }

    if (sortDirection === 'asc') {
      return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    } else {
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    }
  });

  const handleSort = (field: keyof CongressMember) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (field: keyof CongressMember) => {
    if (sortField !== field) return '↕️';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  // Helper function to render a single table
  const renderSingleTable = (members: CongressMember[], title: string, bgColor: string, icon: string) => (
    <div style={{
      background: '#ffffff',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
      border: '1px solid #e5e7eb',
      overflow: 'hidden',
      margin: '1rem 0'
    }}>
      {/* Table Header */}
      <div style={{
        background: bgColor,
        borderBottom: '1px solid #e5e7eb',
        padding: '1rem 1.5rem',
        textAlign: 'left'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ fontSize: '1.2rem' }}>{icon}</div>
          <h4 style={{
            margin: 0,
            fontSize: '1.1rem',
            fontWeight: '600',
            color: '#111827'
          }}>
            {title}
          </h4>
          <span style={{
            background: 'rgba(0,0,0,0.1)',
            padding: '0.25rem 0.5rem',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: '600'
          }}>
            {members.length} members
          </span>
        </div>
      </div>

      {/* Table Content */}
      <div style={{ padding: '1rem' }}>
        {members.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '2rem',
            color: '#6b7280'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📊</div>
            <p>No members found in this category.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'separate',
              borderSpacing: '0',
              fontSize: '0.875rem'
            }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: '500',
                    color: '#6b7280',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Rank
                  </th>
                  <th style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: '500',
                    color: '#6b7280',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Member
                  </th>
                  <th style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'center',
                    fontWeight: '500',
                    color: '#6b7280',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Party
                  </th>
                  <th style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'center',
                    fontWeight: '500',
                    color: '#6b7280',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Location
                  </th>
                  <th style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: '500',
                    color: '#6b7280',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Analysis
                  </th>
                </tr>
              </thead>
              <tbody>
                {members.map((member, index) => (
                  <tr key={index} style={{
                    borderBottom: '1px solid #f1f3f4'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8f9fa';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}>
                    <td style={{
                      padding: '0.75rem 1rem',
                      fontSize: '0.8rem',
                      fontWeight: '500',
                      color: '#9ca3af'
                    }}>
                      {member.ranking || (index + 1)}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '1.2rem' }}>
                          {getChamberIcon(member.chamber)}
                        </span>
                        <div>
                          <div style={{
                            fontWeight: '600',
                            color: '#1f2937',
                            fontSize: '0.95rem'
                          }}>
                            {member.name}
                          </div>
                          <div style={{
                            fontSize: '0.8rem',
                            color: '#6b7280'
                          }}>
                            {member.chamber === 'House' ? 'Representative' : 'Senator'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ 
                      padding: '0.75rem 1rem',
                      textAlign: 'center'
                    }}>
                      {member.party && (
                        <span style={{
                          display: 'inline-block',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '12px',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          color: 'white',
                          backgroundColor: getPartyColor(member.party)
                        }}>
                          {member.party === 'D' ? 'Dem' : member.party === 'R' ? 'Rep' : member.party}
                        </span>
                      )}
                    </td>
                    <td style={{
                      padding: '0.75rem 1rem',
                      textAlign: 'center',
                      fontSize: '0.8rem',
                      fontWeight: '500',
                      color: '#6b7280'
                    }}>
                      {formatLocation(member)}
                    </td>
                    <td style={{
                      padding: '0.75rem 1rem',
                      fontSize: '0.8rem',
                      color: '#374151',
                      lineHeight: '1.4'
                    }}>
                      {member.reason || 'Analysis pending'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );

  if (tableData.has_dual_tables && tableData.aligned_members && tableData.opposed_members) {
    // Render dual tables
    return (
      <div style={{
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        margin: '2rem 0'
      }}>
        {/* Main Header */}
        <div style={{
          background: '#ffffff',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
          border: '1px solid #e5e7eb',
          overflow: 'hidden',
          marginBottom: '2rem'
        }}>
          <div style={{
            background: '#f9fafb',
            borderBottom: '1px solid #e5e7eb',
            padding: '1.5rem 2rem',
            textAlign: 'left'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <div style={{ fontSize: '1.5rem' }}>🏛️</div>
              <h3 style={{
                margin: 0,
                fontSize: '1.5rem',
                fontWeight: '600',
                color: '#111827'
              }}>
                Congressional Analysis Results
              </h3>
            </div>
            <p style={{
              margin: 0,
              color: '#6b7280',
              fontSize: '0.9rem'
            }}>
              {companyName} lobbying investigation • {formatBillId(billId)}
            </p>
            {tableData.summary && (
              <p style={{
                margin: '0.75rem 0 0 0',
                color: '#6b7280',
                fontSize: '0.85rem',
                fontStyle: 'italic'
              }}>
                {tableData.summary}
              </p>
            )}
          </div>

          {/* Combined Stats */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-around',
            padding: '1rem 2rem',
            background: '#f9fafb'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
                {tableData.members.length}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Members</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#059669' }}>
                {tableData.aligned_members.length}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Aligned</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#dc2626' }}>
                {tableData.opposed_members.length}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Opposed</div>
            </div>
          </div>
        </div>

        {/* Aligned Members Table */}
        <div style={{ margin: '2rem 0' }}>
          <div style={{
            background: '#059669',
            color: 'white',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px 8px 0 0',
            fontWeight: '600',
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span>👍</span>
            POLITICIANS MOST ALIGNED WITH {companyName.toUpperCase()} INTERESTS
          </div>
          {renderSingleTable(
            tableData.aligned_members, 
            "Most Aligned with Company Interests",
            '#d1fae5', // Light green background
            '👍'
          )}
        </div>

        {/* Opposed Members Table */}
        <div style={{ margin: '2rem 0' }}>
          <div style={{
            background: '#dc2626',
            color: 'white',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px 8px 0 0',
            fontWeight: '600',
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span>👎</span>
            POLITICIANS MOST OPPOSED TO {companyName.toUpperCase()} INTERESTS
          </div>
          {renderSingleTable(
            tableData.opposed_members, 
            "Most Opposed to Company Interests",
            '#fecaca', // Light red background
            '👎'
          )}
        </div>

        {/* Footer */}
        <div style={{
          background: '#f9fafb',
          padding: '1rem 2rem',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
          textAlign: 'center',
          fontSize: '0.75rem',
          color: '#9ca3af',
          marginTop: '1rem'
        }}>
          <p style={{ margin: 0 }}>
            🤖 Dual table analysis completed by AutoGen Multi-Agent Investigation System
          </p>
        </div>
      </div>
    );
  }

  // Fallback to single table rendering
  return (
    <div style={{
      background: '#ffffff',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
      border: '1px solid #e5e7eb',
      overflow: 'hidden',
      margin: '2rem 0',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{
        background: '#f9fafb',
        borderBottom: '1px solid #e5e7eb',
        padding: '1.5rem 2rem',
        textAlign: 'left'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div style={{ fontSize: '1.5rem' }}>🏛️</div>
          <h3 style={{
            margin: 0,
            fontSize: '1.5rem',
            fontWeight: '600',
            color: '#111827'
          }}>
            Congressional Analysis Results
          </h3>
        </div>
        <p style={{
          margin: 0,
          color: '#6b7280',
          fontSize: '0.9rem'
        }}>
          {companyName} lobbying investigation • {formatBillId(billId)}
        </p>
        {tableData.summary && (
          <p style={{
            margin: '0.75rem 0 0 0',
            color: '#6b7280',
            fontSize: '0.85rem',
            fontStyle: 'italic'
          }}>
            {tableData.summary}
          </p>
        )}
      </div>

      {/* Stats Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-around',
        padding: '1rem 2rem',
        background: '#f9fafb',
        borderBottom: '1px solid #e5e7eb'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
            {tableData.members.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Members</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
            {tableData.members.filter(m => m.chamber === 'House').length}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>House</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#111827' }}>
            {tableData.members.filter(m => m.chamber === 'Senate').length}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Senate</div>
        </div>
      </div>

      {/* Table */}
      <div style={{ padding: '1rem' }}>
        {tableData.members.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            color: '#6b7280'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
            <p>No congressional members data available in the results.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'separate',
              borderSpacing: '0',
              fontSize: '0.875rem'
            }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th onClick={() => handleSort('ranking')} style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: '500',
                    color: '#6b7280',
                    cursor: 'pointer',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Rank {getSortIcon('ranking')}
                  </th>
                  <th onClick={() => handleSort('name')} style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: '500',
                    color: '#6b7280',
                    cursor: 'pointer',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Member {getSortIcon('name')}
                  </th>
                  <th onClick={() => handleSort('party')} style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'center',
                    fontWeight: '500',
                    color: '#6b7280',
                    cursor: 'pointer',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Party {getSortIcon('party')}
                  </th>
                  <th onClick={() => handleSort('state')} style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'center',
                    fontWeight: '500',
                    color: '#6b7280',
                    cursor: 'pointer',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Location {getSortIcon('state')}
                  </th>
                  <th onClick={() => handleSort('reason')} style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    fontWeight: '500',
                    color: '#6b7280',
                    cursor: 'pointer',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}>
                    Analysis {getSortIcon('reason')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedMembers.map((member, index) => (
                  <tr key={index} style={{
                    borderBottom: '1px solid #f1f3f4'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8f9fa';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}>
                    <td style={{
                      padding: '0.75rem 1rem',
                      fontSize: '0.8rem',
                      fontWeight: '500',
                      color: '#9ca3af'
                    }}>
                      {member.ranking || (index + 1)}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '1.2rem' }}>
                          {getChamberIcon(member.chamber)}
                        </span>
                        <div>
                          <div style={{
                            fontWeight: '600',
                            color: '#1f2937',
                            fontSize: '0.95rem'
                          }}>
                            {member.name}
                          </div>
                          <div style={{
                            fontSize: '0.8rem',
                            color: '#6b7280'
                          }}>
                            {member.chamber === 'House' ? 'Representative' : 'Senator'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ 
                      padding: '0.75rem 1rem',
                      textAlign: 'center'
                    }}>
                      {member.party && (
                        <span style={{
                          display: 'inline-block',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '12px',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          color: 'white',
                          backgroundColor: getPartyColor(member.party)
                        }}>
                          {member.party === 'D' ? 'Dem' : member.party === 'R' ? 'Rep' : member.party}
                        </span>
                      )}
                    </td>
                    <td style={{
                      padding: '0.75rem 1rem',
                      textAlign: 'center',
                      fontSize: '0.8rem',
                      fontWeight: '500',
                      color: '#6b7280'
                    }}>
                      {formatLocation(member)}
                    </td>
                    <td style={{
                      padding: '0.75rem 1rem',
                      fontSize: '0.8rem',
                      color: '#374151',
                      lineHeight: '1.4'
                    }}>
                      {member.reason || 'Analysis pending'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        background: '#f9fafb',
        padding: '1rem 2rem',
        borderTop: '1px solid #e5e7eb',
        textAlign: 'center',
        fontSize: '0.75rem',
        color: '#9ca3af'
      }}>
        <p style={{ margin: 0 }}>
          🤖 Analysis completed by AutoGen Multi-Agent Investigation System
        </p>
      </div>
    </div>
  );
};

export default InvestigationResultsTable;