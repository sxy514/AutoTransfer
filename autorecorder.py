from pynput import mouse, keyboard
from datetime import datetime
import json
import time
import os
import glob

class InputRecorder:
    # 控制字符到可读键名的映射
    CONTROL_CHAR_MAP = {
        '\x00': 'Ctrl+@', '\x01': 'Ctrl+A', '\x02': 'Ctrl+B', '\x03': 'Ctrl+C',
        '\x04': 'Ctrl+D', '\x05': 'Ctrl+E', '\x06': 'Ctrl+F', '\x07': 'Ctrl+G',
        '\x08': 'Backspace', '\t': 'Tab', '\n': 'Enter', '\x0b': 'Ctrl+K',
        '\x0c': 'Ctrl+L', '\r': 'Enter', '\x0e': 'Ctrl+N', '\x0f': 'Ctrl+O',
        '\x10': 'Ctrl+P', '\x11': 'Ctrl+Q', '\x12': 'Ctrl+R', '\x13': 'Ctrl+S',
        '\x14': 'Ctrl+T', '\x15': 'Ctrl+U', '\x16': 'Ctrl+V', '\x17': 'Ctrl+W',
        '\x18': 'Ctrl+X', '\x19': 'Ctrl+Y', '\x1a': 'Ctrl+Z', '\x1b': 'Esc',
        '\x1c': 'Ctrl+\\', '\x1d': 'Ctrl+]', '\x1e': 'Ctrl+6', '\x1f': 'Ctrl+/',
        '\x7f': 'Backspace'
    }

    def __init__(self):
        self.events = []
        self.is_recording = False
        self.start_time = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.controller = mouse.Controller()
        self.key_controller = keyboard.Controller()
        self.modifier_keys = {
            'ctrl': False,
            'alt': False,
            'shift': False,
            'cmd': False
        }
        self.current_modifiers = set()

        # 鼠标拖拽状态跟踪
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_button = None
        self.last_move_time = 0
        self.move_threshold = 5  # 移动阈值，避免微小移动被记录

    def get_key_name(self, key):
        """获取可读的键名，处理控制字符"""
        if isinstance(key, str) and key in self.CONTROL_CHAR_MAP:
            return self.CONTROL_CHAR_MAP[key]
        return str(key)

    def update_modifier(self, key, is_pressed):
        """更新修饰键状态"""
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.modifier_keys['ctrl'] = is_pressed
        elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r or key == keyboard.Key.alt_gr:
            self.modifier_keys['alt'] = is_pressed
        elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self.modifier_keys['shift'] = is_pressed
        elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
            self.modifier_keys['cmd'] = is_pressed

        # 更新当前按下的修饰键集合
        self.current_modifiers = {k for k, v in self.modifier_keys.items() if v}

    def get_current_modifiers(self):
        """获取当前按下的修饰键"""
        return list(self.current_modifiers)

    def format_key_event(self, key, event_type):
        """格式化按键事件为可读字符串"""
        key_str = self.get_key_name(key)

        # 如果是控制字符，直接返回转换后的键名
        if key in self.CONTROL_CHAR_MAP:
            return key_str

        # 处理修饰键
        modifiers = self.get_current_modifiers()
        if modifiers:
            return '+'.join(modifiers) + '+' + key_str
        return key_str

    def on_move(self, x, y):
        """处理鼠标移动事件"""
        if not self.is_recording or not self.is_dragging:
            return

        current_time = time.time()

        # 检查是否达到移动阈值或时间间隔
        if self.drag_start_pos:
            dx = abs(x - self.drag_start_pos[0])
            dy = abs(y - self.drag_start_pos[1])
            time_since_last = current_time - self.last_move_time

            if dx > self.move_threshold or dy > self.move_threshold or time_since_last > 0.1:
                event = {
                    'type': 'mouse_drag',
                    'x': x,
                    'y': y,
                    'button': str(self.drag_button),
                    'modifiers': self.get_current_modifiers(),
                    'timestamp': current_time - self.start_time
                }
                self.events.append(event)

                # 更新最后位置和时间
                self.drag_start_pos = (x, y)
                self.last_move_time = current_time

                # 显示拖拽信息
                mod_text = '+'.join(self.get_current_modifiers()) + '+' if self.get_current_modifiers() else ''
                print(f"Mouse {mod_text}{self.drag_button} dragged to ({x}, {y})")

    def on_click(self, x, y, button, pressed):
        if not self.is_recording:
            return

        # 更新拖拽状态
        if pressed:
            self.is_dragging = True
            self.drag_start_pos = (x, y)
            self.drag_button = button
            self.last_move_time = time.time()
        else:
            # 如果之前是拖拽状态，记录拖拽结束
            if self.is_dragging and self.drag_start_pos:
                end_pos = (x, y)
                if end_pos != self.drag_start_pos:  # 如果位置有变化，记录拖拽结束
                    event = {
                        'type': 'mouse_drag_end',
                        'start_x': self.drag_start_pos[0],
                        'start_y': self.drag_start_pos[1],
                        'end_x': end_pos[0],
                        'end_y': end_pos[1],
                        'button': str(button),
                        'modifiers': self.get_current_modifiers(),
                        'timestamp': time.time() - self.start_time
                    }
                    self.events.append(event)

                    # 显示拖拽结束信息
                    mod_text = '+'.join(self.get_current_modifiers()) + '+' if self.get_current_modifiers() else ''
                    print(f"Mouse {mod_text}{button} drag ended from {self.drag_start_pos} to {end_pos}")

            self.is_dragging = False
            self.drag_start_pos = None

        # 记录点击事件
        modifiers = self.get_current_modifiers()
        event = {
            'type': 'mouse',
            'event': 'pressed' if pressed else 'released',
            'button': str(button),
            'x': x,
            'y': y,
            'modifiers': modifiers,
            'timestamp': time.time() - self.start_time
        }
        self.events.append(event)

        # 显示可读的鼠标事件
        action = 'pressed' if pressed else 'released'
        mod_text = '+'.join(modifiers) + '+' if modifiers else ''
        print(f"Mouse {mod_text}{button} {action} at ({x}, {y})")

    def on_scroll(self, x, y, dx, dy):
        if not self.is_recording:
            return

        modifiers = self.get_current_modifiers()

        event = {
            'type': 'mouse_scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'modifiers': modifiers,
            'timestamp': time.time() - self.start_time
        }
        self.events.append(event)

        # 显示可读的滚轮事件
        mod_text = '+'.join(modifiers) + '+' if modifiers else ''
        direction = 'down' if dy < 0 else 'up'
        print(f"Mouse {mod_text}scrolled {direction} at ({x}, {y})")

    def on_press(self, key):
        if not self.is_recording:
            return

        # 更新修饰键状态
        self.update_modifier(key, True)

        # 检查是否是停止录制的组合键 (Ctrl+ESC)
        if key == keyboard.Key.esc and self.modifier_keys['ctrl']:
            self.stop_recording()
            return False

        # 忽略单独的修饰键按下事件（在on_release中处理）
        if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                  keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr,
                  keyboard.Key.shift_l, keyboard.Key.shift_r,
                  keyboard.Key.cmd, keyboard.Key.cmd_r]:
            return

        try:
            key_char = key.char
        except AttributeError:
            key_char = str(key)

        modifiers = self.get_current_modifiers()

        # 记录原始键值和处理后的键名
        event = {
            'type': 'keyboard',
            'event': 'pressed',
            'key': key_char,
            'key_display': self.format_key_event(key_char, 'pressed'),
            'modifiers': modifiers,
            'timestamp': time.time() - self.start_time
        }
        self.events.append(event)

        # 显示可读的按键事件
        print(f"Key {event['key_display']} pressed")

    def on_release(self, key):
        if not self.is_recording:
            return

        # 更新修饰键状态
        self.update_modifier(key, False)

        # 忽略单独的修饰键释放事件
        if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                  keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr,
                  keyboard.Key.shift_l, keyboard.Key.shift_r,
                  keyboard.Key.cmd, keyboard.Key.cmd_r]:
            return

        try:
            key_char = key.char
        except AttributeError:
            key_char = str(key)

        modifiers = self.get_current_modifiers()

        event = {
            'type': 'keyboard',
            'event': 'released',
            'key': key_char,
            'key_display': self.format_key_event(key_char, 'released'),
            'modifiers': modifiers,
            'timestamp': time.time() - self.start_time
        }
        self.events.append(event)

        # 显示可读的释放事件
        print(f"Key {event['key_display']} released")

    def start_recording(self):
        self.events = []
        self.is_recording = True
        self.modifier_keys = {k: False for k in self.modifier_keys}
        self.current_modifiers = set()
        self.start_time = time.time()
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_button = None
        self.last_move_time = 0

        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.mouse_listener.start()

        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.keyboard_listener.start()

        print("\n=== 开始录制 ===")
        print("操作完成后按 Ctrl+ESC 键停止录制")

        self.keyboard_listener.join()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.recording_file = f"recording_{timestamp}.json"

        with open(self.recording_file, 'w', encoding='utf-8') as f:
            json.dump({
                'start_time': self.start_time,
                'events': self.events
            }, f, indent=2, ensure_ascii=False)

        print(f"\n录制已保存到: {self.recording_file}")
        print(f"总录制事件数: {len(self.events)}")
        return self.recording_file

    def load_recording(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['events']

    def play_events(self, events, speed=1.0):
        print("\n=== 开始回放 ===")
        print("按 ESC 键可随时停止回放")

        self.stop_playback = False

        def on_press(key):
            if key == keyboard.Key.esc:
                self.stop_playback = True
                return False

        # Start a listener for the ESC key
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        try:
            start_time = time.time()
            last_timestamp = 0

            for i, event in enumerate(events):
                if self.stop_playback:
                    print("\n回放已停止")
                    break

                # Calculate delay based on timestamps
                current_timestamp = event['timestamp']
                delay = (current_timestamp - last_timestamp) / speed
                if delay > 0:
                    time.sleep(delay)
                last_timestamp = current_timestamp

                # 处理修饰键
                modifiers = event.get('modifiers', [])

                if event['type'] == 'mouse':
                    x, y = event['x'], event['y']
                    button = event['button']

                    # Move mouse to position
                    self.controller.position = (x, y)

                    # Convert string back to Button
                    button_map = {
                        "Button.left": mouse.Button.left,
                        "Button.right": mouse.Button.right,
                        "Button.middle": mouse.Button.middle
                    }

                    if event['event'] == 'pressed':
                        self.controller.press(button_map.get(button, mouse.Button.left))
                        mod_text = '+'.join(modifiers) + '+' if modifiers else ''
                        print(f"Mouse {mod_text}{button} pressed at ({x}, {y})")
                    else:
                        self.controller.release(button_map.get(button, mouse.Button.left))
                        mod_text = '+'.join(modifiers) + '+' if modifiers else ''
                        print(f"Mouse {mod_text}{button} released at ({x}, {y})")

                elif event['type'] == 'mouse_drag':
                    x, y = event['x'], event['y']
                    button = event['button']

                    # 移动鼠标到新位置
                    self.controller.position = (x, y)

                    # 显示拖拽信息
                    mod_text = '+'.join(modifiers) + '+' if modifiers else ''
                    print(f"Mouse {mod_text}{button} dragged to ({x}, {y})")

                elif event['type'] == 'mouse_drag_end':
                    start_x, start_y = event['start_x'], event['start_y']
                    end_x, end_y = event['end_x'], event['end_y']
                    button = event['button']

                    # 移动鼠标到结束位置
                    self.controller.position = (end_x, end_y)

                    # 显示拖拽结束信息
                    mod_text = '+'.join(modifiers) + '+' if modifiers else ''
                    print(f"Mouse {mod_text}{button} drag ended from ({start_x}, {start_y}) to ({end_x}, {end_y})")

                elif event['type'] == 'mouse_scroll':
                    x, y = event['x'], event['y']
                    dx, dy = event['dx'], event['dy']

                    # Move mouse to position and scroll
                    self.controller.position = (x, y)
                    self.controller.scroll(dx, dy)
                    mod_text = '+'.join(modifiers) + '+' if modifiers else ''
                    direction = 'down' if dy < 0 else 'up'
                    print(f"Mouse {mod_text}scrolled {direction} at ({x}, {y})")

                elif event['type'] == 'keyboard':
                    key = event['key']
                    key_display = event.get('key_display', str(key))

                    # 处理特殊键
                    key_obj = None
                    if key.startswith('Key.'):
                        key_name = key.split('.')[1]
                        key_obj = getattr(keyboard.Key, key_name, None)

                    # 处理组合键
                    if event['event'] == 'pressed':
                        try:
                            # 先按下修饰键
                            for mod in modifiers:
                                if mod == 'ctrl':
                                    self.key_controller.press(keyboard.Key.ctrl)
                                elif mod == 'alt':
                                    self.key_controller.press(keyboard.Key.alt)
                                elif mod == 'shift':
                                    self.key_controller.press(keyboard.Key.shift)
                                elif mod == 'cmd':
                                    self.key_controller.press(keyboard.Key.cmd)

                            # 按下主键
                            if key_obj:
                                self.key_controller.press(key_obj)
                            else:
                                # 处理控制字符
                                if key in self.CONTROL_CHAR_MAP:
                                    # 对于控制字符，直接发送原始键值
                                    self.key_controller.press(key)
                                else:
                                    self.key_controller.press(key)

                            print(f"Key pressed: {key_display}")

                        except Exception as e:
                            print(f"无法模拟按键 {key_display}: {e}")
                    else:  # released
                        try:
                            # 释放主键
                            if key_obj:
                                self.key_controller.release(key_obj)
                            else:
                                # 处理控制字符
                                if key in self.CONTROL_CHAR_MAP:
                                    self.key_controller.release(key)
                                else:
                                    self.key_controller.release(key)

                            # 释放修饰键
                            for mod in modifiers:
                                if mod == 'ctrl':
                                    self.key_controller.release(keyboard.Key.ctrl)
                                elif mod == 'alt':
                                    self.key_controller.release(keyboard.Key.alt)
                                elif mod == 'shift':
                                    self.key_controller.release(keyboard.Key.shift)
                                elif mod == 'cmd':
                                    self.key_controller.release(keyboard.Key.cmd)

                            print(f"Key released: {key_display}")

                        except Exception as e:
                            print(f"无法释放按键 {key_display}: {e}")

            print(f"\n回放完成! 总事件数: {len(events)}")

        except Exception as e:
            print(f"回放过程中出错: {e}")
        finally:
            listener.stop()

def list_recordings():
    files = glob.glob("recording_*.json")
    if not files:
        print("没有找到任何录制文件")
        return None

    print("\n可用的录制文件:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")

    while True:
        try:
            choice = input("\n选择要回放的文件编号 (或按 q 返回): ")
            if choice.lower() == 'q':
                return None
            choice = int(choice) - 1
            if 0 <= choice < len(files):
                return files[choice]
            print("无效的选择，请重试")
        except ValueError:
            print("请输入有效的数字")

def main():
    recorder = InputRecorder()

    while True:
        print("\n=== 自动化操作工具 ===")
        print("1. 开始录制")
        print("2. 回放录制")
        print("3. 退出")

        choice = input("\n请选择操作 (1-3): ")

        if choice == '1':
            print("\n3秒后开始录制...")
            print("请切换到目标窗口")
            print("提示: 按 Ctrl+ESC 停止录制")
            time.sleep(3)
            recorder.start_recording()

        elif choice == '2':
            filename = list_recordings()
            if filename:
                try:
                    speed = float(input("\n输入回放速度 (1.0 = 正常速度, 2.0 = 2倍速, 0.5 = 半速): ") or "1.0")
                    speed = float(speed)
                    if speed <= 0:
                        print("速度必须大于0，使用默认速度1.0")
                        speed = 1.0
                except ValueError:
                    print("无效的速度，使用默认速度1.0")
                    speed = 1.0

                print(f"\n3秒后开始回放: {filename} (速度: {speed}x)")
                print("请切换到目标窗口")
                print("提示: 按 ESC 键可随时停止回放")
                time.sleep(3)
                events = recorder.load_recording(filename)
                recorder.play_events(events, speed)

        elif choice == '3':
            print("\n感谢使用，再见!")
            break

        else:
            print("无效的选择，请重试")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 确保所有监听器都已停止
        try:
            if 'recorder' in locals():
                recorder.stop_recording()
        except:
            pass
