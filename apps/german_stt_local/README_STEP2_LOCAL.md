# Munich Local Voice Translator - Step 2

## 목적
OpenAI API 키 없이 내 컴퓨터에서 다음 파일을 자동 생성합니다.

- 독일어 원문 SRT
- 영어 번역 SRT
- 한국어 번역 SRT

## 처음 한 번만
1. 이 파일들을 `GERMAN_STT_LOCAL` 폴더에 복사
2. `setup_voice_translator_once.bat` 더블클릭
3. 첫 실행 때 Whisper 모델과 NLLB 번역 모델이 자동 다운로드됩니다.

## 매번 실행
`run_voice_translator.bat` 더블클릭

브라우저가 안 열리면:
http://localhost:8501

## 추천 설정
- Whisper 정확도 우선: `large-v3`
- GPU 메모리 오류/속도 우선: `medium`
- 한국어 번역 기본: `독일어 → 한국어 직접`
- 한국어가 어색하면: `독일어 → 영어 → 한국어`도 테스트

## 출력 위치
`output_gpu` 폴더 안에 실행 시간별 폴더가 생깁니다.

예:
- `video.large-v3.de.srt`
- `video.large-v3.en.srt`
- `video.large-v3.ko.srt`
