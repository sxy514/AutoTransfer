from autorecorder import InputRecorder
import json
import time


def play_recording(filename, speed=1.0):
    # 创建 InputRecorder 实例, 用来调用回放函数
    recorder = InputRecorder()

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
        events = data['events']

    print(f"准备回放{filename},速度:{speed}x")
    print("3秒后开始回放...")
    time.sleep(3)

    # 开始回放
    recorder.play_events(events, speed)


if __name__ == "__main__":
    recording_file = "recording_20250518_150241.json"
     
    playback_speed = 1

    play_recording(recording_file, playback_speed)
