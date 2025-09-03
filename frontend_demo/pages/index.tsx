import { NextPage } from 'next'
import AgentInvestigationDashboard from '../components/AgentInvestigationDashboard'
import ErrorBoundary from '../components/ErrorBoundary'
import globalErrorHandler from '../lib/global-error-handler'
import { MessageLogger } from '../lib/message-logger'

// Initialize global error handling and message logging
if (typeof window !== 'undefined') {
  globalErrorHandler.setErrorHandler((error) => {
    // Could send to error tracking service here
    console.log('Global error captured:', error);
  });
  
  // Expose message logger for debugging
  const logger = MessageLogger.getInstance();
  logger.exposeToWindow();
}

const Home: NextPage = () => {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Log critical application errors
        console.group('🚨 Critical Application Error');
        console.error('Error:', error);
        console.error('Error Info:', errorInfo);
        console.error('User Agent:', navigator.userAgent);
        console.error('Timestamp:', new Date().toISOString());
        console.groupEnd();
        
        // Could send to error tracking service here
        // e.g., Sentry, LogRocket, etc.
      }}
    >
      <div>
        <AgentInvestigationDashboard />
      </div>
    </ErrorBoundary>
  )
}

export default Home