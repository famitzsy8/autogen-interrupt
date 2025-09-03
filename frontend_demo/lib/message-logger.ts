// Frontend message logger for debugging WebSocket communications

export class MessageLogger {
  private static instance: MessageLogger;
  private logs: Array<{timestamp: string, direction: 'incoming' | 'outgoing', data: any}> = [];
  private maxLogs = 1000;

  static getInstance(): MessageLogger {
    if (!MessageLogger.instance) {
      MessageLogger.instance = new MessageLogger();
    }
    return MessageLogger.instance;
  }

  logIncoming(data: any) {
    this.addLog('incoming', data);
    console.log('🔻 INCOMING from AgentServer:', data);
  }

  logOutgoing(data: any) {
    this.addLog('outgoing', data);
    console.log('🔺 OUTGOING to AgentServer:', data);
  }

  private addLog(direction: 'incoming' | 'outgoing', data: any) {
    this.logs.push({
      timestamp: new Date().toISOString(),
      direction,
      data: JSON.parse(JSON.stringify(data)) // Deep clone
    });

    // Keep only last N logs
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }
  }

  getLogs() {
    return [...this.logs];
  }

  exportLogs() {
    const logString = JSON.stringify(this.logs, null, 2);
    const blob = new Blob([logString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `websocket-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  clearLogs() {
    this.logs = [];
    console.log('🧹 WebSocket logs cleared');
  }

  // Add to window for debugging
  exposeToWindow() {
    (window as any).messageLogger = this;
    console.log('💡 MessageLogger exposed to window.messageLogger');
    console.log('💡 Available commands:');
    console.log('  window.messageLogger.getLogs() - Get all logs');
    console.log('  window.messageLogger.exportLogs() - Download logs as JSON');
    console.log('  window.messageLogger.clearLogs() - Clear logs');
  }
}