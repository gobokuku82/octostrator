import React from 'react';
import { DashboardProps } from '../types/dashboard';
import { ExecutionTimeline } from './ExecutionTimeline';
import { PlanStepsList } from './PlanStepsList';
import { StateViewer } from './StateViewer';
import { ErrorDisplay } from './ErrorDisplay';
import './Dashboard.css';

export const Dashboard: React.FC<DashboardProps> = ({
  currentNode,
  planSteps,
  currentStep,
  stateValues,
  errors,
  executionHistory
}) => {
  return (
    <div className="dashboard-panel">
      {/* 헤더 */}
      <div className="dashboard-header">
        <h2>🔍 Execution Monitor</h2>
        <div className={`status-badge ${currentNode ? 'running' : 'idle'}`}>
          {currentNode ? `Running: ${currentNode}` : 'Idle'}
        </div>
      </div>

      {/* 실행 타임라인 */}
      <div className="dashboard-section">
        <h3>📈 Execution Timeline</h3>
        <ExecutionTimeline events={executionHistory} />
      </div>

      {/* 계획 단계 */}
      <div className="dashboard-section">
        <h3>📋 Plan Steps</h3>
        <PlanStepsList
          steps={planSteps}
          currentStep={currentStep}
        />
      </div>

      {/* State 뷰어 */}
      <div className="dashboard-section">
        <h3>💾 Current State</h3>
        <StateViewer state={stateValues} />
      </div>

      {/* 에러 로그 */}
      {errors.length > 0 && (
        <div className="dashboard-section error-section">
          <h3>❌ Errors</h3>
          <ErrorDisplay errors={errors} />
        </div>
      )}
    </div>
  );
};
