from PIL import Image
import os

def test_image_processing():
    """로컬에서 이미지 처리 테스트"""
    
    # 테스트 이미지 생성
    test_cases = [
        ("test_jpg_large.jpg", (2000, 1500), "RGB"),
        ("test_jpg_small.jpg", (800, 600), "RGB"),
        ("test_png_rgba.png", (1200, 1200), "RGBA"),
        ("test_png_small.png", (500, 400), "RGB"),
    ]
    
    # 테스트 이미지 생성
    for filename, size, mode in test_cases:
        if mode == "RGBA":
            img = Image.new(mode, size, (255, 0, 0, 128))
        else:
            img = Image.new(mode, size, (255, 0, 0))
        img.save(filename)
        print(f"Created: {filename} - {size} - {mode}")
    
    # 1000x1000 크롭 테스트
    print("\n=== 1000x1000 크롭 테스트 ===")
    for filename, _, _ in test_cases:
        img = Image.open(filename)
        print(f"\n원본: {filename} - {img.size}")
        
        # 크롭 로직 테스트
        img_width, img_height = img.size
        
        if img_width <= 1000 and img_height <= 1000:
            print("→ 패딩 추가")
            new_img = Image.new('RGB', (1000, 1000), (255, 255, 255))
            left = (1000 - img_width) // 2
            top = (1000 - img_height) // 2
            if img.mode == 'RGBA':
                new_img.paste(img, (left, top), img)
            else:
                new_img.paste(img, (left, top))
            result = new_img
        else:
            print("→ 중앙 크롭")
            if img_width > img_height:
                new_width = int(1000 * img_width / img_height)
                new_height = 1000
            else:
                new_width = 1000
                new_height = int(1000 * img_height / img_width)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            left = (new_width - 1000) // 2
            top = (new_height - 1000) // 2
            right = left + 1000
            bottom = top + 1000
            result = img_resized.crop((left, top, right, bottom))
        
        output_name = f"output_1000x1000_{filename}"
        result.save(output_name)
        print(f"결과: {output_name} - {result.size}")
    
    # 테스트 파일 정리
    print("\n=== 테스트 파일 정리 ===")
    for filename, _, _ in test_cases:
        os.remove(filename)
        output_name = f"output_1000x1000_{filename}"
        if os.path.exists(output_name):
            os.remove(output_name)
        print(f"Cleaned: {filename}")

if __name__ == "__main__":
    test_image_processing()