import { afterEach, describe, expect, it, vi } from "vitest";


describe("authenticated API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends cookies and exposes a stable error for non-success responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "authentication_required" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const api = await import("./api");

    await expect(api.getCurrentUser()).rejects.toMatchObject({
      status: 401,
      code: "authentication_required",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("sends the selected LLM protocol in the settings JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ llm_protocol: "anthropic_messages" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const api = await import("./api");

    await api.updateSettings({
      llm_protocol: "anthropic_messages",
      llm_base_url: "https://api.anthropic.com",
      llm_model: "claude-3-5-haiku-latest",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/settings",
      expect.objectContaining({
        method: "PUT",
        credentials: "include",
        body: JSON.stringify({
          llm_protocol: "anthropic_messages",
          llm_base_url: "https://api.anthropic.com",
          llm_model: "claude-3-5-haiku-latest",
        }),
      }),
    );
  });
});
