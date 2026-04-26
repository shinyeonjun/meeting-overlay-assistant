import React from "react";
import { FileText, Sparkles } from "lucide-react";

export default function WorkbenchPlaceholder() {
  return (
    <div className="workbench-placeholder">
      <div className="workbench-placeholder-hero">
        <Sparkles size={16} />
        <span>MEETING REPORTS</span>
      </div>
      <h2>왼쪽 회의 목록에서 세션을 고르면 여기서 바로 노트와 회의록을 검토할 수 있습니다.</h2>
      <p>
        워크스페이스 웹은 회의를 새로 시작하는 화면보다, 끝난 회의의 대화 내용, 질문, 결정, 액션,
        회의록을 한 흐름으로 검토하는 데 맞춰져 있습니다.
      </p>
      <div className="workbench-placeholder-note">
        <FileText size={16} />
        <span>새 회의는 앱이나 오버레이에서 시작하고, 여기서는 최근 회의를 선택해 이어서 보면 됩니다.</span>
      </div>
    </div>
  );
}
