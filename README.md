# Munich Unified Toolkit

이 폴더는 형이 말한 3가지 작업을 한 폴더로 묶은 통합본입니다.

## 포함 기능

1. **Instagram 해시태그/관리 대시보드**  
   위치: `apps/instagram_dashboard`

2. **독일어 영상 STT + SRT 번역**  
   위치: `apps/german_stt_local`  
   출력: `apps/german_stt_local/output_gpu`

3. **Facebook 사진 아카이브 수집기**  
   위치: `modules/facebook_archive`  
   입력: `modules/facebook_archive/Muenchner_Knabenchor_Archive/00_INBOX/images`  
   출력: `modules/facebook_archive/Muenchner_Knabenchor_Archive/01_ORIGINAL_BY_YEAR`

## 가장 먼저 실행

Windows에서 압축을 푼 뒤:

```text
RUN_MUNICH_TOOLKIT.bat
```

브라우저가 자동으로 안 뜨면:

```text
http://localhost:8501
```

왼쪽 사이드바에서 다음 페이지를 확인하세요.

- `app` = Instagram 해시태그/관리 대시보드
- `photo collector` = Facebook 사진 수집기
- `german subtitle translator` = 독일어 영상 자막/번역

## 독일어 STT 기능 준비

대시보드 자체는 가볍게 실행되지만, 독일어 영상 자막 기능은 Whisper/Transformers가 필요합니다. 처음 한 번만 실행하세요.

```text
SETUP_VIDEO_STT_ONCE.bat
```

추가로 `ffmpeg`가 Windows PATH에 있어야 영상 파일에서 음성을 읽을 수 있습니다.

## Meta API 토큰

보안을 위해 `.env` 실제 토큰은 이 압축파일에서 제외했습니다. 라이브 Meta API 기능을 쓰려면:

1. `.env.example`을 복사
2. `apps/instagram_dashboard/.env`로 이름 변경
3. 본인 토큰과 IG_USER_ID 입력

## GitHub 업로드 순서

이 통합 폴더를 GitHub에 올릴 때는 이 폴더 자체를 repo root로 잡는 게 제일 덜 꼬입니다.

```powershell
git init
git add .
git commit -m "Initial unified Munich toolkit"
git branch -M main
git remote add origin 본인_깃허브_저장소_URL
git push -u origin main
```

이미 연결된 repo가 있으면:

```powershell
git add .
git commit -m "Update unified Munich toolkit"
git push
```
