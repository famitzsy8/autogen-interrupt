import { AgentCommunication } from './llm-processor';
import { MessageLogger } from './message-logger';

export interface WebSocketMessage {
  type: 'agent_communication' | 'tool_call_start' | 'tool_call_result' | 'investigation_complete' | 'investigation_concluded' | 'investigation_started' | 'investigation_stopped' | 'connection_established' | 'investigation_error' | 'error';
  sessionId?: string;
  timestamp: string;
  data?: any;
  message?: string;
  error?: string;
}

export interface InvestigationStartRequest {
  type: 'start_investigation';
  sessionId: string;
  company: string;
  bill: string;
}

export interface InvestigationStopRequest {
  type: 'stop_investigation';
  sessionId: string;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  private messageHandlers: Map<string, (message: WebSocketMessage) => void> = new Map();
  private sessionId: string | null = null;
  private logger = MessageLogger.getInstance();
  private isManualClose = false;

  constructor(private url: string = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8766') {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.isManualClose = false;
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected to AutoGen server');
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          // Safe JSON parsing with validation
          if (!event.data || typeof event.data !== 'string') {
            console.warn('Invalid WebSocket message format:', event.data);
            return;
          }

          // DETAILED LOGGING - Log raw data from agentServer
          console.log('🔥 RAW WebSocket Data from AgentServer:', {
            rawData: event.data,
            messageSize: event.data.length,
            timestamp: new Date().toISOString()
          });

          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Log incoming message
          this.logger.logIncoming(message);
          
          // DETAILED LOGGING - Log parsed message  
          console.log('📋 PARSED WebSocket Message:', {
            type: message.type,
            sessionId: message.sessionId,
            hasData: !!message.data,
            dataType: typeof message.data,
            dataPreview: message.data ? JSON.stringify(message.data).substring(0, 200) + '...' : null,
            fullMessage: message
          });
          
          // Validate message structure
          if (!message || typeof message !== 'object') {
            console.warn('WebSocket message is not an object:', message);
            return;
          }

          if (!message.type || typeof message.type !== 'string') {
            console.warn('WebSocket message missing type field:', message);
            return;
          }

          if (!message.timestamp || typeof message.timestamp !== 'string') {
            console.warn('WebSocket message missing timestamp field:', message);
            return;
          }

          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          console.error('Raw event data:', event.data);
          
          // Send synthetic error message to handlers
          this.handleMessage({
            type: 'error',
            timestamp: new Date().toISOString(),
            message: 'Failed to parse WebSocket message',
            error: String(error)
          });
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          setTimeout(() => {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            this.connect().catch(console.error);
          }, this.reconnectInterval * this.reconnectAttempts);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
    });
  }

  disconnect(): void {
    this.isManualClose = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    console.log('Received WebSocket message:', message);

    // Call registered handlers with enhanced error protection
    this.messageHandlers.forEach((handler, id) => {
      try {
        handler(message);
      } catch (error) {
        console.error(`Error in message handler "${id}":`, error);
        console.error('Message that caused error:', message);
        
        // Remove problematic handler to prevent future crashes
        console.warn(`Removing faulty message handler "${id}" to prevent further crashes`);
        this.messageHandlers.delete(id);
      }
    });
  }

  onMessage(id: string, handler: (message: WebSocketMessage) => void): void {
    this.messageHandlers.set(id, handler);
  }

  offMessage(id: string): void {
    this.messageHandlers.delete(id);
  }

  startInvestigation(company: string, bill: string, description: string): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      const request: InvestigationStartRequest = {
        type: 'start_investigation',
        sessionId: this.sessionId,
        company,
        bill
      };

      // Set up one-time handler for investigation start confirmation
      const handleStart = (message: WebSocketMessage) => {
        // Accept multiple message types as confirmation that investigation started
        if ((message.type === 'investigation_started' || 
             message.type === 'agent_communication' ||
             message.type === 'tool_call_start') && 
            message.sessionId === this.sessionId) {
          this.offMessage('start_handler');
          resolve(this.sessionId!);
        } else if (message.type === 'investigation_error') {
          this.offMessage('start_handler');
          reject(new Error(message.error || message.message || 'Investigation failed to start'));
        } else if (message.type === 'error' && message.message?.includes('investigation')) {
          this.offMessage('start_handler');
          reject(new Error(message.message || 'Unknown error'));
        }
      };

      this.onMessage('start_handler', handleStart);

      // Send the start request
      this.logger.logOutgoing(request);
      this.ws.send(JSON.stringify(request));

      // More generous timeout (30 seconds) and better success detection
      setTimeout(() => {
        this.offMessage('start_handler');
        
        // Don't immediately fail - check if we're getting communications
        if (this.sessionId && this.ws && this.ws.readyState === WebSocket.OPEN) {
          console.log('Investigation start timeout, but connection is active. Assuming success.');
          resolve(this.sessionId!);
        } else {
          reject(new Error('Investigation start timeout - no server response'));
        }
      }, 30000);
    });
  }

  stopInvestigation(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      if (!this.sessionId) {
        reject(new Error('No active investigation'));
        return;
      }

      const request: InvestigationStopRequest = {
        type: 'stop_investigation',
        sessionId: this.sessionId
      };

      // Set up one-time handler for investigation stop confirmation
      const handleStop = (message: WebSocketMessage) => {
        if (message.type === 'investigation_stopped' && message.sessionId === this.sessionId) {
          this.offMessage('stop_handler');
          this.sessionId = null;
          resolve();
        } else if (message.type === 'error') {
          this.offMessage('stop_handler');
          reject(new Error(message.message || 'Unknown error'));
        }
      };

      this.onMessage('stop_handler', handleStop);

      // Send the stop request
      this.logger.logOutgoing(request);
      this.ws.send(JSON.stringify(request));

      // Timeout after 5 seconds
      setTimeout(() => {
        this.offMessage('stop_handler');
        reject(new Error('Investigation stop timeout'));
      }, 5000);
    });
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getCurrentSessionId(): string | null {
    return this.sessionId;
  }
}

// Transform WebSocket data to AgentCommunication format
export function transformWebSocketToAgentCommunication(message: WebSocketMessage): AgentCommunication | null {
  if (message.type !== 'agent_communication' || !message.data) {
    return null;
  }

  const data = message.data;
  return {
    id: data.id || `comm_${Date.now()}`,
    timestamp: message.timestamp,
    agent: data.agent || 'unknown',
    type: data.type || 'message',
    simplified: data.simplified || data.fullContent?.substring(0, 200) + '...' || 'Communication received',
    fullContent: data.fullContent || data.simplified || 'No content available',
    toolCalls: data.toolCalls || [],
    results: data.results || [],
    status: data.status || 'completed'
  };
}