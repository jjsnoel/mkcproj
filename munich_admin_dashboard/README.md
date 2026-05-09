# Munich Boys Choir Admin Dashboard

Instagram 운영 데이터 분석 대시보드와 Facebook 사진 아카이브 관리 기능을 한 폴더 안에 묶은 Streamlit 프로젝트입니다.

## 핵심 기능

- Instagram export 기반 월별 성과 / 상위 콘텐츠 / 해시태그 성과 분석
- Meta API 기반 외부 태그 후보 갱신
- 게시 실험 기록
- Facebook 사진 아카이브 관리
  - 새 포스트 사진/캡션 저장
  - 연도별 원본 폴더 자동 정리
  - 릴스 후보 테마 폴더 큐레이션
  - master index 재생성
  - 중복 이미지 검사
  - INBOX 정리

## GitHub에 올리는 것과 안 올리는 것

올리는 것:

```text
app.py
data_utils.py
experiment_tracker.py
meta_api.py
tag_recommender.py
archive_dashboard.py
facebook_archive/
requirements.txt
run_dashboard.bat
.env.example
```

안 올리는 것:

```text
.venv/
.env
data/*.csv
data/*.json
Muenchner_Knabenchor_Archive/
```

`.env`에는 Meta API 토큰이 들어갈 수 있고, `data/`와 `Muenchner_Knabenchor_Archive/`에는 실제 계정 데이터와 사진 원본이 들어가므로 로컬에만 둡니다.

## 실행 방법

```powershell
cd munich_admin_dashboard
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

PowerShell에서 가상환경 실행이 막히면 현재 터미널에서만 아래를 먼저 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

또는 `run_dashboard.bat`을 더블클릭해서 실행할 수 있습니다. 단, `.venv`와 패키지 설치가 먼저 되어 있어야 합니다.

## Meta API 설정

`munich_admin_dashboard/.env.example`을 복사해서 `.env`로 바꾼 뒤 값을 채웁니다.

```text
META_ACCESS_TOKEN=
IG_USER_ID=
GRAPH_API_VERSION=v25.0
```

실제 `.env` 파일은 GitHub에 올리지 않습니다.

## Facebook 사진 아카이브 사용 흐름

1. 대시보드 실행
2. `📸 FB 사진 아카이브` 탭 열기
3. `아카이브 폴더 초기화/확인` 클릭
4. `새 포스트 저장`에서 사진, 게시일, 제목, URL, 캡션 입력
5. 저장 후 `목록/인덱스`에서 확인
6. 릴스에 쓸 사진은 `릴스 후보 큐레이션`에서 테마 폴더로 복사

이 기능은 Facebook을 자동 스크래핑하지 않습니다. 사용자가 직접 저장한 사진과 직접 복사한 캡션만 정리합니다.
