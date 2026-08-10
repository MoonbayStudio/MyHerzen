import type { NextFunction, Request, Response } from "express";

interface Bucket {
  count: number;
  resetAt: number;
}

export function createRateLimit(options: { windowMs: number; maxRequests: number }) {
  const buckets = new Map<string, Bucket>();

  return (request: Request, response: Response, next: NextFunction): void => {
    const now = Date.now();
    const key = request.ip || request.socket.remoteAddress || "unknown";
    const current = buckets.get(key);
    const bucket = !current || current.resetAt <= now
      ? { count: 0, resetAt: now + options.windowMs }
      : current;
    bucket.count += 1;
    buckets.set(key, bucket);

    response.setHeader("RateLimit-Limit", String(options.maxRequests));
    response.setHeader(
      "RateLimit-Reset",
      String(Math.max(0, Math.ceil((bucket.resetAt - now) / 1000))),
    );

    if (bucket.count > options.maxRequests) {
      response.setHeader("Retry-After", String(Math.ceil(options.windowMs / 1000)));
      response.status(429).json({
        error: {
          code: "RATE_LIMITED",
          message: "Too many MCP requests. Please retry later.",
        },
      });
      return;
    }

    if (buckets.size > 10_000) {
      for (const [bucketKey, candidate] of buckets) {
        if (candidate.resetAt <= now) buckets.delete(bucketKey);
      }
    }
    next();
  };
}
