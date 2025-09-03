import { AgentCommunication } from './llm-processor';
import { WebSocketService, WebSocketMessage, transformWebSocketToAgentCommunication } from './websocket-service';
import { safeStateUpdate, validateWebSocketMessage, classifyError, safeAsyncOperation, limitArraySize } from './safe-operations';
import { parseCongressTable, ParsedTable } from './table-parser';

export class RealTimeService {
  private websocketService: WebSocketService;
  private sessionActive = false;
  private currentSessionId: string | null = null;
  private communicationCallback: ((communication: AgentCommunication) => void) | null = null;

  constructor() {
    this.websocketService = new WebSocketService();
    this.setupMessageHandlers();
  }

  private setupMessageHandlers(): void {
    this.websocketService.onMessage('realtime_service', (message: WebSocketMessage) => {
      this.handleWebSocketMessage(message);
    });
  }

  private handleWebSocketMessage(message: WebSocketMessage): void {
    try {
      // Validate message before processing
      if (!validateWebSocketMessage(message)) {
        console.warn('Invalid WebSocket message received:', message);
        return;
      }

      console.log('RealTimeService received message:', message);
      
      // Add debug event for WebSocket receipt
      if ((window as any).addCommunicationDebugEvent) {
        (window as any).addCommunicationDebugEvent(
          'websocket_received',
          message,
          `Type: ${message.type}, Source: WebSocket`
        );
      }

      switch (message.type) {
        case 'agent_communication':
          this.handleAgentCommunication(message);
          break;
        case 'tool_call_start':
          this.handleToolCallStart(message);
          break;
        case 'tool_call_result':
          this.handleToolCallResult(message);
          break;
        case 'investigation_complete':
          this.handleInvestigationComplete(message);
          break;
        case 'investigation_concluded':
          this.handleInvestigationConcluded(message);
          break;
        case 'investigation_error':
          this.handleInvestigationError(message);
          break;
        case 'connection_established':
          console.log('Connected to AutoGen server');
          break;
        case 'error':
          console.error('WebSocket error:', message.message);
          this.handleWebSocketError(message);
          break;
        default:
          console.log('Unhandled message type:', message.type);
      }
    } catch (error) {
      console.error('Critical error in WebSocket message handler:', error);
      console.error('Problematic message:', message);
      
      // Create a safe error communication to show in UI
      if (this.communicationCallback) {
        const errorClassification = classifyError(error);
        this.communicationCallback({
          id: `critical_error_${Date.now()}`,
          timestamp: new Date().toISOString(),
          agent: 'system',
          type: 'message',
          simplified: 'Critical system error occurred',
          fullContent: `🚨 **Critical Error**\n\n${errorClassification.userMessage}\n\n**Technical Details:** ${errorClassification.technicalMessage}`,
          toolCalls: [],
          results: [],
          status: 'failed'
        });
      }
    }
  }

  private handleAgentCommunication(message: WebSocketMessage): void {
    const communication = transformWebSocketToAgentCommunication(message);
    if (communication && this.communicationCallback) {
      // Add debug event for processing
      if ((window as any).addCommunicationDebugEvent) {
        (window as any).addCommunicationDebugEvent(
          'realtime_processed',
          communication,
          `Agent: ${communication.agent}, Type: ${communication.type}, Status: ${communication.status}`
        );
      }
      
      // Check if this message contains a congress table
      this.checkForTableContent(communication);
      
      this.communicationCallback(communication);
    }
  }

  private checkForTableContent(communication: AgentCommunication): void {
    try {
      // Check both simplified and fullContent for table data
      const contentToCheck = communication.fullContent || communication.simplified || '';
      
      // Parse table if present
      const parsedTable = parseCongressTable(contentToCheck);
      
      if (parsedTable && parsedTable.members.length > 0) {
        console.log(`🏛️ Congress table detected! ${parsedTable.members.length} members found`);
        
        // Add table data directly to the existing communication instead of creating a new one
        communication.tableData = parsedTable;
        communication.type = 'table_results'; // Mark this communication as containing table results
        
        // Enhance the content with formatted results
        communication.fullContent = this.formatTableResults(parsedTable);
        communication.simplified = `Congress Investigation Results - ${parsedTable.members.length} members analyzed`;
        communication.status = 'completed';
      }
    } catch (error) {
      console.warn('Error checking for table content:', error);
    }
  }

  private formatTableResults(parsedTable: ParsedTable): string {
    let formatted = `🏛️ **Congress Member Investigation Results**\n\n`;
    
    if (parsedTable.billId) {
      formatted += `**Bill:** ${parsedTable.billId}\n`;
    }
    
    formatted += `**Total Members Analyzed:** ${parsedTable.totalMembers}\n`;
    formatted += `**Investigation Status:** ${parsedTable.investigationComplete ? 'Complete' : 'In Progress'}\n\n`;
    
    formatted += `**Top 10 Most Involved Members:**\n\n`;
    
    // Sort by rank and show top 10
    const topMembers = parsedTable.members
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 10);
    
    topMembers.forEach(member => {
      const partyInfo = member.party ? `${member.party}, ` : '';
      const stateDistrict = member.district ? `${member.state}-${member.district}` : member.state;
      formatted += `**${member.rank}. ${member.name}** (${partyInfo}${stateDistrict}) - ${member.chamber}\n`;
      formatted += `${member.reason.substring(0, 200)}${member.reason.length > 200 ? '...' : ''}\n\n`;
    });
    
    formatted += `\n*Full table data available in investigation results.*`;
    
    return formatted;
  }

  private handleToolCallStart(message: WebSocketMessage): void {
    if (!message.data || !this.communicationCallback) return;

    // Create a communication for tool call start
    const communication: AgentCommunication = {
      id: `tool_start_${message.data.id || Date.now()}`,
      timestamp: message.timestamp,
      agent: message.data.agent || 'unknown',
      type: 'tool_call',
      simplified: `Executing tool: ${message.data.name}`,
      fullContent: `Tool call started: ${message.data.name}\nArguments: ${JSON.stringify(message.data.arguments, null, 2)}`,
      toolCalls: [{
        id: message.data.id || 'unknown',
        name: message.data.name || 'unknown_tool',
        arguments: message.data.arguments || {}
      }],
      results: [],
      status: 'in_progress'
    };

    // Add debug event for tool call processing
    if ((window as any).addCommunicationDebugEvent) {
      (window as any).addCommunicationDebugEvent(
        'realtime_processed',
        communication,
        `Tool Call Start: ${message.data.name} by ${communication.agent}`
      );
    }

    this.communicationCallback(communication);
  }

  private handleToolCallResult(message: WebSocketMessage): void {
    if (!message.data || !this.communicationCallback) return;

    // Use enhanced summary and details from LLM parsing
    const summary = message.data.summary || `Tool ${message.data.name} ${message.data.success ? 'completed' : 'failed'}`;
    const details = message.data.details || {};
    
    // Create enhanced tool call result display
    let fullContent = `Tool call result: ${message.data.name}\n`;
    fullContent += `Status: ${message.data.success ? 'Success' : 'Failed'}\n`;
    fullContent += `Summary: ${summary}\n\n`;
    
    if (details.key_findings && details.key_findings.length > 0) {
      fullContent += `Key Findings:\n${details.key_findings.map(f => `• ${f}`).join('\n')}\n\n`;
    }
    
    if (details.data_points) {
      fullContent += `Data Points Found: ${details.data_points}\n\n`;
    }
    
    fullContent += `Raw Result:\n${JSON.stringify(message.data.result, null, 2)}`;

    // Create enhanced communication for tool call result
    const communication: AgentCommunication = {
      id: `tool_result_${message.data.id || Date.now()}`,
      timestamp: message.timestamp,
      agent: message.data.agent || 'unknown',
      type: 'tool_call',
      simplified: summary,
      fullContent: fullContent,
      toolCalls: [],
      results: [{
        call_id: message.data.id || 'unknown',
        content: message.data.result,
        is_error: !message.data.success
      }],
      status: message.data.success ? 'completed' : 'failed'
    };

    this.communicationCallback(communication);
  }

  private handleInvestigationComplete(message: WebSocketMessage): void {
    console.log('Investigation completed:', message.data);
    this.sessionActive = false;
    
    if (this.communicationCallback) {
      // Create a final communication
      const communication: AgentCommunication = {
        id: `final_${Date.now()}`,
        timestamp: message.timestamp,
        agent: 'orchestrator',
        type: 'message',
        simplified: 'Investigation completed successfully',
        fullContent: JSON.stringify(message.data || { status: 'completed' }, null, 2),
        toolCalls: [],
        results: [],
        status: 'completed'
      };

      this.communicationCallback(communication);
    }
  }

  private handleInvestigationConcluded(message: WebSocketMessage): void {
    console.log('Investigation concluded:', message.data);
    this.sessionActive = false;
    
    if (this.communicationCallback) {
      const data = message.data || {};
      const tableStatus = data.table_available ? 'Table available' : 'No table found';
      
      // If we have table data, create a special table communication
      if (data.table_available && data.table_data) {
        const tableComm: AgentCommunication = {
          id: `final_table_${Date.now()}`,
          timestamp: message.timestamp,
          agent: 'orchestrator',
          type: 'table_results',
          simplified: `Investigation Results - ${data.table_data.members?.length || 0} members analyzed`,
          fullContent: JSON.stringify(data.table_data),
          toolCalls: [],
          results: [],
          status: 'completed'
        };
        this.communicationCallback(tableComm);
      }
      
      // Create a conclusion communication
      const communication: AgentCommunication = {
        id: `conclusion_${Date.now()}`,
        timestamp: message.timestamp,
        agent: 'orchestrator',
        type: 'message',
        simplified: `Investigation concluded - ${tableStatus}`,
        fullContent: `${data.conclusion_message || 'Investigation completed successfully'}\n\nTable Status: ${data.table_status || tableStatus}\nConcluded by: ${data.agent || 'Unknown agent'}`,
        toolCalls: [],
        results: [],
        status: 'completed'
      };

      this.communicationCallback(communication);
    }
  }

  private handleWebSocketError(message: WebSocketMessage): void {
    if (this.communicationCallback) {
      const communication: AgentCommunication = {
        id: `ws_error_${Date.now()}`,
        timestamp: message.timestamp,
        agent: 'orchestrator',
        type: 'message',
        simplified: 'Connection error occurred',
        fullContent: `⚠️ **Connection Error**\n\nThere was a problem with the connection to the investigation server.\n\n**Error:** ${message.message || 'Unknown connection error'}\n\n**What you can do:**\n• Check your internet connection\n• Refresh the page to reconnect\n• Try again in a few moments`,
        toolCalls: [],
        results: [],
        status: 'failed'
      };

      this.communicationCallback(communication);
    }
  }

  private handleInvestigationError(message: WebSocketMessage): void {
    console.error('Investigation error:', message.error);
    this.sessionActive = false;
    
    if (this.communicationCallback) {
      // Check if this is an OpenAI API rate limit error
      const errorMessage = message.error || 'Unknown error occurred';
      const isRateLimitError = errorMessage.includes('429') || 
                               errorMessage.includes('Too Many Requests') ||
                               errorMessage.includes('rate limit') ||
                               errorMessage.includes('Retrying request');
      
      let simplifiedMessage = 'Investigation encountered an error';
      let userFriendlyContent = `Error: ${errorMessage}`;
      
      if (isRateLimitError) {
        simplifiedMessage = 'OpenAI API is temporarily overloaded';
        userFriendlyContent = `🚫 **OpenAI API Rate Limit Exceeded**\n\nThe OpenAI API is currently overloaded and cannot process your request at the moment.\n\n**What happened?**\nToo many requests are being sent to OpenAI's servers right now.\n\n**What you can do:**\n• Wait a few minutes and try again\n• The system will automatically retry failed requests\n• Consider trying again during off-peak hours\n\n**Technical details:**\n${errorMessage}`;
      }
      
      const communication: AgentCommunication = {
        id: `error_${Date.now()}`,
        timestamp: message.timestamp,
        agent: 'orchestrator',
        type: 'message',
        simplified: simplifiedMessage,
        fullContent: userFriendlyContent,
        toolCalls: [],
        results: [],
        status: 'failed'
      };

      this.communicationCallback(communication);
    }
  }

  async connect(): Promise<void> {
    try {
      await this.websocketService.connect();
      console.log('RealTimeService connected to WebSocket server');
    } catch (error) {
      console.error('Failed to connect to WebSocket server:', error);
      throw new Error('Unable to connect to AutoGen server. Please ensure the server is running.');
    }
  }

  disconnect(): void {
    this.websocketService.disconnect();
    this.sessionActive = false;
    this.currentSessionId = null;
  }

  async startSession(
    company: string,
    bill: string,
    callback: (communication: AgentCommunication) => void
  ): Promise<void> {
    if (this.sessionActive) {
      throw new Error('Investigation session is already active');
    }

    if (!this.websocketService.isConnected()) {
      await this.connect();
    }

    this.communicationCallback = callback;

    try {
      this.currentSessionId = await this.websocketService.startInvestigation(
        company,
        bill,
        `Investigation of ${company} lobbying activities for bill ${bill}`
      );
      
      this.sessionActive = true;
      console.log(`Started investigation session: ${this.currentSessionId}`);
      
    } catch (error) {
      console.error('Failed to start investigation:', error);
      this.communicationCallback = null;
      throw error;
    }
  }

  async stopSession(): Promise<void> {
    if (!this.sessionActive) {
      return;
    }

    try {
      await this.websocketService.stopInvestigation();
      console.log('Investigation session stopped');
    } catch (error) {
      console.error('Error stopping investigation:', error);
    } finally {
      this.sessionActive = false;
      this.currentSessionId = null;
      this.communicationCallback = null;
    }
  }

  isSessionActive(): boolean {
    return this.sessionActive;
  }

  getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }

  isConnected(): boolean {
    return this.websocketService.isConnected();
  }
}