import React, { useState, useEffect, useCallback } from 'react';
import { AgentCommunication } from '../lib/llm-processor';
import { RealTimeService } from '../lib/real-time-service';
import CompanyBillSelector from './CompanyBillSelector';
import EnhancedCommunicationTimeline from './EnhancedCommunicationTimeline';
import CompanySelection from './CompanySelection';
import BillSelector from './BillSelector';
import MessageDebugger from './MessageDebugger';
import ErrorBoundary from './ErrorBoundary';
import { safeStateUpdate, limitArraySize, classifyError, safeAsyncOperation } from '../lib/safe-operations';

interface CompanyBillPair {
  company: string;
  bill: string;
  description: string;
}

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

type AppStage = 'company_selection' | 'bill_selection' | 'investigation';

const AgentInvestigationDashboard: React.FC = () => {
  const [currentStage, setCurrentStage] = useState<AppStage>('company_selection');
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [selectedPair, setSelectedPair] = useState<CompanyBillPair | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [communications, setCommunications] = useState<AgentCommunication[]>([]);
  const [realTimeService] = useState(() => new RealTimeService());
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [showDebugger, setShowDebugger] = useState(false);

  const handleCompanySelect = (company: Company) => {
    setSelectedCompany(company);
    setCurrentStage('bill_selection');
    setCommunications([]);
    setIsRunning(false);
    realTimeService.stopSession();
  };

  const handleBillSelect = async (companyName: string, billId: string) => {
    try {
      // Fetch bill title from lengths_and_names.json
      const response = await fetch('/data/lengths_and_names.json');
      const lengthsData = await response.json();
      const billInfo = lengthsData[billId];
      const billTitle = billInfo?.title || `Bill ${billId}`;
      
      setSelectedPair({
        company: companyName,
        bill: billId,
        description: `Investigating aligned politicians in lobbied-for ${billTitle}`
      });
      setCurrentStage('investigation');
    } catch (error) {
      console.error('Error fetching bill title:', error);
      // Fallback to generic description
      setSelectedPair({
        company: companyName,
        bill: billId,
        description: `Investigating aligned politicians in lobbied-for bill ${billId}`
      });
      setCurrentStage('investigation');
    }
  };

  const handleBackToCompanies = () => {
    setCurrentStage('company_selection');
    setSelectedCompany(null);
    setSelectedPair(null);
    setCommunications([]);
    setIsRunning(false);
    realTimeService.stopSession();
  };

  const handleBackToBills = () => {
    setCurrentStage('bill_selection');
    setSelectedPair(null);
    setCommunications([]);
    setIsRunning(false);
    realTimeService.stopSession();
  };

  const handleRunInvestigation = async () => {
    if (!selectedPair || isRunning) return;

    setIsRunning(true);
    setCommunications([]);

    // Add a starting message to show progress
    safeStateUpdate(
      setCommunications,
      [{
        id: `starting_${Date.now()}`,
        timestamp: new Date().toISOString(),
        agent: 'system',
        type: 'message',
        simplified: 'Starting investigation...',
        fullContent: `🚀 **Investigation Starting**\n\nInitializing connection to AutoGen agents...\nCompany: ${selectedPair.company}\nBill: ${selectedPair.bill}`,
        toolCalls: [],
        results: [],
        status: 'in_progress'
      }],
      (comms: AgentCommunication[]) => Array.isArray(comms) && comms.length > 0
    );

    try {
      await realTimeService.startSession(
        selectedPair.company,
        selectedPair.bill,
        (communication: AgentCommunication) => {
          safeStateUpdate(
            setCommunications,
            (prev: AgentCommunication[]) => {
              try {
                // Validate incoming communication
                if (!communication || !communication.id) {
                  console.warn('Invalid communication received:', communication);
                  return prev;
                }

                // Remove starting message when first real communication arrives
                const filteredPrev = prev.filter(c => !c.id.startsWith('starting_'));

                // Update existing communication if it has the same ID (for status updates)
                const existingIndex = filteredPrev.findIndex(c => c.id === communication.id);
                if (existingIndex >= 0) {
                  const newComms = [...filteredPrev];
                  newComms[existingIndex] = communication;
                  return limitArraySize(newComms, 500); // Prevent memory leaks
                }
                
                const newComms = [...filteredPrev, communication];
                return limitArraySize(newComms, 500); // Prevent memory leaks
              } catch (error) {
                console.error('Error updating communications:', error);
                return prev; // Keep previous state on error
              }
            },
            (newComms: AgentCommunication[]) => Array.isArray(newComms) // Validator
          );
          
          // Check if this is the completion message or service stopped
          try {
            if (communication.simplified?.includes('Investigation complete') || 
                communication.simplified?.includes('Investigation concluded') || 
                !realTimeService.isSessionActive()) {
              safeStateUpdate(setIsRunning, false);
            }
          } catch (error) {
            console.error('Error checking completion status:', error);
          }
        }
      );
    } catch (error) {
      console.error('Failed to start investigation:', error);
      
      // Classify error to determine if it's a real failure or just startup delay
      const errorClassification = classifyError(error);
      const errorMessage = String(error?.message || error || '').toLowerCase();
      
      // Only show error for actual connection failures, not timeouts during normal startup
      if (errorMessage.includes('not connected') || 
          errorMessage.includes('connection') ||
          errorMessage.includes('server') ||
          !realTimeService.isConnected()) {
        
        safeStateUpdate(setIsRunning, false);
        
        // Add safe error communication only for real connection failures
        safeStateUpdate(
          setCommunications,
          [{
            id: `connection_error_${Date.now()}`,
            timestamp: new Date().toISOString(),
            agent: 'system',
            type: 'message',
            simplified: 'Connection failed',
            fullContent: `🚨 **Connection Failed**\n\n${errorClassification.userMessage}\n\n**Technical Details:** ${errorClassification.technicalMessage}\n\n**Suggested Actions:**\n• Ensure the AutoGen server is running\n• Check your internet connection\n• Refresh the page and try again`,
            toolCalls: [],
            results: [],
            status: 'failed'
          }],
          (comms: AgentCommunication[]) => Array.isArray(comms) && comms.length > 0
        );
      } else {
        // For timeout errors, assume investigation is starting and let it continue
        console.log('Investigation start had timeout, but proceeding with connected session');
        // Keep isRunning = true and let the investigation proceed
      }
    }
  };

  const handleStopInvestigation = async () => {
    try {
      await realTimeService.stopSession();
    } catch (error) {
      console.error('Error stopping investigation:', error);
    }
    setIsRunning(false);
  };

  // Connection management
  useEffect(() => {
    const connectToServer = async () => {
      try {
        setConnectionStatus('connecting');
        await realTimeService.connect();
        setConnectionStatus('connected');
      } catch (error) {
        console.error('Failed to connect to AutoGen server:', error);
        setConnectionStatus('error');
      }
    };

    connectToServer();

    return () => {
      realTimeService.disconnect();
    };
  }, [realTimeService]);

  // Stage-based rendering
  if (currentStage === 'company_selection') {
    return <CompanySelection onCompanySelect={handleCompanySelect} />;
  }

  if (currentStage === 'bill_selection' && selectedCompany) {
    return (
      <BillSelector
        companyName={selectedCompany.name}
        companyColor={selectedCompany.primaryColor}
        onBillSelect={handleBillSelect}
        onBack={handleBackToCompanies}
      />
    );
  }

  // Show investigation dashboard once company and bill are selected
  if (currentStage === 'investigation' && selectedCompany && selectedPair) {
    return (
    <div style={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
      padding: '2rem',
      position: 'relative'
    }}>
      {/* Floating Agent Status */}
      <div style={{
        position: 'fixed',
        top: '2rem',
        right: '2rem',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 1rem',
        borderRadius: '12px',
        fontSize: '0.9rem',
        fontWeight: '500',
        background: connectionStatus === 'connected' ? 'rgba(16, 185, 129, 0.95)' : 
                  connectionStatus === 'connecting' ? 'rgba(245, 158, 11, 0.95)' : 
                  'rgba(239, 68, 68, 0.95)',
        color: 'white',
        backdropFilter: 'blur(10px)',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
        border: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: 'white',
          animation: connectionStatus === 'connecting' ? 'pulse 1.5s infinite' : undefined
        }} />
        {connectionStatus === 'connected' ? '🤖 Agents Online' : 
         connectionStatus === 'connecting' ? '🔄 Connecting...' : 
         '⚠️ Agents Offline'}
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Company Header with gradient */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '2rem',
          padding: '2rem',
          background: `linear-gradient(135deg, ${selectedCompany.primaryColor}15, ${selectedCompany.secondaryColor}25)`,
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
          border: `1px solid ${selectedCompany.primaryColor}30`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={handleBackToBills}
              style={{
                background: 'rgba(255,255,255,0.8)',
                border: '1px solid rgba(0,0,0,0.1)',
                color: '#374151',
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.8)';
              }}
            >
              ← Bills
            </button>
            <div style={{ fontSize: '3rem' }}>{selectedCompany.logo}</div>
            <div>
              <h2 style={{ 
                margin: '0 0 0.5rem 0', 
                fontSize: '2rem', 
                fontWeight: '700',
                color: '#1a1a1a'
              }}>
                {selectedCompany.name} Investigation
              </h2>
              <p style={{ 
                margin: 0, 
                color: '#4a5568',
                fontSize: '1.1rem',
                fontWeight: '500'
              }}>
                {selectedPair.description}
              </p>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={isRunning ? handleStopInvestigation : handleRunInvestigation}
              disabled={!selectedPair || connectionStatus !== 'connected'}
              style={{
                padding: '0.75rem 2rem',
                background: isRunning 
                  ? 'linear-gradient(135deg, #dc2626, #ef4444)' 
                  : `linear-gradient(135deg, ${selectedCompany.primaryColor}, ${selectedCompany.secondaryColor})`,
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: (selectedPair && connectionStatus === 'connected') ? 'pointer' : 'not-allowed',
                fontSize: '1rem',
                fontWeight: '600',
                opacity: (selectedPair && connectionStatus === 'connected') ? 1 : 0.5,
                transition: 'all 0.2s ease',
                boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
              }}
            >
              {isRunning ? '⏹️ Stop Investigation' : 
               connectionStatus !== 'connected' ? '⚠️ AutoGen Server Required' :
               '▶️ Run Investigation'}
            </button>
          </div>
        </div>

        <ErrorBoundary fallback={
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            background: '#fff5f5',
            border: '1px solid #dc3545',
            borderRadius: '8px',
            margin: '1rem 0'
          }}>
            <p>⚠️ Communication timeline encountered an error.</p>
            <button onClick={() => window.location.reload()}>Reload Page</button>
          </div>
        }>
          <EnhancedCommunicationTimeline 
            communications={communications}
            isRunning={isRunning}
            billId={selectedCompany?.bill}
            companyName={selectedCompany?.name}
          />
        </ErrorBoundary>
      </div>
      
      {/* Message Debugger */}
      <MessageDebugger 
        isVisible={showDebugger}
        onToggle={() => setShowDebugger(!showDebugger)}
      />
      
    </div>
    );
  }

  // Fallback (should not happen)
  return <CompanySelection onCompanySelect={handleCompanySelect} />;
};

export default AgentInvestigationDashboard;