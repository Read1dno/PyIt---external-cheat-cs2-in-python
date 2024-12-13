from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import QFileSystemWatcher, QCoreApplication, QObject, Signal, Slot
import multiprocessing
import threading
import requests
import pymem
import pymem.process
import win32api
import win32con
import win32gui
from pynput.mouse import Controller, Button
import json
import os
import sys
import time

# Константы
CONFIG_DIR = os.path.join(os.environ['LOCALAPPDATA'], 'temp', 'PyIt')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
DEFAULT_SETTINGS = {
    "esp_rendering": 1,
    "esp_mode": 1,
    "line_rendering": 1,
    "hp_bar_rendering": 1,
    "head_hitbox_rendering": 1,
    "bons": 1,
    "nickname": 1,
    "radius": 50,
    "keyboard": "C",
    "aim_active": 0,
    "aim_mode": 1,
    "aim_mode_distance": 1,
    "trigger_bot_active": 0,
    "keyboards": "X"
}

# Функции утилиты
def load_settings():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def get_offsets_and_client_dll():
    offsets = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json').json()
    client_dll = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json').json()
    return offsets, client_dll

def get_window_size(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        rect = win32gui.GetClientRect(hwnd)
        return rect[2], rect[3]
    return None, None

def w2s(mtx, posx, posy, posz, width, height):
    screenW = (mtx[12] * posx) + (mtx[13] * posy) + (mtx[14] * posz) + mtx[15]
    if screenW > 0.001:
        screenX = (mtx[0] * posx) + (mtx[1] * posy) + (mtx[2] * posz) + mtx[3]
        screenY = (mtx[4] * posx) + (mtx[5] * posy) + (mtx[6] * posz) + mtx[7]
        camX = width / 2
        camY = height / 2
        x = camX + (camX * screenX / screenW)
        y = camY - (camY * screenY / screenW)
        return [int(x), int(y)]
    return [-999, -999]


# Конфигуратор
class ConfigWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.initUI()
        self.is_dragging = False
        self.drag_start_position = None

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setFixedSize(850, 680)
        self.setStyleSheet("""
            QWidget { background-color: rgb(27, 27, 34); color: white; font-family: 'DejaVu Sans'; border-radius: 10px; }
            QLabel { font-size: 20px; }
            QPushButton { background-color: rgb(46, 43, 63); border: none; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: rgb(66, 63, 83); }
            QCheckBox { font-size: 18px; }
            QComboBox { background-color: rgb(27, 27, 34); border: 1px solid rgb(46, 43, 63); padding: 5px; border-radius: 5px; color: white; font-size: 18px; }
            QLineEdit { background-color: rgb(27, 27, 34); border: 1px solid rgb(46, 43, 63); padding: 5px; border-radius: 5px; color: white; font-size: 18px; }
            QSlider::groove:horizontal { border: 1px solid rgb(46, 43, 63); height: 35px; background: rgb(32, 34, 45); }
            QSlider::handle:horizontal { background: rgb(27, 27, 34); border: 1px solid rgb(46, 43, 63); width: 16px; height: 16px; border-radius: 8px; }
            QSlider::handle:horizontal:hover { background: rgb(66, 63, 83); }
            .container { background-color: rgb(32, 34, 45); border-radius: 5px; padding: 10px; }
        """)

        main_layout = QtWidgets.QHBoxLayout()

        left_container = self.create_left_container()
        right_container = self.create_right_container()

        main_layout.addWidget(left_container)
        main_layout.addWidget(right_container)

        self.setLayout(main_layout)

    def create_left_container(self):
        left_container = QtWidgets.QWidget()
        left_container.setStyleSheet("background-color: rgb(27, 27, 34); border-radius: 5px; padding: 10px;")
        left_layout = QtWidgets.QVBoxLayout()

        esp_container = self.create_esp_container()
        trigger_container = self.create_trigger_container()

        left_layout.addWidget(esp_container)
        left_layout.addItem(QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))
        left_layout.addWidget(trigger_container)

        left_container.setLayout(left_layout)
        return left_container

    def create_right_container(self):
        right_container = QtWidgets.QWidget()
        right_container.setStyleSheet("background-color: rgb(27, 27, 34); border-radius: 5px; padding: 10px;")
        right_layout = QtWidgets.QVBoxLayout()

        aim_container = self.create_aim_container()
        right_layout.addWidget(aim_container)

        right_container.setLayout(right_layout)
        return right_container

    def create_esp_container(self):
        esp_container = QtWidgets.QWidget()
        esp_container.setStyleSheet("background-color: rgb(32, 34, 45); border-radius: 5px; padding: 10px;")
        esp_layout = QtWidgets.QVBoxLayout()

        esp_label = QtWidgets.QLabel("ESP Settings")
        esp_label.setAlignment(QtCore.Qt.AlignCenter)
        esp_layout.addWidget(esp_label)

        self.esp_rendering_cb = QtWidgets.QCheckBox("Enable ESP")
        self.esp_rendering_cb.setChecked(self.settings["esp_rendering"] == 1)
        self.esp_rendering_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.esp_rendering_cb)

        self.esp_mode_cb = QtWidgets.QComboBox()
        self.esp_mode_cb.addItems(["Enemies Only", "All Players"])
        self.esp_mode_cb.setCurrentIndex(self.settings["esp_mode"])
        self.esp_mode_cb.currentIndexChanged.connect(self.save_settings)
        esp_layout.addWidget(self.esp_mode_cb)

        self.line_rendering_cb = QtWidgets.QCheckBox("Draw Lines")
        self.line_rendering_cb.setChecked(self.settings["line_rendering"] == 1)
        self.line_rendering_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.line_rendering_cb)

        self.hp_bar_rendering_cb = QtWidgets.QCheckBox("Draw HP Bars")
        self.hp_bar_rendering_cb.setChecked(self.settings["hp_bar_rendering"] == 1)
        self.hp_bar_rendering_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.hp_bar_rendering_cb)

        self.head_hitbox_rendering_cb = QtWidgets.QCheckBox("Draw Head Hitbox")
        self.head_hitbox_rendering_cb.setChecked(self.settings["head_hitbox_rendering"] == 1)
        self.head_hitbox_rendering_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.head_hitbox_rendering_cb)

        self.bons_cb = QtWidgets.QCheckBox("Draw Bones")
        self.bons_cb.setChecked(self.settings["bons"] == 1)
        self.bons_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.bons_cb)

        self.nickname_cb = QtWidgets.QCheckBox("Show Nickname")
        self.nickname_cb.setChecked(self.settings["nickname"] == 1)
        self.nickname_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.nickname_cb)

        esp_container.setLayout(esp_layout)
        return esp_container

    def create_trigger_container(self):
        trigger_container = QtWidgets.QWidget()
        trigger_container.setStyleSheet("background-color: rgb(32, 34, 45); border-radius: 5px; padding: 10px;")
        trigger_layout = QtWidgets.QVBoxLayout()

        trigger_label = QtWidgets.QLabel("Trigger Bot Settings")
        trigger_label.setAlignment(QtCore.Qt.AlignCenter)
        trigger_layout.addWidget(trigger_label)

        self.trigger_bot_active_cb = QtWidgets.QCheckBox("Enable Trigger Bot")
        self.trigger_bot_active_cb.setChecked(self.settings["trigger_bot_active"] == 1)
        self.trigger_bot_active_cb.stateChanged.connect(self.save_settings)
        trigger_layout.addWidget(self.trigger_bot_active_cb)

        self.trigger_key_input = QtWidgets.QLineEdit()
        self.trigger_key_input.setText(self.settings["keyboards"])
        self.trigger_key_input.textChanged.connect(self.save_settings)
        trigger_layout.addWidget(QtWidgets.QLabel("Trigger Key:"))
        trigger_layout.addWidget(self.trigger_key_input)

        trigger_container.setLayout(trigger_layout)
        return trigger_container

    def create_aim_container(self):
        aim_container = QtWidgets.QWidget()
        aim_container.setStyleSheet("background-color: rgb(32, 34, 45); border-radius: 5px; padding: 10px;")
        aim_layout = QtWidgets.QVBoxLayout()

        aim_label = QtWidgets.QLabel("Aim Settings")
        aim_label.setAlignment(QtCore.Qt.AlignCenter)
        aim_layout.addWidget(aim_label)

        self.aim_active_cb = QtWidgets.QCheckBox("Enable Aim")
        self.aim_active_cb.setChecked(self.settings["aim_active"] == 1)
        self.aim_active_cb.stateChanged.connect(self.save_settings)
        aim_layout.addWidget(self.aim_active_cb)

        self.radius_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.radius_slider.setMinimum(0)
        self.radius_slider.setMaximum(100)
        self.radius_slider.setValue(self.settings["radius"])
        self.radius_slider.valueChanged.connect(self.save_settings)
        aim_layout.addWidget(QtWidgets.QLabel("Aim Radius:"))
        aim_layout.addWidget(self.radius_slider)

        self.keyboard_input = QtWidgets.QLineEdit()
        self.keyboard_input.setText(self.settings["keyboard"])
        self.keyboard_input.textChanged.connect(self.save_settings)
        aim_layout.addWidget(QtWidgets.QLabel("Aim Key:"))
        aim_layout.addWidget(self.keyboard_input)

        self.aim_mode_cb = QtWidgets.QComboBox()
        self.aim_mode_cb.addItems(["Body", "Head"])
        self.aim_mode_cb.setCurrentIndex(self.settings["aim_mode"])
        self.aim_mode_cb.currentIndexChanged.connect(self.save_settings)
        aim_layout.addWidget(QtWidgets.QLabel("Aim Mode:"))
        aim_layout.addWidget(self.aim_mode_cb)

        self.aim_mode_distance_cb = QtWidgets.QComboBox()
        self.aim_mode_distance_cb.addItems(["Closest to Crosshair", "Closest in 3D"])
        self.aim_mode_distance_cb.setCurrentIndex(self.settings["aim_mode_distance"])
        self.aim_mode_distance_cb.currentIndexChanged.connect(self.save_settings)
        aim_layout.addWidget(QtWidgets.QLabel("Aim Distance Mode:"))
        aim_layout.addWidget(self.aim_mode_distance_cb)

        aim_container.setLayout(aim_layout)
        return aim_container

    def save_settings(self):
        self.settings["esp_rendering"] = 1 if self.esp_rendering_cb.isChecked() else 0
        self.settings["esp_mode"] = self.esp_mode_cb.currentIndex()
        self.settings["line_rendering"] = 1 if self.line_rendering_cb.isChecked() else 0
        self.settings["hp_bar_rendering"] = 1 if self.hp_bar_rendering_cb.isChecked() else 0
        self.settings["head_hitbox_rendering"] = 1 if self.head_hitbox_rendering_cb.isChecked() else 0
        self.settings["bons"] = 1 if self.bons_cb.isChecked() else 0
        self.settings["nickname"] = 1 if self.nickname_cb.isChecked() else 0
        self.settings["aim_active"] = 1 if self.aim_active_cb.isChecked() else 0
        self.settings["radius"] = self.radius_slider.value()
        self.settings["keyboard"] = self.keyboard_input.text()
        self.settings["aim_mode"] = self.aim_mode_cb.currentIndex()
        self.settings["aim_mode_distance"] = self.aim_mode_distance_cb.currentIndex()
        self.settings["trigger_bot_active"] = 1 if self.trigger_bot_active_cb.isChecked() else 0
        self.settings["keyboards"] = self.trigger_key_input.text()
        save_settings(self.settings)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.is_dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            self.move(self.pos() + delta)
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = False

def configurator():
    app = QtWidgets.QApplication(sys.argv)
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec())

# ESP
class ESPWindow(QtWidgets.QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle('ESP Overlay')
        self.window_width, self.window_height = get_window_size("Counter-Strike 2")
        if self.window_width is None or self.window_height is None:
            print("Ошибка: окно игры не найдено.")
            sys.exit(1)
        self.setGeometry(0, 0, self.window_width, self.window_height)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        hwnd = self.winId()
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
        self.file_watcher = QFileSystemWatcher([CONFIG_FILE])
        self.file_watcher.fileChanged.connect(self.reload_settings)
        self.offsets, self.client_dll = get_offsets_and_client_dll()
        self.pm = pymem.Pymem("cs2.exe")
        self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(0)
        self.last_time = time.time()
        self.frame_count = 0
        self.fps = 0

    def reload_settings(self):
        self.settings = load_settings()
        self.window_width, self.window_height = get_window_size("Counter-Strike 2")
        if self.window_width is None or self.window_height is None:
            print("Ошибка: окно игры не найдено.")
            sys.exit(1)
        self.setGeometry(0, 0, self.window_width, self.window_height)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            esp(painter, self.pm, self.client, self.offsets, self.client_dll, self.window_width, self.window_height, self.settings)
            current_time = time.time()
            self.frame_count += 1
            if current_time - self.last_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_time = current_time
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
            font = QtGui.QFont('DejaVu Sans', 12, QtGui.QFont.Bold)
            painter.setFont(font)
            painter.drawText(10, 20, f"PyIt | FPS: {self.fps}")
        except Exception as e:
            print(f"Painter Error: {e}")
            QtWidgets.QApplication.quit()

def esp(painter, pm, client, offsets, client_dll, window_width, window_height, settings):
    if settings['esp_rendering'] == 0:
        return
    dwEntityList = offsets['client.dll']['dwEntityList']
    dwLocalPlayerPawn = offsets['client.dll']['dwLocalPlayerPawn']
    dwViewMatrix = offsets['client.dll']['dwViewMatrix']
    m_iTeamNum = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum']
    m_lifeState = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']
    m_pGameSceneNode = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode']
    m_modelState = client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState']
    m_hPlayerPawn = client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn']
    m_iHealth = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iHealth']
    m_iszPlayerName = client_dll['client.dll']['classes']['CBasePlayerController']['fields']['m_iszPlayerName']
    view_matrix = [pm.read_float(client + dwViewMatrix + i * 4) for i in range(16)]
    local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
    try:
        local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
    except:
        return
    no_center_x = window_width / 2
    no_center_y = window_height * 0.75
    for i in range(64):
        entity = pm.read_longlong(client + dwEntityList)
        if not entity:
            continue
        list_entry = pm.read_longlong(entity + ((8 * (i & 0x7FFF) >> 9) + 16))
        if not list_entry:
            continue
        entity_controller = pm.read_longlong(list_entry + (120) * (i & 0x1FF))
        if not entity_controller:
            continue
        entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)
        if not entity_controller_pawn:
            continue
        list_entry = pm.read_longlong(entity + (0x8 * ((entity_controller_pawn & 0x7FFF) >> 9) + 16))
        if not list_entry:
            continue
        entity_pawn_addr = pm.read_longlong(list_entry + (120) * (entity_controller_pawn & 0x1FF))
        if not entity_pawn_addr or entity_pawn_addr == local_player_pawn_addr:
            continue
        entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)
        if entity_team == local_player_team and settings['esp_mode'] == 0:
            continue
        entity_hp = pm.read_int(entity_pawn_addr + m_iHealth)
        if entity_hp <= 0:
            continue
        color = QtGui.QColor(0, 255, 0) if entity_team == local_player_team else QtGui.QColor(255, 0, 0)
        game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
        bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)
        try:
            headX = pm.read_float(bone_matrix + 6 * 0x20)
            headY = pm.read_float(bone_matrix + 6 * 0x20 + 0x4)
            headZ = pm.read_float(bone_matrix + 6 * 0x20 + 0x8) + 8
            head_pos = w2s(view_matrix, headX, headY, headZ, window_width, window_height)
            if settings['line_rendering'] == 1:
                legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                leg_pos = w2s(view_matrix, headX, headY, legZ, window_width, window_height)
                bottom_left_x = head_pos[0] - (head_pos[0] - leg_pos[0]) // 2
                bottom_y = leg_pos[1]
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setPen(QtGui.QPen(color, 1))
                painter.drawLine(bottom_left_x, bottom_y, no_center_x, no_center_y)
            legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
            leg_pos = w2s(view_matrix, headX, headY, legZ, window_width, window_height)
            deltaZ = abs(head_pos[1] - leg_pos[1])
            leftX = head_pos[0] - deltaZ // 3
            rightX = head_pos[0] + deltaZ // 3
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtGui.QPen(color, 1))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(QtCore.QRectF(leftX, head_pos[1], rightX - leftX, leg_pos[1] - head_pos[1]))
            if settings['hp_bar_rendering'] == 1:
                max_hp = 100
                hp_percentage = min(1.0, max(0.0, entity_hp / max_hp))
                hp_bar_width = 2
                hp_bar_height = deltaZ
                hp_bar_x_left = leftX - hp_bar_width - 2
                hp_bar_y_top = head_pos[1]
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                painter.setBrush(QtGui.QColor(0, 0, 0))
                painter.drawRect(QtCore.QRectF(hp_bar_x_left, hp_bar_y_top, hp_bar_width, hp_bar_height))
                painter.setBrush(QtGui.QColor(255, 0, 0))
                current_hp_height = hp_bar_height * hp_percentage
                hp_bar_y_bottom = hp_bar_y_top + hp_bar_height - current_hp_height
                painter.drawRect(QtCore.QRectF(hp_bar_x_left, hp_bar_y_bottom, hp_bar_width, current_hp_height))
            if settings['head_hitbox_rendering'] == 1:
                head_hitbox_size = (rightX - leftX) / 5
                head_hitbox_radius = head_hitbox_size * 2 ** 0.5 / 2
                head_hitbox_x = leftX + 2.5 * head_hitbox_size
                head_hitbox_y = head_pos[1] + deltaZ / 9
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setBrush(QtGui.QColor(255, 0, 0, 128))
                painter.drawEllipse(QtCore.QPointF(head_hitbox_x, head_hitbox_y), head_hitbox_radius, head_hitbox_radius)
            if settings.get('bons', 0) == 1:
                draw_bones(painter, pm, bone_matrix, view_matrix, window_width, window_height)
            if settings.get('nickname', 0) == 1:
                player_name = pm.read_string(entity_controller + m_iszPlayerName, 32)
                font_size = max(6, min(18, deltaZ / 25))
                font = QtGui.QFont('DejaVu Sans', font_size, QtGui.QFont.Bold)
                path = QtGui.QPainterPath()
                path.addText(0, 0, font, player_name)
                text_rect = path.boundingRect()
                name_x = head_pos[0] - text_rect.width() / 2
                name_y = head_pos[1] - deltaZ / 8
                painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
                painter.setFont(font)
                painter.drawText(name_x, name_y, player_name)
            if 'radius' in settings:
                if settings['radius'] != 0:
                    center_x = window_width / 2
                    center_y = window_height / 2
                    screen_radius = settings['radius'] / 100.0 * min(center_x, center_y)
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 16), 0.5))
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.drawEllipse(QtCore.QPointF(center_x, center_y), screen_radius, screen_radius)
        except:
            return

def draw_bones(painter, pm, bone_matrix, view_matrix, width, height):
    bone_ids = {
        "head": 6,
        "neck": 5,
        "spine": 4,
        "pelvis": 0,
        "left_shoulder": 13,
        "left_elbow": 14,
        "left_wrist": 15,
        "right_shoulder": 9,
        "right_elbow": 10,
        "right_wrist": 11,
        "left_hip": 25,
        "left_knee": 26,
        "left_ankle": 27,
        "right_hip": 22,
        "right_knee": 23,
        "right_ankle": 24,
    }
    bone_connections = [
        ("head", "neck"),
        ("neck", "spine"),
        ("spine", "pelvis"),
        ("pelvis", "left_hip"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("pelvis", "right_hip"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
        ("neck", "left_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("neck", "right_shoulder"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
    ]
    bone_positions = {}
    try:
        for bone_name, bone_id in bone_ids.items():
            boneX = pm.read_float(bone_matrix + bone_id * 0x20)
            boneY = pm.read_float(bone_matrix + bone_id * 0x20 + 0x4)
            boneZ = pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
            bone_pos = w2s(view_matrix, boneX, boneY, boneZ, width, height)
            if bone_pos[0] != -999 and bone_pos[1] != -999:
                bone_positions[bone_name] = bone_pos
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 128), 1))
        for connection in bone_connections:
            if connection[0] in bone_positions and connection[1] in bone_positions:
                painter.drawLine(
                    bone_positions[connection[0]][0], bone_positions[connection[0]][1],
                    bone_positions[connection[1]][0], bone_positions[connection[1]][1]
                )
    except Exception as e:
        print(f"Error drawing bones: {e}")

def esp_main():
    settings = load_settings()
    app = QtWidgets.QApplication(sys.argv)
    window = ESPWindow(settings)
    window.show()
    sys.exit(app.exec())

# Trigger Bot
def triggerbot():
    offsets = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json').json()
    client_dll = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json').json()
    dwEntityList = offsets['client.dll']['dwEntityList']
    dwLocalPlayerPawn = offsets['client.dll']['dwLocalPlayerPawn']
    m_iTeamNum = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum']
    m_iIDEntIndex = client_dll['client.dll']['classes']['C_CSPlayerPawnBase']['fields']['m_iIDEntIndex']
    m_iHealth = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iHealth']
    mouse = Controller()
    default_settings = {
        "keyboards": "X",
        "trigger_bot_active": 1,
        "esp_mode": 1
    }

    def load_settings():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default_settings

    def main(settings):
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        while True:
            try:
                trigger_bot_active = settings["trigger_bot_active"]
                attack_all = settings["esp_mode"]
                keyboards = settings["keyboards"]
                if win32api.GetAsyncKeyState(ord(keyboards)):
                    if trigger_bot_active == 1:
                        try:
                            player = pm.read_longlong(client + dwLocalPlayerPawn)
                            entityId = pm.read_int(player + m_iIDEntIndex)
                            if entityId > 0:
                                entList = pm.read_longlong(client + dwEntityList)
                                entEntry = pm.read_longlong(entList + 0x8 * (entityId >> 9) + 0x10)
                                entity = pm.read_longlong(entEntry + 120 * (entityId & 0x1FF))
                                entityTeam = pm.read_int(entity + m_iTeamNum)
                                playerTeam = pm.read_int(player + m_iTeamNum)
                                if (attack_all == 1) or (entityTeam != playerTeam and attack_all == 0):
                                    entityHp = pm.read_int(entity + m_iHealth)
                                    if entityHp > 0:
                                        time.sleep(0.03)
                                        mouse.press(Button.left)
                                        time.sleep(0.03)
                                        mouse.release(Button.left)
                        except Exception:
                            pass
                    time.sleep(0.03)
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(1)

    def start_main_thread(settings):
        while True:
            main(settings)

    def setup_watcher(app, settings):
        watcher = QFileSystemWatcher()
        watcher.addPath(CONFIG_FILE)
        def reload_settings():
            new_settings = load_settings()
            settings.update(new_settings)
        watcher.fileChanged.connect(reload_settings)
        app.exec()

    def main_program():
        app = QCoreApplication(sys.argv)
        settings = load_settings()
        threading.Thread(target=start_main_thread, args=(settings,), daemon=True).start()
        setup_watcher(app, settings)

    main_program()

# Aim Bot
def aim():
    default_settings = {
        'esp_rendering': 1,
        'esp_mode': 1,
        'keyboard': "C",
        'aim_active': 1,
        'aim_mode': 1,
        'radius': 20,
        'aim_mode_distance': 1
    }

    def get_window_size(window_name="Counter-Strike 2"):
        hwnd = win32gui.FindWindow(None, window_name)
        if hwnd:
            rect = win32gui.GetClientRect(hwnd)
            return rect[2] - rect[0], rect[3] - rect[1]
        return 1920, 1080

    def load_settings():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default_settings

    def get_offsets_and_client_dll():
        offsets = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json').json()
        client_dll = requests.get('https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json').json()
        return offsets, client_dll

    def esp(pm, client, offsets, client_dll, settings, target_list, window_size):
        width, height = window_size
        if settings['aim_active'] == 0:
            return
        dwEntityList = offsets['client.dll']['dwEntityList']
        dwLocalPlayerPawn = offsets['client.dll']['dwLocalPlayerPawn']
        dwViewMatrix = offsets['client.dll']['dwViewMatrix']
        m_iTeamNum = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum']
        m_lifeState = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']
        m_pGameSceneNode = client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode']
        m_modelState = client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState']
        m_hPlayerPawn = client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn']
        view_matrix = [pm.read_float(client + dwViewMatrix + i * 4) for i in range(16)]
        local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
        try:
            local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
        except:
            return
        for i in range(64):
            entity = pm.read_longlong(client + dwEntityList)
            if not entity:
                continue
            list_entry = pm.read_longlong(entity + ((8 * (i & 0x7FFF) >> 9) + 16))
            if not list_entry:
                continue
            entity_controller = pm.read_longlong(list_entry + (120) * (i & 0x1FF))
            if not entity_controller:
                continue
            entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)
            if not entity_controller_pawn:
                continue
            list_entry = pm.read_longlong(entity + (0x8 * ((entity_controller_pawn & 0x7FFF) >> 9) + 16))
            if not list_entry:
                continue
            entity_pawn_addr = pm.read_longlong(list_entry + (120) * (entity_controller_pawn & 0x1FF))
            if not entity_pawn_addr or entity_pawn_addr == local_player_pawn_addr:
                continue
            entity_alive = pm.read_int(entity_pawn_addr + m_lifeState)
            if entity_alive != 256:
                continue
            entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)
            if entity_team == local_player_team and settings['esp_mode'] == 0:
                continue
            game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
            bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)
            try:
                bone_id = 6 if settings['aim_mode'] == 1 else 4
                headX = pm.read_float(bone_matrix + bone_id * 0x20)
                headY = pm.read_float(bone_matrix + bone_id * 0x20 + 0x4)
                headZ = pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
                head_pos = w2s(view_matrix, headX, headY, headZ, width, height)
                legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                leg_pos = w2s(view_matrix, headX, headY, legZ, width, height)
                deltaZ = abs(head_pos[1] - leg_pos[1])
                if head_pos[0] != -999 and head_pos[1] != -999:
                    if settings['aim_mode_distance'] == 1:
                        target_list.append({
                            'pos': head_pos,
                            'deltaZ': deltaZ
                        })
                    else:
                        target_list.append({
                            'pos': head_pos,
                            'deltaZ': None
                        })
            except Exception as e:
                pass
        return target_list

    def aimbot(target_list, radius, aim_mode_distance):
        if not target_list:
            return
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2
        if radius == 0:
            closest_target = None
            closest_dist = float('inf')
            for target in target_list:
                dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                if dist < closest_dist:
                    closest_target = target['pos']
                    closest_dist = dist
        else:
            screen_radius = radius / 100.0 * min(center_x, center_y)
            closest_target = None
            closest_dist = float('inf')
            if aim_mode_distance == 1:
                target_with_max_deltaZ = None
                max_deltaZ = -float('inf')
                for target in target_list:
                    dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                    if dist < screen_radius and target['deltaZ'] > max_deltaZ:
                        max_deltaZ = target['deltaZ']
                        target_with_max_deltaZ = target
                closest_target = target_with_max_deltaZ['pos'] if target_with_max_deltaZ else None
            else:
                for target in target_list:
                    dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                    if dist < screen_radius and dist < closest_dist:
                        closest_target = target['pos']
                        closest_dist = dist
        if closest_target:
            target_x, target_y = closest_target
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(target_x - center_x), int(target_y - center_y), 0, 0)

    def main(settings):
        offsets, client_dll = get_offsets_and_client_dll()
        window_size = get_window_size()
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        while True:
            target_list = []
            target_list = esp(pm, client, offsets, client_dll, settings, target_list, window_size)
            if win32api.GetAsyncKeyState(ord(settings['keyboard'])):
                aimbot(target_list, settings['radius'], settings['aim_mode_distance'])
            time.sleep(0.01)

    def start_main_thread(settings):
        while True:
            main(settings)

    def setup_watcher(app, settings):
        watcher = QFileSystemWatcher()
        watcher.addPath(CONFIG_FILE)
        def reload_settings():
            new_settings = load_settings()
            settings.update(new_settings)
        watcher.fileChanged.connect(reload_settings)
        app.exec()

    def main_program():
        app = QCoreApplication(sys.argv)
        settings = load_settings()
        threading.Thread(target=start_main_thread, args=(settings,), daemon=True).start()
        setup_watcher(app, settings)

    main_program()

if __name__ == "__main__":
    print("Waiting cs2.exe")
    while True:
        time.sleep(1)
        try:
            pm = pymem.Pymem("cs2.exe")
            client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
            break
        except Exception as e:
            pass
    print("Starting PyIt cheat!")
    time.sleep(2)

    process1 = multiprocessing.Process(target=configurator)
    process2 = multiprocessing.Process(target=esp_main)
    process3 = multiprocessing.Process(target=triggerbot)
    process4 = multiprocessing.Process(target=aim)

    process1.start()
    process2.start()
    process3.start()
    process4.start()

    process1.join()
    process2.join()
    process3.join()
    process4.join()
