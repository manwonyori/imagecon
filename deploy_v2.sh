#!/bin/bash
# ImageCon v2.0 배포 스크립트

echo "🚀 ImageCon v2.0 배포 시작..."

# 백업
echo "📦 기존 파일 백업..."
cp app.py app_v1_backup.py
cp templates/index.html templates/index_v1_backup.html
cp requirements.txt requirements_v1_backup.txt

# v2 파일로 교체
echo "🔄 v2.0 파일로 교체..."
cp app_v2.py app.py
cp templates/index_v2.html templates/index.html
cp requirements_v2.txt requirements.txt

# Git 커밋
echo "📝 Git 커밋..."
git add -A
git commit -m "Deploy ImageCon v2.0 - Production ready version

Major improvements:
- Complete error handling for all edge cases
- Support for HEIC/HEIF formats
- Memory optimization and GC
- Rate limiting and concurrent request handling
- Enhanced security with input validation
- Better UX with progressive upload
- Offline support preparation
- Comprehensive test suite
- Performance optimizations"

# 푸시
echo "⬆️ GitHub에 푸시..."
git push origin master

echo "✅ 배포 완료! Render가 자동으로 새 버전을 배포합니다."
echo "📊 배포 상태: https://dashboard.render.com"