import React from "react";
import { FileText, Sparkles } from "lucide-react";

export default function WorkbenchPlaceholder() {
  return (
    <div className="workbench-placeholder">
      <div className="workbench-placeholder-hero">
        <Sparkles size={16} />
        <span>SESSION REVIEW DESK</span>
      </div>
      <h2>왼쪽 인박스에서 세션을 고르면 여기서 바로 검토가 시작됩니다.</h2>
      <p>
        이 화면은 분석 대시보드가 아니라 회의 운영 작업면입니다. 세션 상태를 확인하고,
        리포트를 생성하고, 최신 문서를 검토하는 흐름만 남겨두었습니다.
      </p>
      <div className="workbench-placeholder-note">
        <FileText size={16} />
        <span>진행 중, 생성 가능, 실패 세션 중 하나를 먼저 선택해 주세요.</span>
      </div>
    </div>
  );
}
