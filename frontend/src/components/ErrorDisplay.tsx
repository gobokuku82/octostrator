import React from 'react';
import { ErrorLog } from '../types/dashboard';

interface ErrorDisplayProps {
  errors: ErrorLog[];
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ errors }) => {
  return (
    <div className="error-display">
      {errors.length === 0 ? (
        <div className="error-empty">에러가 없습니다</div>
      ) : (
        errors.map((error, index) => (
          <div key={index} className="error-item">
            <div className="error-timestamp">
              {new Date(error.timestamp).toLocaleString('ko-KR')}
            </div>
            <div className="error-node">
              Node: {error.node}
            </div>
            <div className="error-message">
              {error.message}
            </div>
          </div>
        ))
      )}
    </div>
  );
};
