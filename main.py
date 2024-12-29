# main

import mido
from mido import Message
import customtkinter as ctk
from threading import Thread
import json
import os

class MidiMapping:
    def __init__(self):
        self.mappings = {
            'faders': {'start': 1, 'end': 8, 'offset': 80},
            'buttons': {'start': 33, 'end': 40, 'offset': 7}
        }
        self.load_mappings()

    def save_mappings(self):
        with open('mappings.json', 'w') as f:
            json.dump(self.mappings, f)

    def load_mappings(self):
        try:
            with open('mappings.json', 'r') as f:
                self.mappings = json.load(f)
        except FileNotFoundError:
            pass

class MidiBridgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ウィンドウ設定
        self.title("MIDI Signal Bridge")
        self.geometry("800x600")
        
        # 変数初期化
        self.input_port = None
        self.output_port = None
        self.bridge_running = False
        self.bridge_thread = None
        self.midi_mapping = MidiMapping()

        # UIセットアップ
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        # メインフレームを2列に分割
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 左パネル - 接続コントロール
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # リフレッシュボタン
        refresh_btn = ctk.CTkButton(left_frame, text="Refresh Ports", command=self.refresh_ports)
        refresh_btn.pack(pady=5, padx=10, fill="x")

        # 入力ポート選択
        ctk.CTkLabel(left_frame, text="Input Port:").pack(pady=5)
        self.input_dropdown = ctk.CTkOptionMenu(left_frame, values=[])
        self.input_dropdown.pack(pady=5, padx=10, fill="x")

        # 出力ポート選択
        ctk.CTkLabel(left_frame, text="Output Port:").pack(pady=5)
        self.output_dropdown = ctk.CTkOptionMenu(left_frame, values=[])
        self.output_dropdown.pack(pady=5, padx=10, fill="x")

        # 接続ボタン
        self.connect_button = ctk.CTkButton(left_frame, text="Connect", command=self.connect_ports)
        self.connect_button.pack(pady=5, padx=10, fill="x")

        # ブリッジ開始ボタン
        self.start_button = ctk.CTkButton(left_frame, text="Start Bridge", command=self.start_bridge)
        self.start_button.pack(pady=5, padx=10, fill="x")

        # ステータスラベル
        self.status_label = ctk.CTkLabel(left_frame, text="No MIDI devices connected.")
        self.status_label.pack(pady=5)

        # マッピング設定テーブル
        mapping_frame = ctk.CTkFrame(left_frame)
        mapping_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(mapping_frame, text="MIDI Mapping Configuration").pack()
        
        # フェーダーマッピング
        fader_frame = ctk.CTkFrame(mapping_frame)
        fader_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(fader_frame, text="Faders:").pack(side="left")
        self.fader_range = ctk.CTkEntry(fader_frame)
        self.fader_range.pack(side="left", padx=5)
        self.fader_offset = ctk.CTkEntry(fader_frame)
        self.fader_offset.pack(side="left", padx=5)

        # ボタンマッピング
        button_frame = ctk.CTkFrame(mapping_frame)
        button_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(button_frame, text="Buttons:").pack(side="left")
        self.button_range = ctk.CTkEntry(button_frame)
        self.button_range.pack(side="left", padx=5)
        self.button_offset = ctk.CTkEntry(button_frame)
        self.button_offset.pack(side="left", padx=5)

        # 右パネル - メッセージログ
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(right_frame, text="MIDI Message Log").pack(pady=5)
        
        self.log_text = ctk.CTkTextbox(right_frame, wrap="word")
        self.log_text.pack(pady=5, padx=10, fill="both", expand=True)

        # ログクリアボタン
        clear_log_btn = ctk.CTkButton(right_frame, text="Clear Log", command=self.clear_log)
        clear_log_btn.pack(pady=5, padx=10)

    def refresh_ports(self):
        """利用可能なMIDIポートを更新"""
        input_ports = mido.get_input_names()
        output_ports = mido.get_output_names()
        
        self.input_dropdown.configure(values=input_ports)
        self.output_dropdown.configure(values=output_ports)

    def load_settings(self):
        """Load application settings"""
        settings_file = 'settings.json'
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                input_port = settings.get('input_port')
                output_port = settings.get('output_port')
        except FileNotFoundError:
            pass

        if input_port:
            self.input_dropdown.set(input_port)

        if output_port:
            self.output_dropdown.set(output_port)

    def save_settings(self):
        """Save application settings"""
        settings = {
            'input_port': self.input_dropdown.get(),
            'output_port': self.output_dropdown.get()
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

    def add_to_log(self, message):
        """ログにメッセージを追加"""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def clear_log(self):
        """ログをクリア"""
        self.log_text.delete("1.0", "end")

    def transform_message(self, msg):
        """Transform the MIDI message according to the mapping rules."""
        try:
            if msg.type == 'control_change':
                mappings = self.midi_mapping.mappings
                
                # External Controller -> Host Application
                if msg.control in range(mappings['faders']['start'], mappings['faders']['end'] + 1):
                    msg.control += mappings['faders']['offset']
                elif msg.control in range(mappings['buttons']['start'], mappings['buttons']['end'] + 1):
                    msg.control += mappings['buttons']['offset']

                # Host Application -> External Controller
                elif msg.control in range(mappings['faders']['start'] + mappings['faders']['offset'],
                                       mappings['faders']['end'] + mappings['faders']['offset'] + 1):
                    msg.control -= mappings['faders']['offset']
                elif msg.control in range(mappings['buttons']['start'] + mappings['buttons']['offset'],
                                       mappings['buttons']['end'] + mappings['buttons']['offset'] + 1):
                    msg.control -= mappings['buttons']['offset']
            return msg
        except Exception as e:
            self.add_to_log(f"Error transforming message: {e}")
            return None

    def bridge_loop(self):
        """MIDI bridging loop running in separate thread."""
        try:
            while self.bridge_running:
                msg = self.input_port.receive()
                if msg:
                    self.add_to_log(f"Received: {msg}")
                    transformed_msg = self.transform_message(msg)
                    if transformed_msg:
                        self.add_to_log(f"Transformed: {transformed_msg}")
                        self.output_port.send(transformed_msg)
        except Exception as e:
            self.status_label.setText(f"Error during MIDI bridging: {e}")

    def closeEvent(self, event):
        """Handle application closure."""
        if self.bridge_running:
            self.bridge_running = False
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  # ダークモード
    ctk.set_default_color_theme("blue")  # カラーテーマ
    app = MidiBridgeApp()
    app.mainloop()
    