"""
실시간 한국어 → 베트남어 자막 오버레이
PowerPoint 위에 투명 창으로 자막을 표시합니다.

사용법:
  python app.py

필요 패키지:
  pip install SpeechRecognition deep-translator pyaudio
"""

import threading
import queue
import tkinter as tk
from tkinter import font as tkfont
import speech_recognition as sr
from deep_translator import GoogleTranslator

# ===== 설정 =====
FONT_SIZE_VI = 36          # 베트남어 자막 크기
FONT_SIZE_KO = 18          # 한국어 원문 크기
SUBTITLE_HEIGHT = 150       # 자막 영역 높이 (픽셀)
BG_COLOR = '#1a1a1a'       # 배경색
BG_ALPHA = 0.85            # 배경 투명도 (0~1)
VI_COLOR = '#FFD700'       # 베트남어 텍스트 색상 (금색)
KO_COLOR = '#aaaaaa'       # 한국어 텍스트 색상
ENERGY_THRESHOLD = 300     # 마이크 감도 (낮을수록 민감)
PAUSE_THRESHOLD = 0.8      # 말 끊김 인식 시간 (초)


class TranslationOverlay:
    def __init__(self):
        self.text_queue = queue.Queue()
        self.running = True
        self.translator = GoogleTranslator(source='ko', target='vi')

        self._setup_ui()
        self._start_recognition_thread()

    def _setup_ui(self):
        """투명 오버레이 윈도우 생성"""
        self.root = tk.Tk()
        self.root.title('자막 오버레이')

        # 화면 크기 가져오기
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # 화면 하단에 배치
        window_w = screen_w
        window_h = SUBTITLE_HEIGHT
        x = 0
        y = screen_h - window_h - 40  # 작업표시줄 위

        self.root.geometry(f'{window_w}x{window_h}+{x}+{y}')

        # 항상 최상위
        self.root.attributes('-topmost', True)

        # 플랫폼별 투명도 설정
        try:
            # Windows
            self.root.attributes('-alpha', BG_ALPHA)
        except:
            pass

        # 창 테두리 제거
        self.root.overrideredirect(True)

        # 배경
        self.root.configure(bg=BG_COLOR)

        # 메인 프레임
        frame = tk.Frame(self.root, bg=BG_COLOR)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 한국어 원문 (위)
        self.ko_label = tk.Label(
            frame,
            text='마이크로 말씀하세요...',
            fg=KO_COLOR,
            bg=BG_COLOR,
            font=('Malgun Gothic', FONT_SIZE_KO),
            wraplength=screen_w - 80,
            justify='center'
        )
        self.ko_label.pack(side=tk.TOP, fill=tk.X)

        # 베트남어 번역 (아래, 크게)
        self.vi_label = tk.Label(
            frame,
            text='',
            fg=VI_COLOR,
            bg=BG_COLOR,
            font=('Arial', FONT_SIZE_VI, 'bold'),
            wraplength=screen_w - 80,
            justify='center'
        )
        self.vi_label.pack(side=tk.TOP, fill=tk.X, pady=(5, 0))

        # 상태 표시 (작은 점)
        self.status_dot = tk.Label(
            self.root,
            text='●',
            fg='#555555',
            bg=BG_COLOR,
            font=('Arial', 8)
        )
        self.status_dot.place(x=10, y=5)

        # 닫기 버튼 (오른쪽 상단)
        close_btn = tk.Label(
            self.root,
            text='✕',
            fg='#666666',
            bg=BG_COLOR,
            font=('Arial', 12),
            cursor='hand2'
        )
        close_btn.place(x=screen_w - 30, y=5)
        close_btn.bind('<Button-1>', lambda e: self.stop())

        # 드래그로 이동 가능
        self._drag_data = {'x': 0, 'y': 0}
        self.root.bind('<ButtonPress-1>', self._on_drag_start)
        self.root.bind('<B1-Motion>', self._on_drag_motion)

        # ESC로 종료
        self.root.bind('<Escape>', lambda e: self.stop())

        # 주기적으로 큐 확인
        self.root.after(100, self._check_queue)

    def _on_drag_start(self, event):
        self._drag_data['x'] = event.x
        self._drag_data['y'] = event.y

    def _on_drag_motion(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data['x'])
        y = self.root.winfo_y() + (event.y - self._drag_data['y'])
        self.root.geometry(f'+{x}+{y}')

    def _start_recognition_thread(self):
        """음성인식 스레드 시작"""
        thread = threading.Thread(target=self._recognition_worker, daemon=True)
        thread.start()

    def _recognition_worker(self):
        """백그라운드 음성인식"""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = ENERGY_THRESHOLD
        recognizer.pause_threshold = PAUSE_THRESHOLD
        recognizer.dynamic_energy_threshold = True

        try:
            mic = sr.Microphone()
        except (OSError, AttributeError) as e:
            self.text_queue.put(('error', '마이크를 찾을 수 없습니다', str(e)))
            return

        print('[INFO] 마이크 준비 완료. 말씀하세요...')
        self.text_queue.put(('status', 'active', ''))

        with mic as source:
            # 주변 소음 보정 (2초)
            print('[INFO] 주변 소음 보정 중...')
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print('[INFO] 보정 완료. 음성 인식 시작!')

            while self.running:
                try:
                    # 음성 듣기
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)

                    # Google 음성인식 (무료)
                    try:
                        korean_text = recognizer.recognize_google(audio, language='ko-KR')
                        print(f'[인식] {korean_text}')

                        # 번역
                        try:
                            vietnamese_text = self.translator.translate(korean_text)
                            print(f'[번역] {vietnamese_text}')
                            self.text_queue.put(('result', korean_text, vietnamese_text))
                        except Exception as e:
                            print(f'[번역 오류] {e}')
                            self.text_queue.put(('result', korean_text, '(번역 오류)'))

                    except sr.UnknownValueError:
                        # 음성을 인식하지 못함
                        pass
                    except sr.RequestError as e:
                        print(f'[API 오류] {e}')
                        self.text_queue.put(('error', '인터넷 연결 확인', str(e)))

                except sr.WaitTimeoutError:
                    # 타임아웃 - 계속 대기
                    pass
                except Exception as e:
                    print(f'[오류] {e}')
                    if self.running:
                        continue

    def _check_queue(self):
        """메인 스레드에서 큐 확인 후 UI 업데이트"""
        try:
            while True:
                msg = self.text_queue.get_nowait()
                msg_type = msg[0]

                if msg_type == 'result':
                    _, korean, vietnamese = msg
                    self.ko_label.config(text=korean)
                    self.vi_label.config(text=vietnamese)
                    self.status_dot.config(fg='#4CAF50')
                elif msg_type == 'status':
                    self.status_dot.config(fg='#4CAF50')
                elif msg_type == 'error':
                    _, title, detail = msg
                    self.ko_label.config(text=f'{title}')
                    self.vi_label.config(text=detail)
                    self.status_dot.config(fg='#f44336')

        except queue.Empty:
            pass

        if self.running:
            self.root.after(100, self._check_queue)

    def stop(self):
        """앱 종료"""
        self.running = False
        self.root.destroy()

    def run(self):
        """앱 실행"""
        print('='*50)
        print('  실시간 한국어 → 베트남어 자막 오버레이')
        print('='*50)
        print()
        print('  - 마이크로 한국어를 말하면 베트남어 자막이 표시됩니다')
        print('  - 자막 창을 드래그하여 위치를 이동할 수 있습니다')
        print('  - ESC 또는 ✕ 버튼으로 종료')
        print()

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop()


if __name__ == '__main__':
    app = TranslationOverlay()
    app.run()
