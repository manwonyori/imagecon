from flask import Flask, render_template, request, jsonify, send_file
import os
from PIL import Image
import io
import base64
from datetime import datetime
import zipfile
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'ok', 'message': '서버가 정상 작동 중입니다'})

@app.route('/convert', methods=['POST'])
def convert_images():
    try:
        # JSON 데이터 확인
        if not request.is_json:
            return jsonify({'error': 'JSON 데이터가 필요합니다'}), 400
            
        data = request.json
        if not data:
            return jsonify({'error': '데이터가 없습니다'}), 400
            
        images = data.get('images', [])
        if not images:
            return jsonify({'error': '이미지가 없습니다'}), 400
            
        output_format = data.get('format', 'jpg')
        quality = data.get('quality', 85)
        max_size = data.get('maxSize', 1920)
        resize_mode = data.get('resizeMode', 'fit')
        
        print(f"변환 시작: {len(images)}개 이미지")
        
        converted_images = []
        errors = []
        
        for idx, img_data in enumerate(images):
            img_name = img_data.get('name', f'image_{idx}')
            
            try:
                # Base64 데이터 추출
                base64_str = img_data['data']
                if ',' in base64_str:
                    base64_str = base64_str.split(',')[1]
                
                # 디코딩
                img_content = base64.b64decode(base64_str)
                
                # PIL로 이미지 열기
                img = Image.open(io.BytesIO(img_content))
                
                # RGB 변환 (JPG용)
                if output_format == 'jpg' and img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                
                # 리사이징
                if resize_mode == 'crop1000':
                    # 1000x1000 크롭
                    target_size = 1000
                    img = make_square(img, target_size)
                else:
                    # 비율 유지 리사이징
                    if max(img.size) > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # 저장
                output = io.BytesIO()
                if output_format in ('jpg', 'jpeg'):
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                elif output_format == 'png':
                    img.save(output, format='PNG', optimize=True)
                elif output_format == 'webp':
                    img.save(output, format='WEBP', quality=quality, method=6)
                else:
                    img.save(output, format=output_format.upper())
                
                output.seek(0)
                
                # Base64 인코딩
                base_name = os.path.splitext(img_name)[0]
                if resize_mode == 'crop1000':
                    new_name = f"{base_name}_1000x1000.{output_format}"
                else:
                    new_name = f"{base_name}.{output_format}"
                
                converted_images.append({
                    'name': new_name,
                    'data': base64.b64encode(output.getvalue()).decode(),
                    'size': len(output.getvalue())
                })
                
                img.close()
                print(f"성공: {img_name}")
                
            except Exception as e:
                print(f"실패: {img_name} - {str(e)}")
                errors.append({
                    'name': img_name,
                    'error': str(e)
                })
        
        # 응답
        result = {
            'success': True,
            'images': converted_images,
            'count': len(converted_images),
            'total': len(images)
        }
        
        if errors:
            result['errors'] = errors
            result['errorCount'] = len(errors)
        
        print(f"변환 완료: 성공 {len(converted_images)}, 실패 {len(errors)}")
        return jsonify(result)
        
    except Exception as e:
        print(f"서버 오류: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500

def make_square(img, size):
    """이미지를 정사각형으로 만들기"""
    width, height = img.size
    
    # 이미 정사각형이면
    if width == size and height == size:
        return img
    
    # 작은 이미지는 패딩
    if width <= size and height <= size:
        new_img = Image.new('RGB', (size, size), (255, 255, 255))
        left = (size - width) // 2
        top = (size - height) // 2
        new_img.paste(img, (left, top))
        return new_img
    
    # 큰 이미지는 크롭
    # 짧은 쪽을 size에 맞춤
    if width > height:
        new_height = size
        new_width = int(width * size / height)
    else:
        new_width = size
        new_height = int(height * size / width)
    
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 중앙 크롭
    left = (new_width - size) // 2
    top = (new_height - size) // 2
    right = left + size
    bottom = top + size
    
    return img.crop((left, top, right, bottom))

@app.route('/download-zip', methods=['POST'])
def download_zip():
    try:
        data = request.json
        images = data.get('images', [])
        folder_name = data.get('folderName', 'converted_images')
        
        if not images:
            return jsonify({'error': '이미지가 없습니다'}), 400
        
        # ZIP 파일 생성
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img in images:
                img_data = base64.b64decode(img['data'])
                file_path = f"{folder_name}/{img['name']}"
                zipf.writestr(file_path, img_data)
        
        temp.close()
        
        # 전송
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            temp.name,
            as_attachment=True,
            download_name=f'{folder_name}_{timestamp}.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)