import React, { useState, useEffect } from 'react';

interface Company {
  id: string;
  name: string;
  bill: string;
  description: string;
  logo: string;
  primaryColor: string;
  secondaryColor: string;
  industry: string;
  billSummary: string;
}

interface CompanyFromCSV {
  name: string;
  billCount: number;
}

interface CompanySelectionProps {
  onCompanySelect: (company: Company) => void;
}

const CompanySelection: React.FC<CompanySelectionProps> = ({ onCompanySelect }) => {
  const [companies, setCompanies] = useState<CompanyFromCSV[]>([]);
  const [loading, setLoading] = useState(true);

  // Generate colors for companies
  const getCompanyColors = (index: number) => {
    const colors = [
      { primary: '#e11d48', secondary: '#f43f5e' }, // Red
      { primary: '#0ea5e9', secondary: '#38bdf8' }, // Blue
      { primary: '#059669', secondary: '#10b981' }, // Green
      { primary: '#d97706', secondary: '#f59e0b' }, // Orange
      { primary: '#7c3aed', secondary: '#8b5cf6' }, // Purple
      { primary: '#dc2626', secondary: '#ef4444' }, // Red variant
      { primary: '#0891b2', secondary: '#06b6d4' }, // Cyan
      { primary: '#65a30d', secondary: '#84cc16' }, // Lime
    ];
    return colors[index % colors.length];
  };

  // Generate logo emoji for companies
  const getCompanyLogo = (name: string) => {
    const logos = ['🏢', '🏭', '⚡', '🛢️', '🌊', '⛽', '🔋', '🌿'];
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return logos[hash % logos.length];
  };

  useEffect(() => {
    const loadCompanies = async () => {
      try {
        const response = await fetch('/data/big_tech_mini.csv');
        if (!response.ok) {
          throw new Error(`Failed to fetch CSV: ${response.status}`);
        }
        const csvText = await response.text();
        
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
        const clientNameIndex = headers.indexOf('client_name');
        const billIdIndex = headers.indexOf('bill_id');
        
        if (clientNameIndex === -1 || billIdIndex === -1) {
          throw new Error('Required columns not found in CSV');
        }
        
        // Count bills per company
        const companyBillCounts = new Map<string, Set<string>>();
        
        for (let i = 1; i < lines.length; i++) {
          const line = lines[i].trim();
          if (!line) continue;
          
          const cols = parseCSVLine(line);
          if (cols.length > Math.max(clientNameIndex, billIdIndex)) {
            const companyName = cols[clientNameIndex]?.replace(/"/g, '').trim();
            const billId = cols[billIdIndex]?.trim();
            
            if (companyName && billId) {
              if (!companyBillCounts.has(companyName)) {
                companyBillCounts.set(companyName, new Set());
              }
              companyBillCounts.get(companyName)!.add(billId);
            }
          }
        }
        
        // Convert to array and sort by bill count
        const companiesArray: CompanyFromCSV[] = Array.from(companyBillCounts.entries())
          .map(([name, bills]) => ({
            name,
            billCount: bills.size
          }))
          .sort((a, b) => b.billCount - a.billCount);
        
        setCompanies(companiesArray);
        console.log(`Loaded ${companiesArray.length} unique companies from CSV`);
      } catch (error) {
        console.error('Error loading companies:', error);
      } finally {
        setLoading(false);
      }
    };

    loadCompanies();
  }, []);

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
          Loading companies...
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '2rem',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      {/* Header */}
      <div style={{
        textAlign: 'center',
        marginBottom: '3rem',
        color: 'white'
      }}>
        <h1 style={{
          fontSize: '3rem',
          fontWeight: '700',
          margin: '0 0 1rem 0',
          textShadow: '0 2px 4px rgba(0,0,0,0.3)',
          background: 'linear-gradient(45deg, #ffffff, #f0f8ff)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>
          🏛️ Congressional Lobbying Investigator
        </h1>
        <p style={{
          fontSize: '1.3rem',
          opacity: 0.9,
          fontWeight: '300',
          margin: 0,
          textShadow: '0 1px 2px rgba(0,0,0,0.2)'
        }}>
          Select a company to investigate their lobbying activities
        </p>
      </div>

      {/* Company Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1.5rem',
        maxWidth: '1400px',
        width: '100%'
      }}>
        {companies.map((companyData, index) => {
          const colors = getCompanyColors(index);
          const logo = getCompanyLogo(companyData.name);
          
          // Create Company object for callback
          const company: Company = {
            id: `company_${index}`,
            name: companyData.name,
            bill: '', // Will be selected in next step
            description: `Oil & Gas Company with ${companyData.billCount} bills`,
            logo: logo,
            primaryColor: colors.primary,
            secondaryColor: colors.secondary,
            industry: 'Oil & Gas',
            billSummary: `${companyData.billCount} bills`
          };
          
          return (
          <div
            key={company.id}
            onClick={() => onCompanySelect(company)}
            style={{
              background: `linear-gradient(135deg, ${colors.primary}15, ${colors.secondary}25)`,
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '16px',
              padding: '2rem',
              cursor: 'pointer',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
              position: 'relative',
              overflow: 'hidden'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
              e.currentTarget.style.boxShadow = '0 12px 32px rgba(0, 0, 0, 0.2)';
              e.currentTarget.style.background = `linear-gradient(135deg, ${colors.primary}25, ${colors.secondary}35)`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0) scale(1)';
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.1)';
              e.currentTarget.style.background = `linear-gradient(135deg, ${colors.primary}15, ${colors.secondary}25)`;
            }}
          >
            {/* Subtle background pattern */}
            <div style={{
              position: 'absolute',
              top: 0,
              right: 0,
              width: '100px',
              height: '100px',
              background: `radial-gradient(circle, ${colors.primary}10, transparent 70%)`,
              borderRadius: '50%',
              transform: 'translate(30px, -30px)'
            }} />
            
            {/* Logo */}
            <div style={{
              fontSize: '3rem',
              marginBottom: '1rem',
              position: 'relative',
              zIndex: 1
            }}>
              {logo}
            </div>

            {/* Company Name */}
            <h3 style={{
              fontSize: '1.5rem',
              fontWeight: '600',
              margin: '0 0 0.5rem 0',
              color: '#1a1a1a',
              position: 'relative',
              zIndex: 1
            }}>
              {companyData.name}
            </h3>

            {/* Industry */}
            <div style={{
              display: 'inline-block',
              backgroundColor: colors.primary,
              color: 'white',
              padding: '0.3rem 0.8rem',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: '500',
              marginBottom: '1rem',
              position: 'relative',
              zIndex: 1
            }}>
              Oil & Gas
            </div>

            {/* Bill Info */}
            <div style={{
              position: 'relative',
              zIndex: 1
            }}>
              <div style={{
                fontSize: '0.9rem',
                fontWeight: '600',
                color: '#4a5568',
                marginBottom: '0.3rem'
              }}>
                {companyData.billCount} Bills
              </div>
              <div style={{
                fontSize: '0.95rem',
                fontWeight: '500',
                color: '#2d3748',
                marginBottom: '0.5rem'
              }}>
                {company.description}
              </div>
              <div style={{
                fontSize: '0.85rem',
                color: '#718096',
                lineHeight: '1.4'
              }}>
                Click to explore lobbying activities
              </div>
            </div>

            {/* Hover indicator */}
            <div style={{
              position: 'absolute',
              bottom: '1rem',
              right: '1rem',
              width: '2rem',
              height: '2rem',
              borderRadius: '50%',
              background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              transition: 'all 0.3s ease',
              opacity: 0.7
            }}>
              →
            </div>
          </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{
        marginTop: '3rem',
        textAlign: 'center',
        color: 'rgba(255, 255, 255, 0.7)',
        fontSize: '0.9rem'
      }}>
        <p style={{ margin: 0 }}>
          Advanced multi-agent analysis powered by AutoGen • Click any company to begin investigation
        </p>
      </div>
    </div>
  );
};

export default CompanySelection;