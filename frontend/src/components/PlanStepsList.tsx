import React from 'react';
import { PlanStep } from '../types/dashboard';

interface PlanStepsListProps {
  steps: PlanStep[];
  currentStep: number;
}

export const PlanStepsList: React.FC<PlanStepsListProps> = ({ steps, currentStep }) => {
  return (
    <div className="plan-steps-list">
      {steps.length === 0 ? (
        <div className="steps-empty">계획이 아직 생성되지 않았습니다</div>
      ) : (
        steps.map((step, index) => (
          <div
            key={step.step_id}
            className={`plan-step ${step.status} ${index === currentStep ? 'current' : ''}`}
          >
            <div className="step-header">
              <span className="step-number">#{step.step_id}</span>
              <span className="step-agent">{step.agent}</span>
              <span className={`step-status-badge ${step.status}`}>
                {step.status === 'pending' && '⏳'}
                {step.status === 'running' && '▶️'}
                {step.status === 'completed' && '✅'}
                {step.status === 'failed' && '❌'}
                {' '}
                {step.status}
              </span>
            </div>
            <div className="step-description">{step.description}</div>
            {step.result && (
              <div className="step-result">
                <strong>Result:</strong> {step.result.substring(0, 100)}
                {step.result.length > 100 && '...'}
              </div>
            )}
            {step.error && (
              <div className="step-error">
                <strong>Error:</strong> {step.error}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
};
