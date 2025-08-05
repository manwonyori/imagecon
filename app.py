from flask import Flask, render_template, request, jsonify, send_file
import os
from PIL import Image
import io
import base64
from datetime import datetime
import zipfile
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_images():
    try:
        data = request.json
        images = data.get('images', [])
        output_format = data.get('format', 'jpg')
        quality = data.get('quality', 85)
        max_size = data.get('maxSize', 1920)
        resize_mode = data.get('resizeMode', 'fit')  # 'fit', 'crop1000'
        
        if not images:
            return jsonify({'error': '이미지가 없습니다'}), 400
        
        converted_images = []
        
        for img_data in images:
            # Base64 디코딩
            img_name = img_data['name']
            img_content = base64.b64decode(img_data['data'].split(',')[1])
            
            # PIL로 이미지 열기
            img = Image.open(io.BytesIO(img_content))
            
            # RGBA를 RGB로 변환 (JPG용)
            if output_format == 'jpg' and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # 리사이징 모드에 따른 처리
            if resize_mode == 'crop1000':
                # 1000x1000 정사각형으로 크롭
                # 먼저 짧은 쪽이 1000px이 되도록 리사이즈
                img_width, img_height = img.size
                if img_width > img_height:
                    new_width = int(1000 * img_width / img_height)
                    new_height = 1000
                else:
                    new_width = 1000
                    new_height = int(1000 * img_height / img_width)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 중앙에서 1000x1000 크롭
                left = (new_width - 1000) // 2
                top = (new_height - 1000) // 2
                right = left + 1000
                bottom = top + 1000
                img = img.crop((left, top, right, bottom))
            else:
                # 기존 방식: 비율 유지하며 리사이징
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 메모리에 저장
            output = io.BytesIO()
            save_kwargs = {}
            
            if output_format in ('jpg', 'jpeg'):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif output_format == 'webp':
                save_kwargs['quality'] = quality
                save_kwargs['method'] = 6
            
            img.save(output, format=output_format.upper(), **save_kwargs)
            output.seek(0)
            
            # Base64로 인코딩하여 반환
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
        
        return jsonify({
            'success': True,
            'images': converted_images,
            'count': len(converted_images)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-zip', methods=['POST'])
def download_zip():
    try:
        data = request.json
        images = data.get('images', [])
        folder_name = data.get('folderName', 'converted_images')
        
        if not images:
            return jsonify({'error': '이미지가 없습니다'}), 400
        
        # 임시 ZIP 파일 생성
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 폴더 구조로 저장
            for img in images:
                img_data = base64.b64decode(img['data'])
                # 폴더명/파일명 형태로 저장
                file_path = f"{folder_name}/{img['name']}"
                zipf.writestr(file_path, img_data)
        
        temp.close()
        
        # ZIP 파일 전송
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'{folder_name}_{timestamp}.zip'
        
        return send_file(
            temp.name,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-individual/<filename>', methods=['POST'])
def download_individual(filename):
    try:
        data = request.json
        img_data = base64.b64decode(data['data'])
        
        # 메모리에서 직접 전송
        return send_file(
            io.BytesIO(img_data),
            as_attachment=True,
            download_name=filename,
            mimetype=f'image/{filename.split(".")[-1]}'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)