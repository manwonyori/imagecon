"""
ImageCon v2.0 - Production-ready image converter
Complete error handling, security, and performance optimization
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import io
import base64
import hashlib
import tempfile
import zipfile
import logging
import traceback
from datetime import datetime
from functools import wraps
from threading import Lock
import gc

from PIL import Image, ImageFile, ExifTags
import pillow_heif

# PIL 설정
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 200000000  # 200MP 제한

# HEIF 지원 등록
pillow_heif.register_heif_opener()

# Flask 앱 설정
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['JSON_SORT_KEYS'] = False

# CORS 설정
CORS(app, origins=["*"])

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 전역 변수
processing_lock = Lock()
active_processes = 0
MAX_CONCURRENT_PROCESSES = 5

# 지원 형식
SUPPORTED_INPUT_FORMATS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 
    'tiff', 'tif', 'ico', 'heic', 'heif'
}

SUPPORTED_OUTPUT_FORMATS = {
    'jpg': {'mime': 'image/jpeg', 'pil': 'JPEG'},
    'png': {'mime': 'image/png', 'pil': 'PNG'},
    'webp': {'mime': 'image/webp', 'pil': 'WEBP'}
}

def safe_process(func):
    """데코레이터: 안전한 프로세스 실행"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global active_processes
        
        with processing_lock:
            if active_processes >= MAX_CONCURRENT_PROCESSES:
                return jsonify({
                    'error': '서버가 바쁩니다. 잠시 후 다시 시도해주세요.',
                    'code': 'SERVER_BUSY'
                }), 503
            active_processes += 1
        
        try:
            return func(*args, **kwargs)
        finally:
            with processing_lock:
                active_processes -= 1
            gc.collect()
    
    return wrapper

def validate_image_data(img_data):
    """이미지 데이터 검증"""
    if not img_data:
        return False, "빈 데이터"
    
    if 'name' not in img_data or 'data' not in img_data:
        return False, "필수 필드 누락"
    
    # 파일명 검증
    filename = img_data['name']
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return False, "잘못된 파일명"
    
    # Base64 데이터 검증
    base64_str = img_data['data']
    if not base64_str:
        return False, "이미지 데이터 없음"
    
    # 데이터 크기 추정 (Base64는 원본의 약 1.33배)
    estimated_size = len(base64_str) * 0.75
    if estimated_size > 100 * 1024 * 1024:  # 100MB
        return False, f"파일 크기 초과 ({int(estimated_size / 1024 / 1024)}MB)"
    
    return True, None

def extract_base64(data_str):
    """Base64 데이터 추출"""
    if ',' in data_str:
        return data_str.split(',')[1]
    return data_str

def fix_image_orientation(img):
    """EXIF 기반 이미지 방향 수정"""
    try:
        # EXIF 데이터에서 방향 정보 추출
        exif = img.getexif()
        if exif:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            orientation_value = exif.get(orientation)
            if orientation_value:
                rotations = {
                    3: 180,
                    6: 270,
                    8: 90
                }
                if orientation_value in rotations:
                    img = img.rotate(rotations[orientation_value], expand=True)
    except Exception:
        pass  # EXIF 처리 실패는 무시
    
    return img

def convert_to_rgb(img, output_format):
    """이미지를 RGB로 변환"""
    if output_format == 'png' and img.mode in ('RGBA', 'LA', 'PA'):
        # PNG는 투명도 유지
        return img
    
    if img.mode == 'RGBA' or img.mode == 'LA':
        # 흰색 배경에 합성
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img, mask=img.split()[-1])
        return background
    elif img.mode == 'P':
        # 팔레트 모드
        if 'transparency' in img.info:
            img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            return background
        else:
            return img.convert('RGB')
    elif img.mode != 'RGB':
        return img.convert('RGB')
    
    return img

def make_square(img, size):
    """이미지를 정사각형으로 만들기 (개선된 버전)"""
    width, height = img.size
    
    # 이미 목표 크기인 경우
    if width == size and height == size:
        return img
    
    # 작은 이미지는 패딩
    if width <= size and height <= size:
        # 배경 생성 (투명 지원)
        if img.mode == 'RGBA':
            new_img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        else:
            new_img = Image.new('RGB', (size, size), (255, 255, 255))
        
        # 중앙 정렬
        left = (size - width) // 2
        top = (size - height) // 2
        new_img.paste(img, (left, top))
        return new_img
    
    # 큰 이미지는 스마트 크롭
    # 비율 계산
    scale = size / min(width, height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # 고품질 리사이징
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 중앙 크롭
    left = (new_width - size) // 2
    top = (new_height - size) // 2
    right = left + size
    bottom = top + size
    
    return img.crop((left, top, right, bottom))

def process_single_image(img_data, output_format, quality, max_size, resize_mode):
    """단일 이미지 처리"""
    img_name = img_data.get('name', 'untitled')
    
    try:
        # Base64 디코딩
        base64_str = extract_base64(img_data['data'])
        img_bytes = base64.b64decode(base64_str)
        
        # 이미지 열기
        img = Image.open(io.BytesIO(img_bytes))
        
        # EXIF 방향 수정
        img = fix_image_orientation(img)
        
        # 형식별 변환
        if output_format != 'png':
            img = convert_to_rgb(img, output_format)
        
        # 리사이징
        if resize_mode == 'crop1000':
            img = make_square(img, 1000)
        elif resize_mode == 'fit' and max_size:
            # 비율 유지 리사이징
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # 저장 옵션
        save_kwargs = {
            'format': SUPPORTED_OUTPUT_FORMATS[output_format]['pil'],
            'optimize': True
        }
        
        if output_format == 'jpg':
            save_kwargs['quality'] = quality
            save_kwargs['progressive'] = True
            save_kwargs['subsampling'] = 0  # 최고 품질
        elif output_format == 'png':
            save_kwargs['compress_level'] = 6
        elif output_format == 'webp':
            save_kwargs['quality'] = quality
            save_kwargs['method'] = 6
        
        # 메모리 버퍼에 저장
        output = io.BytesIO()
        img.save(output, **save_kwargs)
        output.seek(0)
        
        # 결과 생성
        base_name = os.path.splitext(img_name)[0]
        suffix = '_1000x1000' if resize_mode == 'crop1000' else ''
        new_name = f"{base_name}{suffix}.{output_format}"
        
        result = {
            'name': new_name,
            'data': base64.b64encode(output.getvalue()).decode(),
            'size': len(output.getvalue()),
            'width': img.width,
            'height': img.height
        }
        
        # 메모리 정리
        img.close()
        output.close()
        del img, output
        
        logger.info(f"성공: {img_name} -> {new_name} ({result['size']} bytes)")
        return True, result
        
    except Exception as e:
        logger.error(f"실패: {img_name} - {str(e)}\n{traceback.format_exc()}")
        return False, f"처리 오류: {str(e)}"

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index_v2.html')

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0',
        'active_processes': active_processes,
        'max_processes': MAX_CONCURRENT_PROCESSES,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/convert', methods=['POST'])
@limiter.limit("30 per minute")
@safe_process
def convert_images():
    """이미지 변환 API"""
    try:
        # 요청 검증
        if not request.is_json:
            return jsonify({'error': 'JSON 형식이 필요합니다', 'code': 'INVALID_FORMAT'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': '데이터가 없습니다', 'code': 'NO_DATA'}), 400
        
        # 파라미터 추출
        images = data.get('images', [])
        if not images:
            return jsonify({'error': '이미지가 없습니다', 'code': 'NO_IMAGES'}), 400
        
        if len(images) > 50:
            return jsonify({'error': '최대 50개까지 처리 가능합니다', 'code': 'TOO_MANY_IMAGES'}), 400
        
        output_format = data.get('format', 'jpg').lower()
        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            return jsonify({
                'error': f'지원하지 않는 출력 형식: {output_format}',
                'code': 'UNSUPPORTED_FORMAT',
                'supported': list(SUPPORTED_OUTPUT_FORMATS.keys())
            }), 400
        
        quality = max(1, min(100, int(data.get('quality', 85))))
        max_size = max(100, min(10000, int(data.get('maxSize', 1920))))
        resize_mode = data.get('resizeMode', 'fit')
        
        logger.info(f"변환 시작: {len(images)}개, {output_format}, Q{quality}, {resize_mode}")
        
        # 이미지 처리
        results = []
        errors = []
        
        for idx, img_data in enumerate(images):
            # 검증
            valid, error_msg = validate_image_data(img_data)
            if not valid:
                errors.append({
                    'index': idx,
                    'name': img_data.get('name', f'image_{idx}'),
                    'error': error_msg
                })
                continue
            
            # 처리
            success, result = process_single_image(
                img_data, output_format, quality, max_size, resize_mode
            )
            
            if success:
                results.append(result)
            else:
                errors.append({
                    'index': idx,
                    'name': img_data.get('name', f'image_{idx}'),
                    'error': result
                })
        
        # 응답 생성
        response = {
            'success': len(results) > 0,
            'images': results,
            'processed': len(results),
            'total': len(images),
            'timestamp': datetime.now().isoformat()
        }
        
        if errors:
            response['errors'] = errors
            response['failed'] = len(errors)
        
        # 일부 성공
        if results and errors:
            response['message'] = f"{len(results)}개 성공, {len(errors)}개 실패"
        
        logger.info(f"변환 완료: {len(results)}/{len(images)} 성공")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"서버 오류: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': '서버 오류가 발생했습니다',
            'code': 'SERVER_ERROR',
            'detail': str(e) if app.debug else None
        }), 500

@app.route('/download-zip', methods=['POST'])
@limiter.limit("10 per minute")
def download_zip():
    """ZIP 다운로드"""
    try:
        data = request.json
        images = data.get('images', [])
        folder_name = data.get('folderName', 'converted_images')
        
        # 검증
        if not images:
            return jsonify({'error': '이미지가 없습니다'}), 400
        
        if len(images) > 100:
            return jsonify({'error': '최대 100개까지 다운로드 가능합니다'}), 400
        
        # 안전한 폴더명
        safe_folder = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_'))[:50]
        if not safe_folder:
            safe_folder = 'images'
        
        # ZIP 생성
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp.name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for idx, img in enumerate(images):
                    try:
                        # 안전한 파일명
                        filename = img.get('name', f'image_{idx}.jpg')
                        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
                        
                        # 디코딩 및 저장
                        img_data = base64.b64decode(img['data'])
                        file_path = f"{safe_folder}/{safe_filename}"
                        zipf.writestr(file_path, img_data)
                        
                    except Exception as e:
                        logger.error(f"ZIP 추가 실패: {filename} - {str(e)}")
                        continue
            
            temp.close()
            
            # 전송
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_name = f'{safe_folder}_{timestamp}.zip'
            
            return send_file(
                temp.name,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/zip'
            )
            
        finally:
            # 임시 파일 삭제
            try:
                os.unlink(temp.name)
            except:
                pass
                
    except Exception as e:
        logger.error(f"ZIP 생성 오류: {str(e)}")
        return jsonify({'error': 'ZIP 생성 실패', 'detail': str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(e):
    """파일 크기 초과 에러"""
    return jsonify({
        'error': '요청 크기가 너무 큽니다 (최대 500MB)',
        'code': 'REQUEST_TOO_LARGE'
    }), 413

@app.errorhandler(429)
def ratelimit_handler(e):
    """요청 제한 초과"""
    return jsonify({
        'error': '너무 많은 요청입니다. 잠시 후 다시 시도해주세요.',
        'code': 'RATE_LIMIT_EXCEEDED',
        'retry_after': e.description
    }), 429

@app.errorhandler(500)
def internal_error(e):
    """내부 서버 오류"""
    logger.error(f"Internal error: {str(e)}")
    return jsonify({
        'error': '서버 오류가 발생했습니다',
        'code': 'INTERNAL_ERROR'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)