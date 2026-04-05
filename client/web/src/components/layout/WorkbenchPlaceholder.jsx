import React from "react";
import { FileText, Sparkles } from "lucide-react";

export default function WorkbenchPlaceholder() {
  return (
    <div className="workbench-placeholder">
      <div className="workbench-placeholder-hero">
        <Sparkles size={16} />
        <span>MEETING NOTES</span>
      </div>
      <h2>왼쪽 회의 보드에서 회의를 고르면 여기서 바로 회의 노트가 열립니다.</h2>
      <p>
        `회의` 메뉴는 세션 상세가 아니라 질문, 결정, 액션, 리포트를 한 흐름으로 이어보는
        작업면입니다.
      </p>
      <div className="workbench-placeholder-note">
        <FileText size={16} />
        <span>진행 중이거나 최근 회의를 하나 선택해 주세요.</span>
      </div>
    </div>
  );
}
