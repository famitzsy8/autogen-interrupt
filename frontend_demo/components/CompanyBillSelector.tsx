import React, { useState, useEffect } from 'react';

interface CompanyBillPair {
  company: string;
  bill: string;
  description: string;
}

interface CompanyBillSelectorProps {
  onSelectionChange: (pair: CompanyBillPair | null) => void;
  disabled?: boolean;
}

const CompanyBillSelector: React.FC<CompanyBillSelectorProps> = ({ 
  onSelectionChange, 
  disabled = false 
}) => {
  const [pairs, setPairs] = useState<CompanyBillPair[]>([]);
  const [selectedValue, setSelectedValue] = useState<string>('');

  useEffect(() => {
    // In a real implementation, this would fetch from an API
    // For now, we'll use the hardcoded data from our CSV
    const mockPairs: CompanyBillPair[] = [
      { company: 'ExxonMobil', bill: 'hr2307-117', description: 'Climate and Energy Policy Act' },
      { company: 'Pfizer', bill: 's1234-118', description: 'Pharmaceutical Pricing Reform Act' },
      { company: 'Amazon', bill: 'hr3684-117', description: 'Digital Services Competition Act' },
      { company: 'Apple', bill: 's2456-119', description: 'Technology Innovation and Privacy Act' },
      { company: 'Tesla', bill: 'hr1789-118', description: 'Electric Vehicle Infrastructure Act' },
      { company: 'Meta', bill: 's3201-117', description: 'Social Media Accountability Act' },
      { company: 'Google', bill: 'hr4567-119', description: 'Artificial Intelligence Regulation Act' },
      { company: 'Microsoft', bill: 's1876-118', description: 'Cloud Computing Security Act' },
      { company: 'JPMorgan Chase', bill: 'hr2890-117', description: 'Financial Services Reform Act' },
      { company: 'Walmart', bill: 's3456-119', description: 'Worker Protection and Benefits Act' }
    ];
    
    setPairs(mockPairs);
  }, []);

  const handleSelectionChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    setSelectedValue(value);
    
    if (value === '') {
      onSelectionChange(null);
    } else {
      const [company, bill] = value.split('|');
      const selectedPair = pairs.find(p => p.company === company && p.bill === bill);
      onSelectionChange(selectedPair || null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: '400px' }}>
      <label 
        htmlFor="company-bill-selector" 
        style={{ 
          marginBottom: '0.5rem', 
          fontWeight: '500',
          color: '#333'
        }}
      >
        Select Company-Bill Pair:
      </label>
      <select
        id="company-bill-selector"
        value={selectedValue}
        onChange={handleSelectionChange}
        disabled={disabled}
        style={{
          padding: '0.75rem',
          border: '1px solid #ddd',
          borderRadius: '4px',
          fontSize: '1rem',
          backgroundColor: disabled ? '#f8f9fa' : 'white',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1
        }}
      >
        <option value="">Choose a company-bill pair...</option>
        {pairs.map((pair, index) => (
          <option 
            key={index} 
            value={`${pair.company}|${pair.bill}`}
          >
            {pair.company} - {pair.bill} ({pair.description})
          </option>
        ))}
      </select>
    </div>
  );
};

export default CompanyBillSelector;