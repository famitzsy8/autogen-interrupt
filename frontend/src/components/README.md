# Components

This directory contains all React components for the frontend application. Components are organized by function: initialization, execution control, user interaction, and status display.


## Subdirectories

- `TreeVisualization/`: D3-based conversation tree visualization with swimlane layout
- `StateDisplay/`: Components for displaying agent and conversation state


## Initialization Components

### Config Form (`ConfigForm.tsx`)
Primary entry point - multi-stage walkthrough for initializing agent runs. Three stages: agent selection, task/company-bill selection, and analysis watchlist configuration. Supports template variable substitution and integrates with ComponentReviewModal for AI-generated analysis criteria.

### Component Review Modal (`ComponentReviewModal.tsx`)
Modal for reviewing and editing AI-generated analysis watchlist components. Allows editing labels/descriptions, removing components, and adding custom criteria before run start.


## Execution Control

### Control Bar (`ControlBar.tsx`)
Fixed bottom bar for user interaction during agent execution. Renders only when streaming or interrupted, contains UserInput component.

### Interrupt Button (`InterruptButton.tsx`)
Orange button with stop icon to pause streaming agent output. Shows only while streaming is active.

### Terminate Button (`TerminateButton.tsx`)
Red button to end agent run completely. Different from interrupt (ends run vs pauses).


## User Interaction

### User Input (`UserInput.tsx`)
Bottom-bar input component for sending messages to selected agents. Contains embedded AgentSelector, auto-resizing textarea, and keyboard shortcuts (Enter to send, Shift+Enter for newline).

### Floating Input Panel (`FloatingInputPanel.tsx`)
Alternative floating panel for sending directed messages. Appears when agents are interrupted, supports minimize/close functionality.

### Agent Input Modal (`AgentInputModal.tsx`)
Full-screen sliding panel from right when agent requests human input. Two modes: normal input and analysis-triggered feedback with highlighted components, scores, and expandable reasoning.

### Agent Selector (`AgentSelector.tsx`)
Carousel-like navigation for browsing and selecting agents. Filters out user agents, shows agent name/summary, supports dot indicators for quick selection.


## Status Display

### Connection (`Connection.tsx`)
WebSocket connection status indicator. Color-coded: green (connected), yellow (connecting), gray (disconnected), red (error).

### Termination Modal (`TerminationModal.tsx`)
Modal displaying final research state after run termination. Shows last message, research state summary, and verified facts from tool calls.

### Agent Badge (`AgentBadge.tsx`)
Displays agent names in colored badges using D3 schemeDark2 colors. Supports three sizes (sm, md, lg).

### Error Boundary (`ErrorBoundary.tsx`)
React Error Boundary for catching render errors. Displays error message with component stack trace.
