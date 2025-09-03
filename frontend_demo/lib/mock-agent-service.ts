import { AgentCommunication } from './llm-processor';

const AGENT_NAMES = [
  'orchestrator',
  'committee_specialist', 
  'bill_specialist',
  'actions_specialist',
  'amendment_specialist',
  'congress_member_specialist'
];

const MOCK_MESSAGES = [
  {
    agent: 'orchestrator',
    content: 'Initiating investigation of {company} lobbying activities for bill {bill}. Coordinating specialist agents.',
    type: 'message' as const
  },
  {
    agent: 'bill_specialist',
    content: 'Analyzing bill {bill} structure and key provisions. Identifying sections relevant to {company} interests.',
    type: 'message' as const
  },
  {
    agent: 'bill_specialist',
    content: 'Calling getBillSponsors to identify primary sponsors',
    type: 'tool_call' as const
  },
  {
    agent: 'committee_specialist',
    content: 'Examining committee assignments for {bill}. Investigating {company} connections to committee members.',
    type: 'message' as const
  },
  {
    agent: 'committee_specialist',
    content: 'Retrieved committee membership data. Found 3 potential connection points.',
    type: 'reflection' as const
  },
  {
    agent: 'actions_specialist',
    content: 'Tracking legislative actions and timeline for {bill}. Cross-referencing with {company} lobbying disclosures.',
    type: 'message' as const
  },
  {
    agent: 'congress_member_specialist',
    content: 'Investigating voting patterns and statements from key congress members regarding {company}.',
    type: 'message' as const
  },
  {
    agent: 'amendment_specialist',
    content: 'Analyzing proposed amendments to {bill}. Checking for {company}-favorable modifications.',
    type: 'message' as const
  },
  {
    agent: 'bill_specialist',
    content: 'Identified 5 bill sections with potential {company} impact. Handing off to committee specialist for deeper analysis.',
    type: 'handoff' as const
  },
  {
    agent: 'committee_specialist',
    content: 'Cross-referencing {company} campaign contributions with committee member voting records.',
    type: 'message' as const
  },
  {
    agent: 'actions_specialist',
    content: 'Timeline analysis complete. Found suspicious timing patterns between {company} lobbying and bill modifications.',
    type: 'reflection' as const
  },
  {
    agent: 'orchestrator',
    content: 'Compiling findings from all specialists. Preparing comprehensive lobbying influence report.',
    type: 'message' as const
  }
];

export class MockAgentService {
  private eventCallback: ((communication: AgentCommunication) => void) | null = null;
  private intervalId: NodeJS.Timeout | null = null;
  private messageIndex = 0;
  private sessionId = '';

  startSession(company: string, bill: string, onCommunication: (communication: AgentCommunication) => void) {
    this.eventCallback = onCommunication;
    this.messageIndex = 0;
    this.sessionId = `session_${Date.now()}`;
    
    // Send initial message immediately
    this.sendNextMessage(company, bill);
    
    // Continue sending messages every 5 seconds
    this.intervalId = setInterval(() => {
      this.sendNextMessage(company, bill);
    }, 5000);
  }

  stopSession() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.eventCallback = null;
  }

  private sendNextMessage(company: string, bill: string) {
    if (!this.eventCallback || this.messageIndex >= MOCK_MESSAGES.length) {
      // Session complete
      if (this.eventCallback) {
        this.eventCallback({
          id: `${this.sessionId}_complete`,
          timestamp: new Date().toISOString(),
          agent: 'orchestrator',
          type: 'message',
          simplified: 'Investigation complete. All findings have been compiled and analyzed.',
          status: 'completed'
        });
      }
      this.stopSession();
      return;
    }

    const mockMessage = MOCK_MESSAGES[this.messageIndex];
    const communication: AgentCommunication = {
      id: `${this.sessionId}_${this.messageIndex}`,
      timestamp: new Date().toISOString(),
      agent: mockMessage.agent,
      type: mockMessage.type,
      simplified: mockMessage.content
        .replace(/{company}/g, company)
        .replace(/{bill}/g, bill),
      status: 'completed'
    };

    this.eventCallback(communication);
    this.messageIndex++;
  }

  isSessionActive(): boolean {
    return this.intervalId !== null;
  }
}