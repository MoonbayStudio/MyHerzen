export const errorCodes = [
  "GROUP_NOT_FOUND",
  "GROUP_AMBIGUOUS",
  "SCHEDULE_UNAVAILABLE",
  "INVALID_DATE_RANGE",
  "UPSTREAM_UNAVAILABLE",
] as const;

export type HerzenErrorCode = (typeof errorCodes)[number];

export class HerzenMcpError extends Error {
  constructor(
    public readonly code: HerzenErrorCode,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "HerzenMcpError";
  }
}

export function serializeError(error: unknown): {
  code: HerzenErrorCode;
  message: string;
  details?: unknown;
} {
  if (error instanceof HerzenMcpError) {
    return {
      code: error.code,
      message: error.message,
      ...(error.details === undefined ? {} : { details: error.details }),
    };
  }

  return {
    code: "UPSTREAM_UNAVAILABLE",
    message: "The official Herzen schedule service is unavailable.",
  };
}
