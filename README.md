# ImageCon - 이미지 일괄 변환기

웹 기반 이미지 일괄 변환 도구입니다.

## 주요 기능

- 🖼️ 드래그 앤 드롭으로 여러 이미지 한번에 업로드
- 🔄 JPG, PNG, WEBP 형식으로 변환
- 📏 이미지 리사이징 (비율 유지 또는 1000x1000 정사각형)
- 🎨 품질 조절 (50-100%)
- 📦 변환된 이미지 ZIP 파일로 일괄 다운로드
- 📱 반응형 디자인 (모바일 지원)
- ⚠️ 상세한 오류 메시지 (파일별 처리 상태)

## 지원 파일 형식

입력: JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF
출력: JPG, PNG, WEBP
최대 파일 크기: 50MB

## 크기 조절 옵션

1. **비율 유지**: 원본 비율을 유지하면서 최대 크기 내에서 리사이징
2. **1000x1000 정사각형**: 이미지를 중앙 크롭하여 정확히 1000x1000 픽셀로 변환

## 사용 방법

1. 웹사이트 접속
2. 출력 형식, 품질, 최대 크기 설정
3. 이미지를 드래그 앤 드롭 또는 클릭하여 선택
4. 자동 변환 후 ZIP 파일로 다운로드

## 기술 스택

- Backend: Python Flask
- Image Processing: Pillow
- Frontend: HTML5, CSS3, JavaScript
- Deployment: Render

## 로컬 실행

```bash
pip install -r requirements.txt
python app.py
```

http://localhost:5000 접속