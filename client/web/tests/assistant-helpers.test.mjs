import assert from "node:assert/strict";
import test from "node:test";

import {
  ASSISTANT_POLL_MAX_FAILURES,
  buildChatRequest,
  buildConversationScopeKey,
  buildMessagesFromConversationResponse,
  hasPendingAssistantResponse,
  shouldStopAssistantPollingAfterFailure,
} from "../src/features/assistant/Assistant.helpers.js";

test("buildChatRequest restores conversation id and sends compact completed history", () => {
  const request = buildChatRequest(
    "What was decided?",
    { accountId: "account-1", contactId: "contact-1", contextThreadId: "thread-1" },
    {
      conversationId: "conversation-1",
      messages: [
        { role: "user", content: "Earlier question", status: "completed" },
        { role: "assistant", content: "Earlier answer", status: "completed" },
        { role: "assistant", content: "", status: "pending" },
        { role: "assistant", content: "Network failed", error: "failed" },
      ],
    },
  );

  assert.equal(request.conversationId, "conversation-1");
  assert.deepEqual(request.sourceTypes, ["report", "note"]);
  assert.equal(request.accountId, "account-1");
  assert.equal(request.contactId, "contact-1");
  assert.equal(request.contextThreadId, "thread-1");
  assert.deepEqual(request.history, [
    { role: "user", content: "Earlier question" },
    { role: "assistant", content: "Earlier answer" },
  ]);
});

test("buildConversationScopeKey separates users and workspace context", () => {
  assert.equal(
    buildConversationScopeKey({
      userId: "user-1",
      accountId: "account-1",
      contactId: "contact-1",
      contextThreadId: "thread-1",
    }),
    "user:user-1|account-1|contact-1|thread-1",
  );
  assert.equal(
    buildConversationScopeKey({}),
    "anonymous|all-accounts|all-contacts|workspace",
  );
});

test("buildMessagesFromConversationResponse keeps usable messages and hides empty pending assistant", () => {
  const messages = buildMessagesFromConversationResponse({
    messages: [
      {
        id: "user-1",
        role: "user",
        content: "Question",
        status: "completed",
        sources: [],
        created_at: "2026-05-27T00:00:00Z",
      },
      {
        id: "assistant-pending-1",
        role: "assistant",
        content: "",
        status: "pending",
        sources: [],
        created_at: "2026-05-27T00:00:01Z",
      },
      {
        id: "assistant-1",
        role: "assistant",
        content: "Answer",
        status: "completed",
        sources: [{ chunk_id: "chunk-1" }],
        created_at: "2026-05-27T00:00:02Z",
      },
    ],
  });

  assert.deepEqual(messages.map((message) => message.id), ["user-1", "assistant-1"]);
  assert.equal(messages[1].sources[0].chunk_id, "chunk-1");
});

test("assistant polling helpers detect pending state and bounded failure retries", () => {
  assert.equal(
    hasPendingAssistantResponse({
      messages: [{ role: "assistant", status: "pending", content: "" }],
    }),
    true,
  );
  assert.equal(
    shouldStopAssistantPollingAfterFailure(ASSISTANT_POLL_MAX_FAILURES - 1),
    false,
  );
  assert.equal(
    shouldStopAssistantPollingAfterFailure(ASSISTANT_POLL_MAX_FAILURES),
    true,
  );
});
