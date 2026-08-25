# ==========================================
# stt_node의 음성인식 결과 기록용 메시지
# ==========================================

bool success          # 음성 인식 자체의 성패 (무음/API에러 등). 
string text
string error_message  # success=false일 때만: "무음 감지" | "API 오류" 등
