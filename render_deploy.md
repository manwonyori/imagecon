# ImageCon Render 배포 직접 링크

## 빠른 배포 (원클릭)

아래 링크를 클릭하여 바로 배포할 수 있습니다:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/manwonyori/imagecon)

## 수동 배포 단계

1. Render Dashboard 접속: https://dashboard.render.com/
2. "New +" 버튼 클릭
3. "Web Service" 선택
4. GitHub 계정 연결 (처음인 경우)
5. 저장소 찾기: "manwonyori/imagecon"
6. "Connect" 버튼 클릭
7. 설정 확인:
   - Name: imagecon (또는 원하는 이름)
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
8. "Create Web Service" 클릭

## 배포 상태 확인

- 배포 시작: 보통 2-5분 소요
- 로그 확인: Dashboard > 서비스 선택 > Logs 탭
- 배포 완료시: "Your service is live 🎉" 메시지 표시

## 문제 해결

로그가 없을 경우:
1. 서비스가 아직 생성되지 않음
2. Build 단계에서 멈춤
3. 저장소 연결 문제

해결 방법:
- Render Dashboard에서 서비스 상태 확인
- Events 탭에서 배포 이벤트 확인
- 필요시 "Manual Deploy" > "Clear build cache & deploy" 시도