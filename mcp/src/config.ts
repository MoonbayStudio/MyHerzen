import { z } from "zod";

const integerFromEnv = (fallback: number, min: number, max: number) =>
  z.coerce.number().int().min(min).max(max).catch(fallback);

export interface AppConfig {
  port: number;
  herzenApiBaseUrl: URL;
  upstreamTimeoutMs: number;
  metadataCacheMs: number;
  rateLimitWindowMs: number;
  rateLimitMaxRequests: number;
  trustProxyHops: number;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const herzenApiBaseUrl = new URL(
    env.HERZEN_API_BASE_URL ?? "https://api.herzen.spb.ru/schedule/v1",
  );

  if (herzenApiBaseUrl.protocol !== "https:") {
    throw new Error("HERZEN_API_BASE_URL must use HTTPS");
  }

  if (herzenApiBaseUrl.hostname !== "api.herzen.spb.ru") {
    throw new Error("HERZEN_API_BASE_URL must point to api.herzen.spb.ru");
  }

  herzenApiBaseUrl.pathname = herzenApiBaseUrl.pathname.replace(/\/+$/, "");

  return {
    port: integerFromEnv(3000, 1, 65_535).parse(env.PORT),
    herzenApiBaseUrl,
    upstreamTimeoutMs: integerFromEnv(10_000, 500, 30_000).parse(
      env.HERZEN_API_TIMEOUT_MS,
    ),
    metadataCacheMs: integerFromEnv(600_000, 0, 3_600_000).parse(
      env.HERZEN_METADATA_CACHE_MS,
    ),
    rateLimitWindowMs: integerFromEnv(60_000, 1_000, 3_600_000).parse(
      env.RATE_LIMIT_WINDOW_MS,
    ),
    rateLimitMaxRequests: integerFromEnv(60, 1, 10_000).parse(
      env.RATE_LIMIT_MAX_REQUESTS,
    ),
    trustProxyHops: integerFromEnv(0, 0, 3).parse(env.TRUST_PROXY_HOPS),
  };
}
