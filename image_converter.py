import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from PIL import Image
import threading
from datetime import datetime
import queue

class ImageConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("이미지 일괄 변환기")
        self.root.geometry("500x400")
        
        # 변환 설정
        self.output_format = tk.StringVar(value="jpg")
        self.quality = tk.IntVar(value=85)
        self.max_size = tk.IntVar(value=1920)
        
        # 진행 상태
        self.progress_queue = queue.Queue()
        self.total_files = 0
        self.processed_files = 0
        
        self.setup_ui()
        self.root.after(100, self.check_progress)
    
    def setup_ui(self):
        # 설정 프레임
        settings_frame = ttk.Frame(self.root, padding="10")
        settings_frame.pack(fill=tk.X)
        
        # 출력 형식 선택
        format_label = ttk.Label(settings_frame, text="출력 형식:")
        format_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        formats = [("JPG", "jpg"), ("PNG", "png"), ("WEBP", "webp")]
        for i, (text, value) in enumerate(formats):
            rb = ttk.Radiobutton(settings_frame, text=text, variable=self.output_format, value=value)
            rb.grid(row=0, column=i+1, padx=5)
        
        # 품질 설정 (JPG, WEBP용)
        quality_label = ttk.Label(settings_frame, text="품질:")
        quality_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.quality_scale = ttk.Scale(settings_frame, from_=50, to=100, variable=self.quality, 
                                      orient=tk.HORIZONTAL, length=200)
        self.quality_scale.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        self.quality_value = ttk.Label(settings_frame, text="85%")
        self.quality_value.grid(row=1, column=3, padx=5, pady=5)
        self.quality_scale.configure(command=self.update_quality_label)
        
        # 크기 설정
        size_label = ttk.Label(settings_frame, text="최대 크기 (px):")
        size_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.size_entry = ttk.Entry(settings_frame, textvariable=self.max_size, width=10)
        self.size_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 드래그 앤 드롭 영역
        self.drop_frame = ttk.Frame(self.root, relief=tk.RIDGE, borderwidth=2)
        self.drop_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.drop_label = ttk.Label(self.drop_frame, text="🖼️ 이미지를 여기에\n드래그하세요", 
                                   font=("Arial", 16), anchor=tk.CENTER)
        self.drop_label.pack(expand=True)
        
        # 진행 상태
        self.progress_label = ttk.Label(self.root, text="대기 중...")
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.progress_bar.pack(pady=5)
        
        # 드래그 앤 드롭 설정
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
    
    def update_quality_label(self, value):
        self.quality_value.config(text=f"{int(float(value))}%")
    
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))]
        
        if not image_files:
            messagebox.showwarning("경고", "이미지 파일이 없습니다.")
            return
        
        self.total_files = len(image_files)
        self.processed_files = 0
        self.progress_bar['maximum'] = self.total_files
        self.progress_bar['value'] = 0
        
        # 별도 스레드에서 변환 실행
        thread = threading.Thread(target=self.convert_images, args=(image_files,))
        thread.daemon = True
        thread.start()
    
    def convert_images(self, files):
        # 출력 폴더 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_folder = os.path.join(os.path.dirname(files[0]), f"converted_{timestamp}")
        os.makedirs(output_folder, exist_ok=True)
        
        for file_path in files:
            try:
                self.convert_single_image(file_path, output_folder)
                self.processed_files += 1
                self.progress_queue.put(('progress', self.processed_files))
            except Exception as e:
                self.progress_queue.put(('error', f"{os.path.basename(file_path)}: {str(e)}"))
        
        self.progress_queue.put(('complete', output_folder))
    
    def convert_single_image(self, input_path, output_folder):
        # 이미지 열기
        img = Image.open(input_path)
        
        # RGBA를 RGB로 변환 (JPG용)
        if self.output_format.get() == 'jpg' and img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # 리사이징
        max_size = self.max_size.get()
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # 파일명 생성
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{base_name}.{self.output_format.get()}"
        output_path = os.path.join(output_folder, output_name)
        
        # 저장
        save_kwargs = {}
        if self.output_format.get() in ('jpg', 'jpeg'):
            save_kwargs['quality'] = self.quality.get()
            save_kwargs['optimize'] = True
        elif self.output_format.get() == 'webp':
            save_kwargs['quality'] = self.quality.get()
            save_kwargs['method'] = 6
        
        img.save(output_path, **save_kwargs)
        img.close()
    
    def check_progress(self):
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                
                if msg_type == 'progress':
                    self.progress_bar['value'] = data
                    self.progress_label.config(text=f"처리중: {data}/{self.total_files} 파일")
                
                elif msg_type == 'error':
                    messagebox.showerror("변환 오류", data)
                
                elif msg_type == 'complete':
                    self.progress_label.config(text="변환 완료!")
                    messagebox.showinfo("완료", f"모든 이미지가 변환되었습니다.\n저장 위치: {data}")
                    # 폴더 열기
                    os.startfile(data)
        
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_progress)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageConverter(root)
    root.mainloop()