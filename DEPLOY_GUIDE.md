# ImageCon Render 배포 가이드

## 자동 배포 설정 (이미 완료된 경우)
GitHub 저장소가 Render와 연결되어 있다면, push할 때마다 자동으로 배포됩니다.

## 신규 배포 방법

1. **Render 접속**
   - https://render.com 로그인

2. **새 서비스 생성**
   - Dashboard에서 "New +" 클릭
   - "Web Service" 선택

3. **GitHub 저장소 연결**
   - "Connect a repository" 선택
   - `manwonyori/imagecon` 검색 및 선택
   - "Connect" 클릭

4. **서비스 설정**
   - Name: `imagecon` (또는 원하는 이름)
   - Region: Singapore (아시아 지역 추천)
   - Branch: `master`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

5. **인스턴스 타입 선택**
   - Free tier 선택 (무료)

6. **Create Web Service 클릭**

## 배포 확인

배포가 완료되면 다음과 같은 URL이 생성됩니다:
- https://imagecon.onrender.com (또는 선택한 이름)

## 수동 배포

Dashboard에서 서비스를 선택하고 "Manual Deploy" > "Deploy latest commit" 클릭

## 로그 확인

Dashboard에서 서비스를 선택하고 "Logs" 탭에서 실시간 로그 확인 가능