import test from "node:test";
import assert from "node:assert/strict";

import {
  buildSpeakerNameMap,
  buildTranscriptRows,
  canEditSpeakerNames,
  resolveSpeakerName,
} from "../src/features/workspace/workspace-canvas-model.js";

const speakers = {
  max_name_length: 40,
  items: [
    { speaker_label: "SPEAKER_01", display_name: "김민수", default_name: "화자 1", custom_name: "김민수", utterance_count: 2 },
    { speaker_label: "SPEAKER_00", display_name: "화자 2", default_name: "화자 2", custom_name: null, utterance_count: 1 },
  ],
};

test("발화 행 이름은 서버가 준 speaker_name, 없으면 라벨, 그것도 없으면 참석자다", () => {
  const rows = buildTranscriptRows({
    overview: null,
    reportDetail: null,
    transcriptItems: [
      { speaker_label: "SPEAKER_01", speaker_name: "김민수", start_ms: 0, end_ms: 500, text: "a" },
      { speaker_label: "SPEAKER_03", start_ms: 600, end_ms: 900, text: "b" },
      { speaker_label: null, start_ms: 1000, end_ms: 1500, text: "c" },
    ],
  });

  assert.deepEqual(rows.map((row) => row.speaker), ["김민수", "SPEAKER_03", "참석자"]);
});

test("이벤트 담당자는 화자 목록의 이름으로 바꾸고, 라벨이 없거나 모르면 null이다", () => {
  const names = buildSpeakerNameMap(speakers);

  assert.equal(resolveSpeakerName("SPEAKER_01", names), "김민수");
  assert.equal(resolveSpeakerName(" SPEAKER_00 ", names), "화자 2");
  assert.equal(resolveSpeakerName("SPEAKER_09", names), null);
  assert.equal(resolveSpeakerName(null, names), null);
  assert.equal(resolveSpeakerName("SPEAKER_01", buildSpeakerNameMap(null)), null);
});

test("진행 중이거나 정리 중인 회의는 화자 이름을 바꾸지 않는다", () => {
  const done = { pipelineStage: "completed", status: "completed" };
  assert.equal(canEditSpeakerNames({ isLive: false, speakers, workflow: done }), true);
  assert.equal(canEditSpeakerNames({ isLive: true, speakers, workflow: done }), false);
  assert.equal(canEditSpeakerNames({ isLive: false, speakers: { items: [] }, workflow: done }), false);
  assert.equal(
    canEditSpeakerNames({
      isLive: false,
      speakers,
      workflow: { pipelineStage: "post_processing", status: "processing" },
    }),
    false,
  );
});
