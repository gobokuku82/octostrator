/**
 * Dashboard 관련 타입 정의
 */

export interface PlanStep {
  step_id: number;
  agent: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  error?: string;
}

export interface ExecutionEvent {
  timestamp: string;
  node: string;
  eventType: 'started' | 'completed' | 'error';
  duration?: number;
}

export interface ErrorLog {
  timestamp: string;
  node: string;
  message: string;
}

export interface DashboardState {
  current_step: number;
  plan: PlanStep[];
  messages: number;
  output_format: string;
}

export interface DashboardProps {
  currentNode: string | null;
  planSteps: PlanStep[];
  currentStep: number;
  stateValues: DashboardState;
  errors: ErrorLog[];
  executionHistory: ExecutionEvent[];
}
