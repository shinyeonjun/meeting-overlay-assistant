import test from "node:test";
import assert from "node:assert/strict";

import {
  CAPTION_FEED_MERGE_MAX_COMPACT_CHARS,
  CAPTION_SILENCE_FINALIZE_MAX_COMPACT_CHARS,
  isNonTerminalSilenceFinalize,
  isWeakSilenceFragment,
  looksLikeTerminalCaptionText,
  shouldKeepCaptionFeedOpen,
  shouldMergeCaptionFeedLine,
  shouldSuppressSilenceFinalizeCommit,
} from "../src/controllers/live/live-caption-policy.js";

test("비완결 silence 조각은 약한 fragment로 본다", () => {
  assert.equal(
    isWeakSilenceFragment("도시에는 컴퓨터", { finalizeReason: "silence" }),
    true,
  );
});

test("종결된 silence 문장은 약한 fragment가 아니다", () => {
  assert.equal(
    isWeakSilenceFragment("좋아요.", { finalizeReason: "silence" }),
    false,
  );
});

test("길어도 비완결 silence는 feed에 올리지 않는다", () => {
  assert.equal(
    shouldSuppressSilenceFinalizeCommit(
      "아까 우리가 메인 요리를 하려고 했던 얘기를 시작하기도 전인데 근데 그 얘기 지난번에 정리해서",
      { finalizeReason: "silence" },
    ),
    true,
  );
});

test("종결된 silence라도 자막 길이를 크게 넘기면 feed에 올리지 않는다", () => {
  const longTerminalLine =
    "요리가 되기 위한 회의를 시작해도 될까요? 네? 네 아시다시피 지난번에 제가 유튜브 영상으로 댓글을 받아내는 그거 대단하던데요? 물론 제가 나왔으면 더 잘 나왔겠지만서도 정리한 자료를 기반으로 각자 의견을 말씀해 주시면 됩니다.";

  assert.equal(
    longTerminalLine.replace(/\s+/gu, "").length > CAPTION_SILENCE_FINALIZE_MAX_COMPACT_CHARS,
    true,
  );
  assert.equal(
    shouldSuppressSilenceFinalizeCommit(longTerminalLine, { finalizeReason: "silence" }),
    true,
  );
});

test("종결된 silence는 suppress 대상이 아니다", () => {
  assert.equal(
    isNonTerminalSilenceFinalize("좋습니다.", { finalizeReason: "silence" }),
    false,
  );
});

test("비완결 live_final 문장은 feed를 이어붙일 수 있다", () => {
  assert.equal(
    shouldKeepCaptionFeedOpen("그냥 여기 있던 하나하나의 숫자", "live_final"),
    true,
  );
  assert.equal(
    shouldKeepCaptionFeedOpen("같이 해석해보죠.", "live_final"),
    false,
  );
});

test("자막 줄 길이가 cap을 넘기면 feed 병합을 멈춘다", () => {
  const previous = "댓글을 보면 다들 우리집 레시피가 최고라고 자랑하거든요";
  const next = "그러니까 우리집 취향의 개수만큼 레시피가 존재한다는거죠";
  const mergedCompactLength = `${previous} ${next}`.replace(/\s+/gu, "").length;

  assert.equal(mergedCompactLength > CAPTION_FEED_MERGE_MAX_COMPACT_CHARS, true);
  assert.equal(shouldMergeCaptionFeedLine(previous, next, "live_final"), false);
});

test("짧은 비완결 live_final은 cap 안에서만 feed 병합을 허용한다", () => {
  assert.equal(
    shouldMergeCaptionFeedLine(
      "먼저 먹는 레시피",
      "말씀해주신 분도 계세요",
      "live_final",
    ),
    true,
  );
});

test("종결 어미와 구두점을 문장 끝으로 본다", () => {
  assert.equal(looksLikeTerminalCaptionText("맞습니다"), true);
  assert.equal(looksLikeTerminalCaptionText("도시에는 컴퓨터"), false);
});
