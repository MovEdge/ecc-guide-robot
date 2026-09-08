#!/usr/bin/env python3
"""landmarks.csv 전체에 대해 TTS 캐시를 미리 채워둔다(한국어+영어).

로봇을 실제로 켜서 목적지마다 안내를 받아보지 않아도, mov_ui가 실제로
말할 모든 문구를 미리 합성해 tts_node.ensure_cached()와 동일한 캐시에
넣어둔다 — 이후 실제 주행에서는 API 호출 없이 캐시만 재생되어 지연이
거의 없어진다(mov_tts/CLAUDE.md 캐싱 항목 참고).

문구 생성 로직(mov_ui._build_navigating_speech/_build_arrived_speech,
카테고리 자동 최근접 판정은 mov_dest_resolver.AUTO_NEAREST_CATEGORIES)을
직접 재구현하지 않고 그대로 import해서 쓴다 — 실제 런타임이 만드는 문구와
어긋나면 캐시가 있어도 그 문구는 캐시 미스가 나서 예열한 의미가 없어지기
때문.

실행 (ros_humble 컨테이너 안, 워크스페이스 source 후):
    python3 src/mov_tts/scripts/prewarm_cache.py
"""
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from google import genai

# 실측(2026-09-03): gemini-3.1-flash-tts는 분당 10건 쿼터라 동시 요청 5개로
# 돌렸더니 바로 429가 남. 순차 처리 + 429의 "retry in Ns" 안내를 그대로
# 따라 대기하는 재시도로 바꿈.
_RETRY_AFTER_RE = re.compile(r'retry in ([\d.]+)s')
MAX_RETRIES = 6

from mov_dest_resolver.resolver_core import (
    AUTO_NEAREST_CATEGORIES, DEFAULT_LANDMARKS_CSV, load_landmarks)
from mov_tts.tts_node import cache_path, ensure_cached
from mov_ui.i18n import i18n
from mov_ui.ui_node import _build_arrived_speech, _build_navigating_speech

LANGS = ('ko', 'en')


def collect_phrases():
    """실제 mov_ui가 말할 수 있는 모든 문구를 언어별로 수집(중복 제거)."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    auto_nearest_categories = sorted({
        lm.category for lm in landmarks if lm.category in AUTO_NEAREST_CATEGORIES})
    named_place_landmarks = [
        lm for lm in landmarks if lm.category not in AUTO_NEAREST_CATEGORIES]

    phrases = set()
    for lang in LANGS:
        i18n._lang = lang  # set_lang()은 콜백을 돌리는데 여긴 콜백이 없어 직접 대입
        phrases.add(_build_arrived_speech())
        for category in auto_nearest_categories:
            phrases.add(_build_navigating_speech(place_name='', category=category))
        for lm in named_place_landmarks:
            phrases.add(_build_navigating_speech(place_name=lm.name, category=''))

    return sorted(phrases)


def main():
    load_dotenv()
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print('GEMINI_API_KEY 미설정 — .env 확인', file=sys.stderr)
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    phrases = collect_phrases()
    print(f'대상 문구 {len(phrases)}개 (한국어+영어, 랜드마크 {DEFAULT_LANDMARKS_CSV} 기준)')

    already = sum(1 for p in phrases if os.path.exists(cache_path(p)))
    print(f'이미 캐시됨 {already}개, 새로 합성 {len(phrases) - already}개')

    ok, failed = 0, []

    def work(text):
        for attempt in range(MAX_RETRIES):
            try:
                ensure_cached(client, text, log=lambda _msg: None)
                return text
            except Exception as e:
                m = _RETRY_AFTER_RE.search(str(e))
                if m and attempt < MAX_RETRIES - 1:
                    wait_s = float(m.group(1)) + 1.0
                    print(f'429, {wait_s:.0f}초 대기 후 재시도: {text}', file=sys.stderr)
                    time.sleep(wait_s)
                    continue
                raise

    # 쿼터가 분당 10건이라 동시 요청 자체가 429를 유발함 — 순차 처리.
    with ThreadPoolExecutor(max_workers=1) as pool:
        futures = {pool.submit(work, p): p for p in phrases}
        for i, future in enumerate(as_completed(futures), 1):
            text = futures[future]
            try:
                future.result()
                ok += 1
                print(f'[{i}/{len(phrases)}] OK: {text}')
            except Exception as e:
                failed.append((text, e))
                print(f'[{i}/{len(phrases)}] FAILED: {text} -> {e!r}', file=sys.stderr)

    print(f'완료: {ok}개 성공, {len(failed)}개 실패')
    if failed:
        for text, e in failed:
            print(f'  - {text!r}: {e!r}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
