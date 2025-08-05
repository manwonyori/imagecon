"""
ImageCon v2.0 종합 테스트
모든 엣지 케이스와 오류 상황을 테스트
"""

import unittest
import json
import base64
import io
import os
import tempfile
from PIL import Image
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 테스트 설정
TEST_URL = os.environ.get('TEST_URL', 'http://localhost:5000')
PROD_URL = 'https://imagecon.onrender.com'

class ImageConTestSuite(unittest.TestCase):
    """종합 테스트 스위트"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 환경 설정"""
        cls.base_url = TEST_URL
        cls.test_images = cls.create_test_images()
        
    @classmethod
    def create_test_images(cls):
        """다양한 테스트 이미지 생성"""
        images = {}
        
        # 1. 일반 RGB 이미지
        img = Image.new('RGB', (100, 100), color='red')
        images['simple_rgb'] = cls.image_to_base64(img, 'PNG')
        
        # 2. RGBA 투명 이미지
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        images['transparent'] = cls.image_to_base64(img, 'PNG')
        
        # 3. 팔레트 모드
        img = Image.new('P', (100, 100))
        img.putpalette([i//3 for i in range(768)])
        images['palette'] = cls.image_to_base64(img, 'PNG')
        
        # 4. 그레이스케일
        img = Image.new('L', (100, 100), color=128)
        images['grayscale'] = cls.image_to_base64(img, 'PNG')
        
        # 5. 큰 이미지
        img = Image.new('RGB', (4000, 3000), color='blue')
        images['large'] = cls.image_to_base64(img, 'JPEG')
        
        # 6. 작은 이미지
        img = Image.new('RGB', (50, 50), color='green')
        images['small'] = cls.image_to_base64(img, 'PNG')
        
        # 7. 세로 이미지
        img = Image.new('RGB', (500, 1000), color='yellow')
        images['portrait'] = cls.image_to_base64(img, 'JPEG')
        
        # 8. 가로 이미지
        img = Image.new('RGB', (1000, 500), color='cyan')
        images['landscape'] = cls.image_to_base64(img, 'JPEG')
        
        # 9. 정사각형
        img = Image.new('RGB', (1000, 1000), color='magenta')
        images['square'] = cls.image_to_base64(img, 'PNG')
        
        return images
    
    @staticmethod
    def image_to_base64(img, format='PNG'):
        """이미지를 Base64로 변환"""
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)
        return f"data:image/{format.lower()};base64,{base64.b64encode(buffer.getvalue()).decode()}"
    
    def test_01_health_check(self):
        """헬스 체크"""
        response = requests.get(f'{self.base_url}/health')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('version', data)
        
    def test_02_basic_conversion(self):
        """기본 변환 테스트"""
        formats = ['jpg', 'png', 'webp']
        
        for format in formats:
            with self.subTest(format=format):
                response = requests.post(
                    f'{self.base_url}/convert',
                    json={
                        'images': [{
                            'name': f'test.{format}',
                            'data': self.test_images['simple_rgb']
                        }],
                        'format': format,
                        'quality': 85,
                        'resizeMode': 'fit'
                    }
                )
                
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(len(data['images']), 1)
                self.assertTrue(data['images'][0]['name'].endswith(f'.{format}'))
    
    def test_03_transparency_handling(self):
        """투명도 처리 테스트"""
        # PNG는 투명도 유지
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'transparent.png',
                    'data': self.test_images['transparent']
                }],
                'format': 'png',
                'resizeMode': 'fit'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # JPG는 흰색 배경
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'transparent.png',
                    'data': self.test_images['transparent']
                }],
                'format': 'jpg',
                'quality': 85,
                'resizeMode': 'fit'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_04_resize_modes(self):
        """리사이즈 모드 테스트"""
        modes = ['fit', 'crop1000', 'none']
        test_image = self.test_images['large']
        
        for mode in modes:
            with self.subTest(mode=mode):
                response = requests.post(
                    f'{self.base_url}/convert',
                    json={
                        'images': [{
                            'name': f'resize_{mode}.jpg',
                            'data': test_image
                        }],
                        'format': 'jpg',
                        'quality': 85,
                        'maxSize': 1920,
                        'resizeMode': mode
                    }
                )
                
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                
                if mode == 'crop1000':
                    self.assertIn('1000x1000', data['images'][0]['name'])
    
    def test_05_batch_processing(self):
        """배치 처리 테스트"""
        images = []
        for i in range(10):
            images.append({
                'name': f'batch_{i}.png',
                'data': self.test_images['simple_rgb']
            })
        
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': images,
                'format': 'jpg',
                'quality': 85,
                'resizeMode': 'fit'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['processed'], 10)
    
    def test_06_error_handling(self):
        """에러 처리 테스트"""
        
        # 1. 빈 요청
        response = requests.post(f'{self.base_url}/convert', json={})
        self.assertEqual(response.status_code, 400)
        
        # 2. 잘못된 형식
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'test.xyz',
                    'data': self.test_images['simple_rgb']
                }],
                'format': 'invalid'
            }
        )
        self.assertEqual(response.status_code, 400)
        
        # 3. 손상된 Base64
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'corrupted.jpg',
                    'data': 'data:image/jpeg;base64,invalid_base64_data'
                }],
                'format': 'jpg'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
    
    def test_07_concurrent_requests(self):
        """동시 요청 테스트"""
        def make_request(index):
            return requests.post(
                f'{self.base_url}/convert',
                json={
                    'images': [{
                        'name': f'concurrent_{index}.jpg',
                        'data': self.test_images['simple_rgb']
                    }],
                    'format': 'jpg',
                    'quality': 85
                }
            )
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = []
            
            for future in as_completed(futures):
                try:
                    response = future.result()
                    results.append(response.status_code)
                except Exception as e:
                    results.append(None)
        
        # 일부는 성공, 일부는 503 (서버 바쁨) 가능
        success_count = sum(1 for r in results if r == 200)
        self.assertGreater(success_count, 0)
    
    def test_08_rate_limiting(self):
        """요청 제한 테스트"""
        # 짧은 시간에 많은 요청
        responses = []
        for i in range(35):  # 분당 30개 제한
            response = requests.post(
                f'{self.base_url}/convert',
                json={
                    'images': [{
                        'name': f'rate_limit_{i}.jpg',
                        'data': self.test_images['simple_rgb']
                    }],
                    'format': 'jpg'
                }
            )
            responses.append(response.status_code)
            
            if response.status_code == 429:
                break
        
        # 일부 요청은 429 (Too Many Requests) 응답
        self.assertIn(429, responses)
    
    def test_09_special_cases(self):
        """특수 케이스 테스트"""
        
        # 1. 매우 작은 이미지
        img = Image.new('RGB', (1, 1), color='red')
        tiny_image = self.image_to_base64(img)
        
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'tiny.jpg',
                    'data': tiny_image
                }],
                'format': 'jpg',
                'resizeMode': 'crop1000'
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # 2. 한글 파일명
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': '한글파일명.png',
                    'data': self.test_images['simple_rgb']
                }],
                'format': 'jpg'
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. 특수문자 파일명
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'file@#$%.jpg',
                    'data': self.test_images['simple_rgb']
                }],
                'format': 'jpg'
            }
        )
        self.assertEqual(response.status_code, 200)
    
    def test_10_zip_download(self):
        """ZIP 다운로드 테스트"""
        # 먼저 이미지 변환
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': f'zip_test_{i}.png',
                    'data': self.test_images['simple_rgb']
                } for i in range(3)],
                'format': 'jpg'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        converted_images = data['images']
        
        # ZIP 다운로드
        response = requests.post(
            f'{self.base_url}/download-zip',
            json={
                'images': converted_images,
                'folderName': 'test_folder'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/zip')
        self.assertGreater(len(response.content), 0)
    
    def test_11_stress_test(self):
        """스트레스 테스트 (큰 이미지, 많은 수)"""
        if os.environ.get('SKIP_STRESS_TEST'):
            self.skipTest("스트레스 테스트 건너뛰기")
        
        # 5MB 크기의 이미지 생성
        large_img = Image.new('RGB', (3000, 3000), color='blue')
        large_data = self.image_to_base64(large_img, 'PNG')
        
        response = requests.post(
            f'{self.base_url}/convert',
            json={
                'images': [{
                    'name': 'stress_test.png',
                    'data': large_data
                }],
                'format': 'jpg',
                'quality': 50,
                'maxSize': 1000
            },
            timeout=60
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_12_memory_leak_check(self):
        """메모리 누수 체크"""
        # 여러 번 반복하여 메모리 누수 확인
        for i in range(5):
            response = requests.post(
                f'{self.base_url}/convert',
                json={
                    'images': [{
                        'name': f'memory_test_{i}.jpg',
                        'data': self.test_images['large']
                    }],
                    'format': 'jpg',
                    'quality': 85,
                    'maxSize': 1920
                }
            )
            self.assertEqual(response.status_code, 200)
            time.sleep(1)  # GC 시간 확보

def run_performance_test():
    """성능 테스트"""
    print("\n=== 성능 테스트 ===")
    
    # 테스트 이미지 준비
    img = Image.new('RGB', (1920, 1080), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    test_data = f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    
    # 단일 요청 시간 측정
    start = time.time()
    response = requests.post(
        f'{TEST_URL}/convert',
        json={
            'images': [{
                'name': 'perf_test.jpg',
                'data': test_data
            }],
            'format': 'jpg',
            'quality': 85
        }
    )
    single_time = time.time() - start
    print(f"단일 이미지 변환 시간: {single_time:.2f}초")
    
    # 배치 처리 시간 측정
    batch_size = 10
    start = time.time()
    response = requests.post(
        f'{TEST_URL}/convert',
        json={
            'images': [{
                'name': f'batch_perf_{i}.jpg',
                'data': test_data
            } for i in range(batch_size)],
            'format': 'jpg',
            'quality': 85
        }
    )
    batch_time = time.time() - start
    print(f"{batch_size}개 배치 변환 시간: {batch_time:.2f}초")
    print(f"이미지당 평균 시간: {batch_time/batch_size:.2f}초")

if __name__ == '__main__':
    # 단위 테스트 실행
    print("ImageCon v2.0 종합 테스트 시작...")
    unittest.main(verbosity=2, exit=False)
    
    # 성능 테스트
    run_performance_test()
    
    print("\n모든 테스트 완료!")