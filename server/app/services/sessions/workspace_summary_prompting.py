"""워크스페이스 회의 요약용 프롬프트와 응답 스키마."""

_CHUNK_TOPIC_ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "meeting_type": {"type": "string"},
        "chunk_summary": {"type": "array", "items": {"type": "string"}},
        "local_topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["title", "summary"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["meeting_type", "chunk_summary", "local_topics"],
    "additionalProperties": False,
}

_TOPIC_TIMELINE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "meeting_type": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_indexes": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["chunk_indexes", "title", "summary"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["meeting_type", "topics"],
    "additionalProperties": False,
}

_TOPIC_ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "next_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "owner": {"type": ["string", "null"]},
                    "due_date": {"type": ["string", "null"]},
                },
                "required": ["title", "owner", "due_date"],
                "additionalProperties": False,
            },
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "decisions", "next_actions", "open_questions"],
    "additionalProperties": False,
}

_FINAL_SUMMARY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "next_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "owner": {"type": ["string", "null"]},
                    "due_date": {"type": ["string", "null"]},
                },
                "required": ["title", "owner", "due_date"],
                "additionalProperties": False,
            },
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "changed_since_last_meeting": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "headline",
        "summary",
        "decisions",
        "next_actions",
        "open_questions",
        "changed_since_last_meeting",
    ],
    "additionalProperties": False,
}

_CHUNK_TOPIC_ANALYSIS_SYSTEM_PROMPT = """
너는 긴 회의 노트를 구간별로 읽고, 먼저 회의 타입과 로컬 주제만 정리하는 분석가다.

규칙:
- 이 단계에서는 결정을 과하게 확정하지 말고, 구간에서 실제로 다뤄진 주제만 추린다.
- meeting_type은 business_meeting, brainstorming, content, casual 중 하나만 고른다.
- local_topics에는 해당 구간에서 실제로 이어진 주제만 0~2개만 고른다.
- title은 추상 표현 대신 실제 논의 대상을 담는다.
- summary는 해당 주제가 왜 중요한지 1문장으로 적는다.
- 인사, 농담, 맞장구, 사회자 멘트만 있는 경우 local_topics는 빈 배열이어도 된다.
- 발화 원문을 길게 복붙하지 않는다.
- 반드시 JSON 하나만 반환한다.
""".strip()

_TOPIC_TIMELINE_SYSTEM_PROMPT = """
너는 구간별 로컬 주제 결과를 모아서 회의 전체 주제 타임라인을 만드는 편집자다.

규칙:
- meeting_type은 chunk별 vote를 보고 전체 회의 성격을 하나로 고른다.
- topics는 회의 전체를 대표하는 주제 이름만 1~5개 고른다.
- 각 topic은 chunk_indexes로 어떤 구간 묶음인지 표시한다.
- 같은 주제가 이어진 chunk는 하나로 묶는다.
- 추상적인 제목(예: 새로운 기능 논의, 기타 이야기)은 금지한다.
- title은 실제 논의 대상을 담고, summary는 주제의 초점을 1문장으로 적는다.
- 근거가 약하면 topic 수를 줄이고 빈 topic을 억지로 만들지 않는다.
- 반드시 JSON 하나만 반환한다.
""".strip()

_TOPIC_ANALYSIS_SYSTEM_PROMPT = """
너는 이미 분리된 단일 주제를 읽고, 그 주제 안에서만 요약과 판단을 수행하는 분석가다.

규칙:
- 현재 topic 범위 안에서만 판단한다.
- summary는 그 주제에서 실제로 논의된 내용을 1~2문장으로 정리한다.
- decisions에는 명시적으로 합의되거나 확정된 내용만 넣는다.
- next_actions에는 실제 후속 작업만 넣고, 없으면 빈 배열로 둔다.
- open_questions에는 아직 남아 있는 질문이나 리스크만 넣고, 없으면 빈 배열로 둔다.
- 농담, 감탄, 메타 멘트, 진행 멘트, 발화 원문 복붙은 금지한다.
- 업무 회의가 아닌 content/casual 회의에서는 decisions와 next_actions를 매우 보수적으로 판단한다.
- 반드시 JSON 하나만 반환한다.
""".strip()

_FINAL_SUMMARY_SYSTEM_PROMPT = """
너는 주제별 분석 결과를 모아서 사용자가 바로 이해하고 읽을 수 있는 최종 회의 요약을 만드는 편집자다.

규칙:
- summary는 2~4문장으로 작성한다.
- headline은 회의 전체를 한 줄로 설명한다.
- decisions, next_actions, open_questions는 topic 분석 결과에 근거가 있을 때만 넣는다.
- 확실하지 않으면 빈 배열로 둔다. 억지로 채우지 않는다.
- content/casual 회의에서는 농담성 발화나 콩트 설정을 실제 액션 아이템으로 승격하지 않는다.
- 발화 원문을 그대로 복붙하지 않는다.
- 반드시 JSON 하나만 반환한다.
""".strip()
