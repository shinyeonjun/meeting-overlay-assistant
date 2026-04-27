import React from "react";
import { FileText, Sparkles } from "lucide-react";

export default function WorkbenchPlaceholder() {
  return (
    <div className="workbench-placeholder">
      <div className="workbench-placeholder-hero">
        <Sparkles size={16} />
        <span>회의 선택</span>
      </div>
      <h2>왼쪽 회의 목록에서 회의를 고르면 노트와 회의록을 바로 검토할 수 있습니다.</h2>
      <p>
        회의가 끝난 뒤 대화 내용, 질문, 결정, 다음 할 일, 회의록을 한 흐름으로 확인하는 화면입니다.
      </p>
      <div className="workbench-placeholder-note">
        <FileText size={16} />
        <span>새 회의는 앱이나 오버레이에서 시작하고, 여기서는 최근 회의를 선택해 이어서 보면 됩니다.</span>
      </div>
    </div>
  );
}
