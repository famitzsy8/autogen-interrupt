# Tree Visualization

This directory contains the D3.js-based conversation tree visualization system. It renders agent conversations in a horizontal swimlane layout with support for branching, zoom/pan, analysis scoring, and interrupt functionality.


## Core Files

### Main Component (`TreeVisualization.tsx`)
Entry point that orchestrates the visualization. Manages container dimensions via ResizeObserver, integrates the D3 tree hook with React store data, and handles node/edge click events for popups.

### D3 Tree Hook (`useD3Tree.ts`)
Core visualization logic using D3.js. Renders the tree in 6 phases: swimlane backgrounds, agent labels, edges (Bezier curves), nodes (circles for messages, squares for tools), analysis badges, and summary text boxes.

Key features:
- Horizontal swimlane layout (120px per agent)
- Dynamic spacing: recent nodes spread out (150-300px), older nodes compressed (80px)
- Zoom/pan with 0.5x-3x scale range
- Auto-center on latest message (disables after 15 seconds of user interaction)
- Overlap detection for summary text boxes

### Tree Controls (`TreeControls.tsx`)
Keyboard shortcuts for navigation:
- `C`: Recenter on latest message
- `+`/`=`: Zoom in
- `-`: Zoom out
- `0`: Reset zoom to fit all swimlanes

### Node Details Popup (`NodeDetailsPopup.tsx`)
Modal displaying comprehensive node information with three tabs:
- Message: Content with analysis scores and color-coded badges
- Run State: State of run and tool call facts from StateUpdate
- Actions: Tool calls and execution results with expandable details

### Edge Interrupt Popup (`EdgeInterruptPopup.tsx`)
Popup shown when clicking an edge to send an interrupt message. Positioned at click location, integrates with FloatingInputPanel, and passes trim count to backend.


## Analysis Components

### Analysis Badge (`AnalysisBadge.tsx`)
Colored badges representing analysis component scores. Supports collapsed mode (small circles) and expanded mode (labeled badges with tooltips).

### Analysis Score Display (`AnalysisScoreDisplay.tsx`)
Detailed score display shown in NodeDetailsPopup. Card-based layout with color-coded scores, progress bars, and conditional reasoning for triggered components.


## Utilities

### Tree Utils (`utils/treeUtils.ts`)
Tree traversal and data manipulation utilities:
- `convertToD3Hierarchy()`: Convert TreeNode to D3 hierarchy
- `findActivePath()`: Get all active node IDs in current branch
- `findLastMessageNode()`: Get most recent node by timestamp
- `extractAgentNames()`: Get unique agent names in appearance order
- `calculateTrimCount()`: Count active nodes after target (for interrupts)
- `findStateForNode()`: Find state update matching node's timestamp
