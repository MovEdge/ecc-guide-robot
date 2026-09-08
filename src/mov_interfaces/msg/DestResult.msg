# ==========================================
# dest_resolver_node의 목적지 해석 결과 기록용 메시지
# ==========================================
# 좌표는 의도적으로 포함하지 않음 — 좌표가 필요한 소비자는
# dest_resolver_node 자신(Nav2 액션 호출)뿐이라 내부 값으로만 쓰고,
# 이 메시지는 mov_ui 등 외부에서 "성공적으로 어떤 장소를 알아들었는지"만
# 알면 되는 소비자를 위한 것.

bool success
string place_name      # 매칭된 정식 장소명 (success=true일 때만 유효)
string error_message    # success=false일 때: "장소를 찾을 수 없음" | "카테고리 검색 미지원" | "LLM 오류" 등
# 비어있지 않으면(예: "화장실"), place_name이 여러 동일 카테고리 후보 중
# 사용자에게 안 물어보고 자동으로 고른 최근접이라는 뜻(2026-09-02 추가,
# resolver_core.AUTO_NEAREST_CATEGORIES 참고) — 소비자(mov_ui)는 TTS
# 안내 문구에 place_name("동1 화장실") 대신 이 카테고리명("화장실")을 써야
# 자연스럽다. 사용자가 직접 고른 경우(choice_selected)나 named_place
# 매칭이면 항상 빈 문자열.
string category
