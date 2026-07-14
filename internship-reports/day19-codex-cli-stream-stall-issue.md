# Codex CLI silent stream stall issue

Date: 2026-07-14

Target: `openai/codex` new CLI bug issue

Status: published as [openai/codex#33051](https://github.com/openai/codex/issues/33051) after the user confirmed the exact target, title, and body.

## Evidence boundary

- `OBS`: On `codex-cli 0.144.4`, an HTTP/SSE Responses turn logged `stream disconnected - retrying sampling request (1/5)` at `2026-07-14 12:06:21 UTC` and `(2/5)` at `12:06:51 UTC`; the next attempt recovered. The user has also observed 5-10 minute periods with no TUI progress. The local logs do not prove that these particular retries were caused by the 300-second idle timeout.
- `CODE`: Current `openai/codex` main at `5bed6447998c754d154dbd796517310b8f04d4ce` defaults `stream_idle_timeout` to 300 seconds and `stream_max_retries` to 5.
- `CODE`: HTTP/SSE applies the same idle timeout to the first and every subsequent `stream.next()` call. WebSocket does the same after sending a request.
- `CODE`: An idle timeout maps to a retryable stream error. Failed WebSocket connections are discarded before retry. Release builds suppress the first WebSocket reconnect notification, while HTTP/SSE surfaces it.
- `INFERENCE`: A silent or half-open model response stream can therefore look frozen for one or more complete 300-second windows. Existing issue observations support this mechanism, but the source of a particular silent stream can be the backend, an intermediary, or the local network.

## Exact issue draft

### Title

`CLI can wait 300s before detecting a silent Responses stream, causing repeated 5-10 minute stalls`

### Body

````markdown
### What version of Codex CLI is running?

codex-cli 0.144.4

### What subscription do you have?

API key billing through a custom Responses-compatible provider

### Which model were you using?

gpt-5.6-sol, high/xhigh reasoning

### What platform is your computer?

Linux 6.8.0-124-generic x86_64 x86_64

### What terminal emulator and version are you using (if applicable)?

VS Code integrated terminal 1.128.0 over SSH, without tmux or zellij

### Codex doctor report

```json
{
  "overallStatus": "ok",
  "codexVersion": "0.144.4",
  "authMode": "api_key",
  "model": "gpt-5.6-sol",
  "wireApi": "responses",
  "transport": "responses_http",
  "supportsWebsockets": false,
  "providerReachability": "ok",
  "note": "The custom provider base URL and local filesystem paths were redacted."
}
```

### What issue are you seeing?

Codex can remain in `Working` with no new reasoning, tool, or progress events for 5-10 minutes when a Responses stream becomes silent without delivering a clean EOF or transport error. In one recent HTTP/SSE turn on 0.144.4, the structured log recorded `stream disconnected - retrying sampling request (1/5)` and then `(2/5)` about 31 seconds later before a later attempt recovered. This confirms repeated stream failure and recovery in the affected environment, although that local sample alone does not prove the 300-second path.

Current main still has a client-side mechanism that can explain the longer silent windows. The default `stream_idle_timeout` is [300,000 ms](https://github.com/openai/codex/blob/5bed6447998c754d154dbd796517310b8f04d4ce/codex-rs/model-provider-info/src/lib.rs#L26-L27), and both HTTP/SSE and WebSocket use that same timeout while waiting for the first application event after a request as well as for later stream events:

- HTTP/SSE: [`timeout(idle_timeout, stream.next())`](https://github.com/openai/codex/blob/5bed6447998c754d154dbd796517310b8f04d4ce/codex-rs/codex-api/src/sse/responses.rs#L491-L527)
- WebSocket: [`timeout(idle_timeout, ws_stream.next())`](https://github.com/openai/codex/blob/5bed6447998c754d154dbd796517310b8f04d4ce/codex-rs/codex-api/src/endpoint/responses_websocket.rs#L666-L705)

The resulting stream error is retryable, with a default budget of [five retries](https://github.com/openai/codex/blob/5bed6447998c754d154dbd796517310b8f04d4ce/codex-rs/model-provider-info/src/lib.rs#L26-L31). This means a silent or half-open stream can consume one or more complete 300-second windows before recovery. For WebSocket release builds, the [first retry notification is intentionally suppressed](https://github.com/openai/codex/blob/5bed6447998c754d154dbd796517310b8f04d4ce/codex-rs/core/src/responses_retry.rs#L48-L74), which makes the first window appear completely frozen.

This is related to #23807, #32764, #32818, and #32856. Those reports provide symptom and transport evidence; this issue is intended to track the shared client behavior and an implementation-level acceptance criterion across both Responses transports. I am not claiming that every stall has the same backend or network cause.

### What steps can reproduce the bug?

The production failure is intermittent, but maintainers can reproduce the client behavior deterministically with a mock Responses transport:

1. Return successful HTTP response headers for an SSE request, or accept a WebSocket request frame.
2. Do not yield a request-correlated application event and do not close the stream.
3. Observe that Codex waits the full `stream_idle_timeout` before retrying.
4. Repeat the silent response on the next attempt and observe another full timeout window.

### What is the expected behavior?

Codex should distinguish request acknowledgement from inactivity within an already acknowledged stream. After sending a request, it should use a shorter, separately configurable watchdog for a request-correlated protocol event such as `response.created` or equivalent turn state. If that acknowledgement does not arrive, Codex should retry on a fresh transport and show a visible waiting/reconnect status before the long stream idle timeout expires.

The existing 300-second idle timeout can remain available for an acknowledged long-running response. Ping/pong frames, cached connection metadata, rate-limit events, or other uncorrelated activity should not satisfy the request-acknowledgement watchdog.

### Additional information

A focused regression should use paused Tokio time and assert both transports separately: headers/send succeeds, no request-correlated event arrives, the request-ack watchdog fires before 300 seconds, a fresh attempt is made, and the user receives a visible status. A second test should send `response.created` and verify that subsequent inactivity still uses the normal stream idle timeout.
````

## Publication record

- Published at: `2026-07-14T12:26:44Z`
- Author: `ranxi2001`
- Initial state: open, unlocked, no assignee, no milestone, no comments
- Automatic labels: `bug`, `CLI`, `custom-model`, `connectivity`
- Remote title and body matched the confirmed draft; GitHub only added a trailing blank line.
- No maintainer mention, follow-up comment, or other issue mutation was made.
