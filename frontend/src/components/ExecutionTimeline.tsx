import React from 'react';
import { ExecutionEvent } from '../types/dashboard';

interface ExecutionTimelineProps {
  events: ExecutionEvent[];
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({ events }) => {
  return (
    <div className="execution-timeline">
      {events.length === 0 ? (
        <div className="timeline-empty">실행 이벤트가 없습니다</div>
      ) : (
        events.map((event, index) => (
          <div key={index} className={`timeline-event ${event.eventType}`}>
            <div className="event-icon">
              {event.eventType === 'started' && '🟢'}
              {event.eventType === 'completed' && '🔵'}
              {event.eventType === 'error' && '🔴'}
            </div>
            <div className="event-details">
              <div className="event-node">{event.node}</div>
              <div className="event-time">
                {new Date(event.timestamp).toLocaleTimeString('ko-KR')}
              </div>
              {event.duration !== undefined && (
                <div className="event-duration">{event.duration.toFixed(2)}s</div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
};
