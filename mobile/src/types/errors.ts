/**
 * MediaGrab Mobile - Error Type Definitions
 * Properly typed error handling for better type safety
 */

export interface MediaGrabError {
  message: string;
  code?: string;
  details?: any;
}

export interface NetworkError extends MediaGrabError {
  code: 'NETWORK_ERROR';
  statusCode?: number;
}

export interface ValidationError extends MediaGrabError {
  code: 'VALIDATION_ERROR';
  field?: string;
}

export interface AnalysisError extends MediaGrabError {
  code: 'ANALYSIS_ERROR';
  platform?: string;
  url?: string;
}

export interface ConnectionError extends MediaGrabError {
  code: 'CONNECTION_ERROR';
  serverUrl?: string;
}

export type AppError = NetworkError | ValidationError | AnalysisError | ConnectionError | MediaGrabError;

/**
 * Type guard to check if an object is a MediaGrabError
 */
export function isMediaGrabError(error: unknown): error is MediaGrabError {
  return typeof error === 'object' && error !== null && 'message' in error;
}

/**
 * Convert unknown error to MediaGrabError
 */
export function toMediaGrabError(error: unknown, defaultMessage: string = "An unknown error occurred"): MediaGrabError {
  if (isMediaGrabError(error)) {
    return error;
  }
  
  if (error instanceof Error) {
    return {
      message: error.message,
      code: 'UNKNOWN_ERROR',
      details: error.stack
    };
  }
  
  return {
    message: defaultMessage,
    code: 'UNKNOWN_ERROR',
    details: error
  };
}
