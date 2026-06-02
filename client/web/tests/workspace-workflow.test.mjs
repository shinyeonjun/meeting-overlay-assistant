import assert from "node:assert/strict";
import test from "node:test";

import {
  groupSessionsByOperationalState,
  resolveMeetingWorkflowStatus,
  resolveWorkflowStatus,
} from "../src/app/workspace-workflow.js";
import { buildEmptyState } from "../src/features/workspace/components/WorkspaceTranscriptPanel.helpers.js";

test("draft sessions stay in preparation state and do not request post-processing", () => {
  const session = {
    id: "session-draft",
    status: "draft",
    post_processing_status: "not_started",
  };
  const reportStatus = {
    status: "pending",
    pipeline_stage: "draft",
  };

  const workflow = resolveWorkflowStatus(session, reportStatus);
  const meetingWorkflow = resolveMeetingWorkflowStatus(session, reportStatus);
  const emptyState = buildEmptyState(meetingWorkflow);

  assert.equal(workflow.category, "draft");
  assert.equal(workflow.pipelineStage, "draft");
  assert.equal(meetingWorkflow.category, "draft");
  assert.equal(emptyState.actionLabel, null);
});

test("draft sessions are grouped with ready sessions instead of processing", () => {
  const sessions = [{ id: "session-draft", status: "draft" }];

  const grouped = groupSessionsByOperationalState(sessions, {
    "session-draft": { status: "pending", pipeline_stage: "draft" },
  });

  assert.deepEqual(grouped.ready.map((session) => session.id), ["session-draft"]);
  assert.equal(grouped.processing.length, 0);
});

test("recovery pipeline status is not treated as report generation ready", () => {
  const workflow = resolveWorkflowStatus(
    { id: "session-recovery", status: "ended" },
    { status: "recovery_required", pipeline_stage: "recovery" },
  );

  assert.equal(workflow.category, "recovery_required");
  assert.equal(workflow.pipelineStage, "recovery");
});
