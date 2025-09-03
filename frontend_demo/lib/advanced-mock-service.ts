import { AgentCommunication } from './llm-processor';
import agentCommunications from '../data/agent-communications.json';
import toolCalls from '../data/tool-calls.json';
import toolSummaries from '../data/tool-summaries.json';
import finalResults from '../data/final-table.json';

export class AdvancedMockService {
  private eventCallback: ((communication: AgentCommunication) => void) | null = null;
  private timeoutIds: NodeJS.Timeout[] = [];
  private currentStep = 0;
  private sessionId = '';
  private isActive = false;

  // Timing configuration: communication -> tool_call (2s) -> results_obtained (3s) -> next communication (2s)
  private readonly COMMUNICATION_TO_TOOL_DELAY = 2000; // 2 seconds
  private readonly TOOL_TO_RESULTS_DELAY = 3000; // 3 seconds  
  private readonly RESULTS_TO_NEXT_DELAY = 2000; // 2 seconds

  startSession(company: string, bill: string, onCommunication: (communication: AgentCommunication) => void) {
    this.eventCallback = onCommunication;
    this.currentStep = 0;
    this.sessionId = `session_${Date.now()}`;
    this.isActive = true;
    this.timeoutIds = [];

    // Start the presentation flow
    this.presentNextStep(company, bill);
  }

  stopSession() {
    this.isActive = false;
    this.timeoutIds.forEach(id => clearTimeout(id));
    this.timeoutIds = [];
    this.eventCallback = null;
  }

  private presentNextStep(company: string, bill: string) {
    if (!this.isActive || !this.eventCallback) return;

    const communicationIndex = Math.floor(this.currentStep / 2);
    const toolIndex = Math.floor(this.currentStep / 2);

    // Check if we've completed all communications and tool calls
    if (communicationIndex >= agentCommunications.length && toolIndex >= toolCalls.length) {
      this.presentFinalResults(company, bill);
      return;
    }

    const isToolCallStep = this.currentStep % 2 === 1;

    if (isToolCallStep && toolIndex < toolCalls.length) {
      // Present tool call
      this.presentToolCall(company, bill, toolIndex);
    } else if (!isToolCallStep && communicationIndex < agentCommunications.length) {
      // Present communication
      this.presentCommunication(company, bill, communicationIndex);
    } else {
      // Skip if one type is exhausted
      this.currentStep++;
      this.scheduleNextStep(company, bill, this.RESULTS_TO_NEXT_DELAY);
    }
  }

  private presentCommunication(company: string, bill: string, index: number) {
    if (!this.eventCallback || !this.isActive) return;

    const comm = agentCommunications[index];
    const communication: AgentCommunication = {
      id: `${this.sessionId}_comm_${index}`,
      timestamp: new Date().toISOString(),
      agent: comm.agent,
      type: 'message',
      simplified: comm.simplified.replace(/{company}/g, company).replace(/{bill}/g, bill),
      fullContent: comm.fullContent?.replace(/{company}/g, company).replace(/{bill}/g, bill),
      status: 'completed'
    };

    this.eventCallback(communication);
    this.currentStep++;

    // Schedule tool call after 2 seconds
    this.scheduleNextStep(company, bill, this.COMMUNICATION_TO_TOOL_DELAY);
  }

  private presentToolCall(company: string, bill: string, index: number) {
    if (!this.eventCallback || !this.isActive) return;

    const toolCall = toolCalls[index];
    const communication: AgentCommunication = {
      id: `${this.sessionId}_tool_${index}`,
      timestamp: new Date().toISOString(),
      agent: toolCall.agent,
      type: 'tool_call',
      simplified: toolCall.simplified.replace(/{company}/g, company).replace(/{bill}/g, bill),
      toolCalls: toolCall.toolCalls,
      status: 'in_progress'
    };

    this.eventCallback(communication);

    // After 3 seconds, mark as completed with results
    const resultsTimeout = setTimeout(() => {
      if (!this.isActive || !this.eventCallback) return;

      const completedCommunication: AgentCommunication = {
        ...communication,
        status: 'completed',
        results: toolCall.results
      };

      this.eventCallback(completedCommunication);
      this.currentStep++;

      // Schedule next communication after 2 more seconds
      this.scheduleNextStep(company, bill, this.RESULTS_TO_NEXT_DELAY);
    }, this.TOOL_TO_RESULTS_DELAY);

    this.timeoutIds.push(resultsTimeout);
  }

  private scheduleNextStep(company: string, bill: string, delay: number) {
    if (!this.isActive) return;

    const timeout = setTimeout(() => {
      this.presentNextStep(company, bill);
    }, delay);

    this.timeoutIds.push(timeout);
  }

  private presentFinalResults(company: string, bill: string) {
    if (!this.eventCallback || !this.isActive) return;

    const finalCommunication: AgentCommunication = {
      id: `${this.sessionId}_final`,
      timestamp: new Date().toISOString(),
      agent: 'orchestrator',
      type: 'message',
      simplified: `Investigation complete. Comprehensive analysis of ${company} lobbying activities for ${bill} has been compiled.`,
      fullContent: `Investigation Summary:\n\nThe multi-agent investigation into ${company}'s lobbying activities regarding ${bill} has been completed. All specialists have provided detailed analysis covering:\n\n- Bill structure and relevant provisions\n- Committee assignments and member profiles\n- Legislative timeline and procedural actions\n- Amendment analysis and modifications\n- Congressional member voting patterns and industry connections\n\nA comprehensive ranking table of all Congressional members by their involvement in the bill's advancement has been generated, providing detailed insights into the lobbying influence patterns.`,
      status: 'completed'
    };

    this.eventCallback(finalCommunication);

    // Present final table after 3 seconds
    setTimeout(() => {
      if (!this.eventCallback || !this.isActive) return;

      const finalTable: AgentCommunication = {
        id: `${this.sessionId}_final_table`,
        timestamp: new Date().toISOString(),
        agent: 'orchestrator',
        type: 'message',
        simplified: '📊 Final Investigation Results Table',
        fullContent: JSON.stringify(finalResults),
        status: 'completed'
      };

      this.eventCallback(finalTable);
      
      // Stop the session after final table
      setTimeout(() => {
        this.stopSession();
      }, 1000);
    }, 3000);
  }

  isSessionActive(): boolean {
    return this.isActive;
  }
}