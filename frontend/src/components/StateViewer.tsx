import React, { useState } from 'react';
import { DashboardState } from '../types/dashboard';

interface StateViewerProps {
  state: DashboardState;
}

export const StateViewer: React.FC<StateViewerProps> = ({ state }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="state-viewer">
      <div className="state-summary">
        <div className="state-item">
          <strong>Current Step:</strong> {state.current_step ?? 0}
        </div>
        <div className="state-item">
          <strong>Plan Length:</strong> {state.plan?.length ?? 0}
        </div>
        <div className="state-item">
          <strong>Messages:</strong> {state.messages ?? 0}
        </div>
        <div className="state-item">
          <strong>Output Format:</strong> {state.output_format ?? 'chat'}
        </div>
      </div>

      <button
        className="expand-button"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? '▼ Hide Full State' : '▶ Show Full State'}
      </button>

      {expanded && (
        <pre className="state-json">
          {JSON.stringify(state, null, 2)}
        </pre>
      )}
    </div>
  );
};
