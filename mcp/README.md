# Herzen MCP

Connect official Herzen University schedule data to your usual AI assistant.

Ask things like:

- «Какие у меня пары сегодня?»
- «Во сколько в пятницу заканчиваются пары?»
- «Успею ли я после пар зайти в спортзал?»
- «Найди мою группу ИВТ»

The server does not contain an LLM and does not replace ChatGPT, Claude, Gemini,
or another MCP-capable client. It gives that client structured, read-only data;
the client combines it with the conversation, its own memory, calendar, maps, or
other tools.

## MVP scope

This first version implements milestones 1-2:

- stateless Streamable HTTP endpoint at `POST /mcp`;
- healthcheck at `GET /health`;
- `search_groups`;
- `get_schedule`;
- normalized data from the public official Herzen schedule API.

Knowledge search, crawling, OAuth, accounts, and write operations are not part
of this MVP.

## How the group is remembered

There is intentionally no Herzen MCP account in this version. The user can tell
their AI, for example, «Моя группа — 1б-ИВТ-1/26». A client with conversation or
profile memory can pass that group to `get_schedule` later. If it does not know
the group, the tool description instructs it to ask the user or call
`search_groups`; the server never guesses among multiple matches.

## Tools

### `search_groups`

Input:

```json
{ "query": "ИВТ" }
```

Returns official group IDs, names, and their faculty/institute.

### `get_schedule`

Input:

```json
{
  "group": "1б-ИВТ-1/26",
  "dateFrom": "2026-09-01",
  "dateTo": "2026-09-07"
}
```

`group` may be an official numeric ID or an unambiguous name. Dates are optional;
without them the server returns today plus the next six days in
`Europe/Moscow`. The maximum range is 31 days.

## Development

Requirements: Node.js 22 or newer.

```bash
cp .env.example .env
npm install
npm test
npm run dev
```

Then check:

```bash
curl http://localhost:3000/health
```

The integration suite starts a real local HTTP server and verifies MCP
initialization, `tools/list`, both `tools/call` paths, structured output, and
schema rejection.

## Docker

```bash
docker compose up --build
```

In production, put the service behind an HTTPS reverse proxy and expose a stable
URL such as `https://mcp.example.org/mcp`. Configure that URL in any client that
supports remote MCP over Streamable HTTP. Client-specific availability and setup
steps can change; check the current documentation for the chosen AI client. If
there is exactly one trusted reverse proxy, set `TRUST_PROXY_HOPS=1` so per-client
rate limiting uses the forwarded address; leave the secure default `0` otherwise.

## Privacy and security

- read-only tools only;
- no account, token, prompt, or personal-profile storage;
- no arbitrary URL input;
- the upstream hostname is restricted to `api.herzen.spb.ru` over HTTPS;
- bounded inputs, date ranges, request bodies, upstream time, and response size;
- per-IP MCP rate limiting;
- structured logs exclude prompts and group values.

All schedule results identify the official upstream source. Empty days are
returned explicitly. Upstream failures use stable error codes and are never
presented as fresh cached data.

## Project notes

The audited MyHerzen API flow and implementation decisions are documented in
[`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md).
