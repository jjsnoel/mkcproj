# Project Context

이 통합본은 기존 3개 작업을 하나의 폴더로 모은 버전입니다.

- `apps/instagram_dashboard`: 인스타그램/릴스 성과, 해시태그 추천, 실험 기록용 Streamlit 대시보드
- `apps/german_stt_local`: 독일어 영상/음성 → DE/EN/KO SRT 생성 파이프라인
- `modules/facebook_archive`: Facebook 사진 아카이브 폴더와 archive_manager.py

최근 반영 내용:

- `archive_manager.py`에 `archive_inbox_post(...)` 함수가 있는 버전을 사용
- `photo collector` 페이지는 더 이상 `data/collected_photos` 단순 복사를 하지 않음
- `00_INBOX/images` → `01_ORIGINAL_BY_YEAR/YYYY/post/images/001.jpg` 구조로 정리
- 모든 기본 경로는 압축을 푼 위치 기준의 상대 경로로 동작하도록 수정
- 실제 Meta API 토큰이 들어 있는 `.env`는 제외하고 `.env.example`만 포함
