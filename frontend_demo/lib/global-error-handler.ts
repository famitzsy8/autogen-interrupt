/**
 * Global error handling for Promise rejections and other uncaught errors
 * This catches errors that React Error Boundaries can't handle
 */

interface ErrorReport {
  timestamp: string;
  type: 'unhandled_rejection' | 'uncaught_error' | 'resource_error';
  message: string;
  stack?: string;
  url?: string;
  line?: number;
  column?: number;
  userAgent: string;
}

class GlobalErrorHandler {
  private errorQueue: ErrorReport[] = [];
  private maxErrors = 100;
  private onError?: (error: ErrorReport) => void;

  constructor() {
    this.setupErrorHandlers();
  }

  private setupErrorHandlers() {
    // Handle unhandled Promise rejections
    if (typeof window !== 'undefined') {
      window.addEventListener('unhandledrejection', (event) => {
        const error = this.createErrorReport(
          'unhandled_rejection',
          event.reason?.message || String(event.reason),
          event.reason?.stack
        );
        
        this.handleError(error);
        
        // Prevent the error from being logged to console
        event.preventDefault();
      });

      // Handle uncaught JavaScript errors
      window.addEventListener('error', (event) => {
        const error = this.createErrorReport(
          'uncaught_error',
          event.message,
          event.error?.stack,
          event.filename,
          event.lineno,
          event.colno
        );
        
        this.handleError(error);
      });

      // Handle resource loading errors (images, scripts, etc.)
      window.addEventListener('error', (event) => {
        if (event.target !== window) {
          const target = event.target as HTMLElement;
          const error = this.createErrorReport(
            'resource_error',
            `Failed to load resource: ${target.tagName}`,
            undefined,
            (target as any).src || (target as any).href
          );
          
          this.handleError(error);
        }
      }, true);
    }
  }

  private createErrorReport(
    type: ErrorReport['type'],
    message: string,
    stack?: string,
    url?: string,
    line?: number,
    column?: number
  ): ErrorReport {
    return {
      timestamp: new Date().toISOString(),
      type,
      message: message || 'Unknown error',
      stack,
      url,
      line,
      column,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown'
    };
  }

  private handleError(error: ErrorReport) {
    // Add to queue
    this.errorQueue.push(error);
    if (this.errorQueue.length > this.maxErrors) {
      this.errorQueue.shift();
    }

    // Log to console (but in a controlled way)
    console.group('🚨 Global Error Caught');
    console.error('Type:', error.type);
    console.error('Message:', error.message);
    if (error.stack) {
      console.error('Stack:', error.stack);
    }
    if (error.url) {
      console.error('URL:', error.url);
    }
    console.groupEnd();

    // Call custom error handler if provided
    if (this.onError) {
      try {
        this.onError(error);
      } catch (handlerError) {
        console.error('Error in custom error handler:', handlerError);
      }
    }

    // Show user-friendly notification for critical errors
    this.showUserNotification(error);
  }

  private showUserNotification(error: ErrorReport) {
    // Only show notifications for certain types of errors
    if (error.type === 'unhandled_rejection' && 
        (error.message.includes('429') || 
         error.message.includes('rate limit') ||
         error.message.includes('WebSocket') ||
         error.message.includes('investigation'))) {
      
      this.showErrorToast(this.getUserFriendlyMessage(error));
    }
  }

  private getUserFriendlyMessage(error: ErrorReport): string {
    const message = error.message.toLowerCase();
    
    if (message.includes('429') || message.includes('rate limit')) {
      return '⚠️ Service temporarily overloaded. Please wait a moment and try again.';
    }
    
    if (message.includes('websocket') || message.includes('connection')) {
      return '🔌 Connection lost. Attempting to reconnect...';
    }
    
    if (message.includes('investigation')) {
      return '🔍 Investigation encountered an issue. You can try starting a new investigation.';
    }
    
    return '⚠️ An unexpected error occurred. The page may need to be refreshed.';
  }

  private showErrorToast(message: string) {
    // Create a simple toast notification
    if (typeof document !== 'undefined') {
      const existingToast = document.getElementById('global-error-toast');
      if (existingToast) {
        existingToast.remove();
      }

      const toast = document.createElement('div');
      toast.id = 'global-error-toast';
      toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #dc3545;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 300px;
        font-family: system-ui, sans-serif;
        font-size: 14px;
        animation: slideIn 0.3s ease-out;
      `;
      
      // Add animation
      const style = document.createElement('style');
      style.textContent = `
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `;
      document.head.appendChild(style);
      
      toast.textContent = message;
      
      // Add close button
      const closeBtn = document.createElement('button');
      closeBtn.textContent = '×';
      closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        font-size: 18px;
        float: right;
        margin-left: 10px;
        cursor: pointer;
        line-height: 1;
      `;
      closeBtn.onclick = () => toast.remove();
      
      toast.appendChild(closeBtn);
      document.body.appendChild(toast);
      
      // Auto-remove after 5 seconds
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 5000);
    }
  }

  // Public methods
  public setErrorHandler(handler: (error: ErrorReport) => void) {
    this.onError = handler;
  }

  public getRecentErrors(count = 10): ErrorReport[] {
    return this.errorQueue.slice(-count);
  }

  public clearErrors() {
    this.errorQueue = [];
  }

  public getErrorStats() {
    const stats = {
      total: this.errorQueue.length,
      unhandled_rejections: 0,
      uncaught_errors: 0,
      resource_errors: 0
    };

    this.errorQueue.forEach(error => {
      stats[error.type]++;
    });

    return stats;
  }
}

// Create global instance
const globalErrorHandler = new GlobalErrorHandler();

// Export for use in other modules
export default globalErrorHandler;

// Auto-setup on import
if (typeof window !== 'undefined') {
  console.log('🛡️ Global error handler initialized');
}