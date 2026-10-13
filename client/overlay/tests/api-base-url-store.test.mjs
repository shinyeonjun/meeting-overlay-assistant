import test from "node:test";
import assert from "node:assert/strict";

import { createApiBaseUrlStore } from "../../shared/src/runtime/create-api-base-url-store.js";

const KEY = "caps-test-live-api-base-url";

function installStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  globalThis.window = {
    localStorage: {
      getItem: (key) => (data.has(key) ? data.get(key) : null),
      setItem: (key, value) => data.set(key, String(value)),
      removeItem: (key) => data.delete(key),
    },
  };
  return data;
}

test("저장된 값이 없으면 기본값을 쓴다", () => {
  installStorage();
  const store = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });

  assert.equal(store.getApiBaseUrl(), "http://127.0.0.1:8011");
  assert.equal(store.isUsingDefaultApiBaseUrl(), true);
});

test("기본값과 같은 주소는 저장하지 않는다", () => {
  const data = installStorage();
  const store = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });

  store.setApiBaseUrl("127.0.0.1:8011/");

  assert.equal(data.has(KEY), false);
});

test("사용자가 고른 주소는 기본값이 그대로인 동안 유지된다", () => {
  const data = installStorage();
  createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY }).setApiBaseUrl("http://10.0.0.5:9000");

  const reopened = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });

  assert.equal(reopened.getApiBaseUrl(), "http://10.0.0.5:9000");
  assert.equal(reopened.isUsingDefaultApiBaseUrl(), false);
  assert.equal(JSON.parse(data.get(KEY)).defaultAtSave, "http://127.0.0.1:8011");
});

test("저장한 뒤 기본값(환경 변수)이 바뀌면 새 기본값을 따른다", () => {
  const data = installStorage();
  createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8012", storageKey: KEY }).setApiBaseUrl("http://10.0.0.5:9000");

  const reopened = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });

  assert.equal(reopened.getApiBaseUrl(), "http://127.0.0.1:8011");
  assert.equal(data.has(KEY), false);
});

test("예전 형식으로 저장된 내장 기본 주소는 지금 기본값과 다르면 버린다", () => {
  // 이전 버전은 "다시 확인"을 누를 때 기본값 8012를 문자열로 저장했다.
  const data = installStorage({ [KEY]: "http://127.0.0.1:8012" });

  const store = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });

  assert.equal(store.getApiBaseUrl(), "http://127.0.0.1:8011");
  assert.equal(data.has(KEY), false);
});

test("예전 형식이라도 사용자가 직접 넣은 주소는 유지한다", () => {
  installStorage({ [KEY]: "http://192.168.0.20:8011" });

  const store = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });

  assert.equal(store.getApiBaseUrl(), "http://192.168.0.20:8011");
});

test("기본값으로 되돌리면 저장값을 지운다", () => {
  const data = installStorage();
  const store = createApiBaseUrlStore({ defaultBaseUrl: "http://127.0.0.1:8011", storageKey: KEY });
  store.setApiBaseUrl("http://10.0.0.5:9000");

  store.resetApiBaseUrl();

  assert.equal(store.getApiBaseUrl(), "http://127.0.0.1:8011");
  assert.equal(data.has(KEY), false);
});
