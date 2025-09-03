import React, { useState, useEffect } from 'react';

interface BillInfo {
  billId: string;
  title: string;
  tokens: number;
}

interface BillSelectorProps {
  companyName: string;
  companyColor: string;
  onBillSelect: (company: string, billId: string) => void;
  onBack: () => void;
}

const formatBillName = (billId: string): string => {
  // Convert "s3591-116" to "S. 3591 (116th)"
  const match = billId.match(/([a-z]+)(\d+)-(\d+)/);
  if (match) {
    const [, chamber, number, congress] = match;
    const chamberUpper = chamber.toUpperCase();
    const congressOrdinal = congress + 'th';
    
    if (chamber === 's') {
      return `S. ${number} (${congressOrdinal})`;
    } else if (chamber === 'hr') {
      return `H.R. ${number} (${congressOrdinal})`;
    } else if (chamber === 'hjres') {
      return `H.J.Res. ${number} (${congressOrdinal})`;
    } else if (chamber === 'hres') {
      return `H.Res. ${number} (${congressOrdinal})`;
    } else if (chamber === 'hconres') {
      return `H.Con.Res. ${number} (${congressOrdinal})`;
    } else if (chamber === 'sjres') {
      return `S.J.Res. ${number} (${congressOrdinal})`;
    } else if (chamber === 'sres') {
      return `S.Res. ${number} (${congressOrdinal})`;
    } else if (chamber === 'sconres') {
      return `S.Con.Res. ${number} (${congressOrdinal})`;
    }
  }
  return billId;
};

const BillSelector: React.FC<BillSelectorProps> = ({ 
  companyName, 
  companyColor, 
  onBillSelect, 
  onBack 
}) => {
  const [bills, setBills] = useState<BillInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadBills = async () => {
      try {
        // Load the CSV data and lengths data
        const csvResponse = await fetch('/data/big_tech_mini.csv');
        const csvText = await csvResponse.text();
        
        const lengthsResponse = await fetch('/data/lengths_and_names.json');
        const lengthsData = await lengthsResponse.json();
        
        // Parse CSV (handle quoted fields properly)
        const parseCSVLine = (line: string): string[] => {
          const result: string[] = [];
          let current = '';
          let inQuotes = false;
          
          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
              result.push(current.trim());
              current = '';
            } else {
              current += char;
            }
          }
          result.push(current.trim());
          return result;
        };

        const lines = csvText.split('\n');
        const headers = parseCSVLine(lines[0]);
        const billIdIndex = headers.indexOf('bill_id');
        const clientNameIndex = headers.indexOf('client_name');
        
        if (billIdIndex === -1 || clientNameIndex === -1) {
          throw new Error('Required columns not found in CSV');
        }
        
        // Find bills for this company
        const companyBills = new Set<string>();
        for (let i = 1; i < lines.length; i++) {
          const line = lines[i].trim();
          if (!line) continue;
          
          const cols = parseCSVLine(line);
          if (cols.length > Math.max(clientNameIndex, billIdIndex)) {
            const csvCompanyName = cols[clientNameIndex]?.replace(/"/g, '').trim();
            const billId = cols[billIdIndex]?.trim();
            
            if (csvCompanyName === companyName && billId) {
              companyBills.add(billId);
            }
          }
        }

        console.log(lengthsData)
        
        // Create bill info array (limited to 20)
        const billInfos: BillInfo[] = Array.from(companyBills)
          .slice(0, 20)
          .map(billId => ({
            billId,
            title: lengthsData[billId]?.title || 'Unknown Bill Title',
            tokens: lengthsData[billId]?.tokens || 0
          }))
          .sort((a, b) => a.billId.localeCompare(b.billId));
        
        setBills(billInfos);
      } catch (error) {
        console.error('Error loading bills:', error);
      } finally {
        setLoading(false);
      }
    };

    loadBills();
  }, [companyName]);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          color: 'white',
          fontSize: '1.5rem',
          textAlign: 'center'
        }}>
          Loading bills for {companyName}...
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '2rem'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: '3rem',
          gap: '1rem'
        }}>
          <button
            onClick={onBack}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.3)',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '1rem',
              transition: 'all 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.2)';
            }}
          >
            ← Back to Companies
          </button>
          
          <h1 style={{
            color: 'white',
            margin: 0,
            fontSize: '2.5rem',
            fontWeight: '700'
          }}>
            Select Bill for {companyName}
          </h1>
        </div>

        {/* Bills Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
          gap: '1.5rem'
        }}>
          {bills.map((bill) => (
            <div
              key={bill.billId}
              onClick={() => onBillSelect(companyName, bill.billId)}
              style={{
                background: 'rgba(255,255,255,0.95)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '12px',
                padding: '1.5rem',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                boxShadow: '0 4px 16px rgba(0,0,0,0.1)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.2)';
                e.currentTarget.style.background = 'rgba(255,255,255,1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.1)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.95)';
              }}
            >
              {/* Bill Name */}
              <div style={{
                fontSize: '1.25rem',
                fontWeight: '700',
                color: companyColor,
                marginBottom: '0.5rem'
              }}>
                {formatBillName(bill.billId)}
              </div>
              
              {/* Bill Title */}
              <div style={{
                fontSize: '1rem',
                color: '#374151',
                marginBottom: '1rem',
                lineHeight: '1.5',
                minHeight: '3rem'
              }}>
                {bill.title}
              </div>
              
              {/* Bill Stats */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                paddingTop: '1rem',
                borderTop: '1px solid #e5e7eb'
              }}>
                <div style={{
                  fontSize: '0.875rem',
                  color: '#6b7280',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  📄 {bill.tokens.toLocaleString()} tokens
                </div>
                
                <div style={{
                  fontSize: '0.875rem',
                  color: companyColor,
                  fontWeight: '600'
                }}>
                  Investigate →
                </div>
              </div>
            </div>
          ))}
        </div>

        {bills.length === 0 && (
          <div style={{
            textAlign: 'center',
            color: 'white',
            fontSize: '1.2rem',
            marginTop: '3rem'
          }}>
            No bills found for {companyName}
          </div>
        )}
      </div>
    </div>
  );
};

export default BillSelector;