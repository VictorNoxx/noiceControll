import sys
import os
import winreg
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSystemTrayIcon, QMenu, QDialog, QLineEdit, QFormLayout, QSpinBox,
    QComboBox, QCheckBox, QMessageBox, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, QSettings, QSize, QPropertyAnimation
from PySide6.QtGui import QIcon, QAction, QFont, QPalette, QColor
import sounddevice as sd
import numpy as np
import soundfile as sf
import requests
import datetime
import time
import threading
import qtawesome as qta
import logging

# Constants
APP_NAME = "NoiseMonitor"
SETTINGS_ORG = "NoiseControl"
DEFAULT_THRESHOLD = 30
DEFAULT_SPIKE_DURATION = 500
SAMPLE_RATE = 44100
CHUNK_DURATION = 0.1  # 100ms chunks
ALERT_COOLDOWN = 600  # 10 minutes in seconds
ICON_SIZE = QSize(12, 12)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(APP_NAME)

class ThemeManager:
    """Manages application themes and styles."""
    
    @staticmethod
    def is_system_dark_theme() -> bool:
        """Check if Windows is using dark theme."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except Exception as e:
            logger.error(f"Error checking system theme: {e}")
            return False

    @staticmethod
    def get_stylesheet(theme: str) -> str:
        """Return stylesheet based on theme with adjusted input sizes."""
        if theme == "Dark" or (theme == "System" and ThemeManager.is_system_dark_theme()):
            return """
                QMainWindow, QDialog {
                    background-color: #1A1A1A;
                    color: #E0E0E0;
                }
                QLabel {
                    color: #E0E0E0;
                    font-family: 'Segoe UI', Arial;
                    padding: 2px 4px;
                }
                QLabel#title {
                    font-size: 14px;
                    font-weight: bold;
                    color: #4CAF50;
                    padding: 2px 4px;
                }
                QLabel#form-label {
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-family: 'Segoe UI', Arial;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45A049;
                }
                QPushButton:pressed {
                    background-color: #3D8B40;
                }
                QFrame {
                    background-color: #252525;
                    border: 1px solid #333333;
                    border-radius: 6px;
                }
                QLineEdit, QSpinBox, QComboBox {
                    background-color: #333333;
                    color: #E0E0E0;
                    border: 1px solid #444444;
                    border-radius: 4px;
                    padding: 2px 4px;
                    font-family: 'Segoe UI', Arial;
                    font-size: 12px;
                }
                QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                    border: 1px solid #4CAF50;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    background-color: #444444;
                    border: none;
                    width: 14px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 18px;
                }
                QCheckBox {
                    color: #E0E0E0;
                    font-family: 'Segoe UI', Arial;
                    font-size: 12px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #444444;
                    border-radius: 3px;
                    background-color: #333333;
                }
                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border-color: #4CAF50;
                }
            """
        return """
            QMainWindow, QDialog {
                background-color: #F5F5F5;
                color: #333333;
            }
            QLabel {
                color: #333333;
                font-family: 'Segoe UI', Arial;
                padding: 2px 4px;
            }
            QLabel#title {
                font-size: 14px;
                font-weight: bold;
                color: #4CAF50;
                padding: 2px 4px;
            }
            QLabel#form-label {
                font-size: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-family: 'Segoe UI', Arial;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:pressed {
                background-color: #3D8B40;
            }
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 2px 4px;
                font-family: 'Segoe UI', Arial;
                font-size: 12px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #4CAF50;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #E0E0E0;
                border: none;
                width: 14px;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QCheckBox {
                color: #333333;
                font-family: 'Segoe UI', Arial;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
        """

class SettingsManager:
    """Manages application settings and autostart configuration."""
    
    def __init__(self):
        self.settings = QSettings(SETTINGS_ORG, APP_NAME)

    def get(self, key: str, default: any, type: type = str) -> any:
        """Retrieve a setting with type conversion."""
        return self.settings.value(key, default, type=type)

    def set(self, key: str, value: any) -> None:
        """Set a setting."""
        self.settings.setValue(key, value)

    def set_autostart(self, enabled: bool, app_path: str) -> None:
        """Set or remove autostart registry entry."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                if enabled:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{app_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            logger.error(f"Error setting autostart: {e}")

class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""
    
    def __init__(self, parent: Optional[QMainWindow] = None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(200)
        animation.setStartValue(0.9)
        animation.setEndValue(1.0)
        animation.start()

        self.setWindowTitle("Settings")
        self.setFixedSize(440, 650)
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self) -> None:
        """Setup the settings dialog UI with improved spacing and smaller inputs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Device Selection
        device_frame = QFrame()
        device_layout = QVBoxLayout(device_frame)
        device_layout.setContentsMargins(8, 8, 8, 8)
        device_layout.setSpacing(8)
        
        device_title = QLabel("🎤 Audio Device")
        device_title.setObjectName("title")
        device_layout.addWidget(device_title)
        
        self.device_combo = QComboBox()
        self.refresh_devices()
        device_layout.addWidget(self.device_combo)
        layout.addWidget(device_frame)

        # Telegram Settings
        telegram_frame = QFrame()
        telegram_layout = QFormLayout(telegram_frame)
        telegram_layout.setContentsMargins(12, 12, 12, 12)
        telegram_layout.setSpacing(8)
        telegram_layout.setLabelAlignment(Qt.AlignLeft)
        
        telegram_title = QLabel("📱 Telegram")
        telegram_title.setObjectName("title")
        telegram_layout.addRow(telegram_title)
        
        token_label = QLabel("Token:")
        token_label.setObjectName("form-label")
        self.token_edit = QLineEdit(self.settings_manager.get("telegram_token", ""))
        self.token_edit.setPlaceholderText("Bot Token")
        telegram_layout.addRow(token_label, self.token_edit)
        
        chat_id_label = QLabel("Chat ID:")
        chat_id_label.setObjectName("form-label")
        self.chat_id_edit = QLineEdit(self.settings_manager.get("telegram_chat_id", ""))
        self.chat_id_edit.setPlaceholderText("Chat ID")
        telegram_layout.addRow(chat_id_label, self.chat_id_edit)
        layout.addWidget(telegram_frame)

        # Threshold Settings
        threshold_frame = QFrame()
        threshold_layout = QFormLayout(threshold_frame)
        threshold_layout.setContentsMargins(12, 12, 12, 12)
        threshold_layout.setSpacing(8)
        threshold_layout.setLabelAlignment(Qt.AlignLeft)
        
        threshold_title = QLabel("🔊 Threshold")
        threshold_title.setObjectName("title")
        threshold_layout.addRow(threshold_title)
        
        level_label = QLabel("Level:")
        level_label.setObjectName("form-label")
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 120)
        self.threshold_spin.setValue(self.settings_manager.get("threshold", DEFAULT_THRESHOLD, type=int))
        self.threshold_spin.setSuffix(" dB")
        threshold_layout.addRow(level_label, self.threshold_spin)
        layout.addWidget(threshold_frame)

        # Theme Settings
        theme_frame = QFrame()
        theme_layout = QFormLayout(theme_frame)
        theme_layout.setContentsMargins(12, 12, 12, 12)
        theme_layout.setSpacing(8)
        theme_layout.setLabelAlignment(Qt.AlignLeft)
        
        theme_title = QLabel("🎨 Theme")
        theme_title.setObjectName("title")
        theme_layout.addRow(theme_title)
        
        theme_label = QLabel("Theme:")
        theme_label.setObjectName("form-label")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings_manager.get("theme", "System"))
        theme_layout.addRow(theme_label, self.theme_combo)
        layout.addWidget(theme_frame)

        # Spike Filter Settings
        filter_frame = QFrame()
        filter_layout = QFormLayout(filter_frame)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(8)
        filter_layout.setLabelAlignment(Qt.AlignLeft)
        
        filter_title = QLabel("⚡ Spike Filter")
        filter_title.setObjectName("title")
        filter_layout.addRow(filter_title)
        
        self.filter_check = QCheckBox("Enable Spike Filter")
        self.filter_check.setChecked(self.settings_manager.get("filter_micro_lags", True, type=bool))
        filter_layout.addRow(self.filter_check)
        
        duration_label = QLabel("Duration:")
        duration_label.setObjectName("form-label")
        self.spike_duration_spin = QSpinBox()
        self.spike_duration_spin.setRange(100, 2000)
        self.spike_duration_spin.setSingleStep(100)
        self.spike_duration_spin.setValue(self.settings_manager.get("spike_duration_ms", DEFAULT_SPIKE_DURATION, type=int))
        self.spike_duration_spin.setSuffix(" ms")
        filter_layout.addRow(duration_label, self.spike_duration_spin)
        layout.addWidget(filter_frame)

        # Startup Settings
        startup_frame = QFrame()
        startup_layout = QFormLayout(startup_frame)
        startup_layout.setContentsMargins(12, 12, 12, 12)
        startup_layout.setSpacing(8)
        startup_layout.setLabelAlignment(Qt.AlignLeft)
        
        startup_title = QLabel("⚙️ Startup")
        startup_title.setObjectName("title")
        startup_layout.addRow(startup_title)
        
        self.autostart_check = QCheckBox("Start with Windows")
        self.autostart_check.setChecked(self.settings_manager.get("autostart", False, type=bool))
        startup_layout.addRow(self.autostart_check)
        
        self.minimized_check = QCheckBox("Start Minimized")
        self.minimized_check.setChecked(self.settings_manager.get("start_minimized", False, type=bool))
        startup_layout.addRow(self.minimized_check)
        layout.addWidget(startup_frame)

        # Save Button
        save_button = QPushButton(qta.icon('fa5s.save'), "Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button, alignment=Qt.AlignRight)

    def refresh_devices(self) -> None:
        """Refresh the list of audio devices."""
        self.device_combo.clear()
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                self.device_combo.addItem(device['name'], i)
        current_device = self.settings_manager.get("audio_device", "")
        index = self.device_combo.findText(current_device)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)

    def save_settings(self) -> None:
        """Save settings and update autostart."""
        self.settings_manager.set("audio_device", self.device_combo.currentText())
        self.settings_manager.set("telegram_token", self.token_edit.text())
        self.settings_manager.set("telegram_chat_id", self.chat_id_edit.text())
        self.settings_manager.set("threshold", self.threshold_spin.value())
        self.settings_manager.set("filter_micro_lags", self.filter_check.isChecked())
        self.settings_manager.set("spike_duration_ms", self.spike_duration_spin.value())
        self.settings_manager.set("autostart", self.autostart_check.isChecked())
        self.settings_manager.set("start_minimized", self.minimized_check.isChecked())
        self.settings_manager.set("theme", self.theme_combo.currentText())

        app_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        self.settings_manager.set_autostart(self.autostart_check.isChecked(), app_path)

        if isinstance(self.parent(), QMainWindow):
            self.parent().apply_theme()
        self.accept()

    def apply_theme(self) -> None:
        """Apply the selected theme."""
        self.setStyleSheet(ThemeManager.get_stylesheet(self.settings_manager.get("theme", "System")))

class NoiseMonitorWindow(QMainWindow):
    """Main window for the Noise Monitor application."""
    
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.is_monitoring = True
        self.last_alert_time = 0
        self.recording_thread: Optional[threading.Thread] = None
        self.noise_levels = []
        self.max_level = 0
        self.min_level = 120
        self.current_db = 0
        self.max_level_time: Optional[datetime.datetime] = None
        self.min_level_time: Optional[datetime.datetime] = None
        self.setup_ui()
        self.setup_tray()
        self.setup_audio()
        self.apply_theme()
        self.start_monitoring()

        if self.settings_manager.get("start_minimized", False, type=bool):
            self.hide()

    def setup_ui(self) -> None:
        """Setup the main window UI."""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(320, 240)
        self.setWindowIcon(qta.icon('fa5s.volume-up'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Status Frame
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(6)

        # Noise Level Display
        level_layout = QHBoxLayout()
        self.noise_label = QLabel("0.0")
        self.noise_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.noise_label.setAlignment(Qt.AlignCenter)
        level_layout.addWidget(self.noise_label)

        self.unit_label = QLabel("dB SPL")
        self.unit_label.setFont(QFont("Segoe UI", 12))
        level_layout.addWidget(self.unit_label)
        status_layout.addLayout(level_layout)

        # Min/Max Levels
        stats_grid = QGridLayout()
        stats_grid.setSpacing(4)

        self.min_icon = QLabel()
        self.min_icon.setPixmap(qta.icon('fa5s.arrow-down', color='#4CAF50').pixmap(ICON_SIZE))
        stats_grid.addWidget(self.min_icon, 0, 0, Qt.AlignCenter)

        self.min_label = QLabel("Min: -- dB")
        self.min_label.setFont(QFont("Segoe UI", 10))
        stats_grid.addWidget(self.min_label, 0, 1)

        self.min_time_label = QLabel("")
        self.min_time_label.setFont(QFont("Segoe UI", 8))
        self.min_time_label.setStyleSheet("color: #888888;")
        stats_grid.addWidget(self.min_time_label, 0, 2)

        self.max_icon = QLabel()
        self.max_icon.setPixmap(qta.icon('fa5s.arrow-up', color='#F44336').pixmap(ICON_SIZE))
        stats_grid.addWidget(self.max_icon, 1, 0, Qt.AlignCenter)

        self.max_label = QLabel("Max: -- dB")
        self.max_label.setFont(QFont("Segoe UI", 10))
        stats_grid.addWidget(self.max_label, 1, 1)

        self.max_time_label = QLabel("")
        self.max_time_label.setFont(QFont("Segoe UI", 8))
        self.max_time_label.setStyleSheet("color: #888888;")
        stats_grid.addWidget(self.max_time_label, 1, 2)

        status_layout.addLayout(stats_grid)
        main_layout.addWidget(status_frame, stretch=2)

        # Device Info Frame
        info_frame = QFrame()
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(6)

        info_title = QLabel("Device Information")
        info_title.setObjectName("title")
        info_layout.addWidget(info_title, 0, 0, 1, 2)

        self.device_label = QLabel("Device: Not selected")
        self.device_label.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(self.device_label, 1, 0, 1, 2)

        threshold_icon = QLabel()
        threshold_icon.setPixmap(qta.icon('fa5s.volume-up').pixmap(ICON_SIZE))
        info_layout.addWidget(threshold_icon, 2, 0)

        self.threshold_label = QLabel(f"Threshold: {self.settings_manager.get('threshold', DEFAULT_THRESHOLD)} dB")
        self.threshold_label.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(self.threshold_label, 2, 1)

        filter_icon = QLabel()
        filter_icon.setPixmap(qta.icon('fa5s.filter').pixmap(ICON_SIZE))
        info_layout.addWidget(filter_icon, 3, 0)

        self.filter_label = QLabel("Spike Filter: Enabled")
        self.filter_label.setFont(QFont("Segoe UI", 10))
        info_layout.addWidget(self.filter_label, 3, 1)

        main_layout.addWidget(info_frame, stretch=1)

        # Control Buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.status_icon = QLabel()
        self.status_icon_active = qta.icon('fa5s.broadcast-tower', color='#4CAF50')
        self.status_icon_paused = qta.icon('fa5s.pause-circle', color='#F44336')
        self.status_icon.setPixmap(self.status_icon_active.pixmap(ICON_SIZE))
        control_layout.addWidget(self.status_icon)

        self.status_label = QLabel("Monitoring...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()

        self.toggle_button = QPushButton(qta.icon('fa5s.pause'), "")
        self.toggle_button.setToolTip("Pause Monitoring")
        self.toggle_button.setFixedSize(28, 28)
        self.toggle_button.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.toggle_button)

        settings_button = QPushButton(qta.icon('fa5s.cog'), "")
        settings_button.setToolTip("Settings")
        settings_button.setFixedSize(28, 28)
        settings_button.clicked.connect(self.show_settings)
        control_layout.addWidget(settings_button)

        main_layout.addLayout(control_layout)

    def apply_theme(self) -> None:
        """Apply the selected theme to the window."""
        self.setStyleSheet(ThemeManager.get_stylesheet(self.settings_manager.get("theme", "System")))
        # Animate theme transition
        # Fade in animation
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(200)
        animation.setStartValue(0.9)
        animation.setEndValue(1.0)
        animation.start()

    def setup_tray(self) -> None:
        """Setup the system tray icon and menu."""
        try:
            self.tray_icon = QSystemTrayIcon(self)
            self.update_tray_icon(0)
            self.tray_icon.setToolTip(APP_NAME)

            tray_menu = QMenu()
            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)

            self.pause_action = QAction("Pause", self)
            self.pause_action.triggered.connect(self.toggle_monitoring)
            tray_menu.addAction(self.pause_action)

            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(QApplication.quit)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self._tray_icon_activated)
            self.tray_icon.show()

        except Exception as e:
            logger.error(f"Failed to setup system tray: {e}")
            QMessageBox.warning(self, "Tray Icon Error", f"Could not create system tray icon: {str(e)}")

    def _tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def setup_audio(self) -> None:
        """Setup audio device configuration."""
        self.device_name = self.settings_manager.get("audio_device", "")
        devices = sd.query_devices()
        self.device_id = None

        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0 and device['name'] == self.device_name:
                self.device_id = i
                break

        if self.device_id is None and devices:
            self.device_id = sd.default.device[0]
            if self.device_id is not None:
                self.device_name = devices[self.device_id]['name']

        self.device_label.setText(f"Device: {self.device_name or 'Not selected'}")
        self.filter_label.setText(f"Spike Filter: {'Enabled' if self.settings_manager.get('filter_micro_lags', True, type=bool) else 'Disabled'}")

    def update_tray_icon(self, db_level: float) -> None:
        """Update the system tray icon with current dB level."""
        from PIL import Image, ImageDraw, ImageFont
        import io

        img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_size = 10 if db_level < 100 else 8
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = f"{int(db_level)}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (16 - text_width) // 2
        y = (16 - text_height) // 2

        threshold = self.settings_manager.get("threshold", DEFAULT_THRESHOLD, type=int)
        text_color = (255, 80, 80, 255) if db_level > threshold else (80, 255, 80, 255)
        draw.text((x, y), text, font=font, fill=text_color)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        from PySide6.QtGui import QImage, QPixmap
        qimg = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        icon = QIcon(pixmap)

        if self.tray_icon:
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip(f'{APP_NAME}\nCurrent Level: {db_level:.1f} dB')

    def start_monitoring(self) -> None:
        """Start the noise monitoring timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_noise_level)
        self.update_timer.start(5000)  # Update every 5 seconds

    def update_noise_level(self) -> None:
        """Update the noise level by recording audio."""
        if not self.is_monitoring or self.device_id is None:
            return

        if self.recording_thread is None or not self.recording_thread.is_alive():
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()

    def record_audio(self) -> None:
        """Record and process audio data."""
        try:
            duration = 10
            samples = int(duration * SAMPLE_RATE)
            recording = sd.rec(
                samples,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32',
                device=self.device_id,
                blocking=True
            )

            chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
            chunks = np.array_split(recording, len(recording) // chunk_size)
            db_levels = []

            for chunk in chunks:
                rms = np.sqrt(np.mean(chunk**2))
                if rms > 0:
                    db = 20 * np.log10(rms) + 90  # Convert to SPL
                    db_levels.append(db)

            if db_levels:
                avg_db = np.mean(db_levels)
                max_db = np.max(db_levels)
                min_db = np.min(db_levels)
                current_time = datetime.datetime.now()

                if max_db > self.max_level:
                    self.max_level = max_db
                    self.max_level_time = current_time
                if min_db < self.min_level:
                    self.min_level = min_db
                    self.min_level_time = current_time

                self.noise_label.setText(f"{avg_db:.1f}")
                self.min_label.setText(f"Min: {self.min_level:.1f} dB")
                self.max_label.setText(f"Max: {self.max_level:.1f} dB")
                self.min_time_label.setText(self.min_level_time.strftime("%H:%M:%S") if self.min_level_time else "")
                self.max_time_label.setText(self.max_level_time.strftime("%H:%M:%S") if self.max_level_time else "")

                self.current_db = avg_db
                if self.tray_icon:
                    self.update_tray_icon(avg_db)

                threshold = self.settings_manager.get("threshold", DEFAULT_THRESHOLD, type=int)
                current_time = time.time()

                should_alert = False
                if self.settings_manager.get("filter_micro_lags", True, type=bool):
                    spike_duration_ms = self.settings_manager.get("spike_duration_ms", DEFAULT_SPIKE_DURATION, type=int)
                    required_chunks = int(spike_duration_ms / (CHUNK_DURATION * 1000))
                    high_chunks = sum(1 for db in db_levels if db > threshold)
                    should_alert = high_chunks >= required_chunks
                else:
                    should_alert = max_db > threshold

                if should_alert and (current_time - self.last_alert_time) >= ALERT_COOLDOWN:
                    self.send_alert(avg_db, max_db, min_db, recording)
                    self.last_alert_time = current_time

        except Exception as e:
            logger.error(f"Recording error: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def send_alert(self, avg_db: float, max_db: float, min_db: float, recording: np.ndarray) -> None:
        """Send a Telegram alert with audio recording."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            wav_path = f"noise_alert_{timestamp}.wav"
            ogg_path = wav_path.replace('.wav', '.ogg')

            sf.write(wav_path, recording, SAMPLE_RATE)
            data, samplerate = sf.read(wav_path)
            sf.write(ogg_path, data, samplerate)

            token = self.settings_manager.get("telegram_token", "")
            chat_id = self.settings_manager.get("telegram_chat_id", "")

            if token and chat_id:
                message = f"""
🚨 *NOISE ALERT* 🚨

📊 *Noise Levels (10s sample):*
• Average: {avg_db:.1f} dB SPL
• Maximum: {max_db:.1f} dB SPL
• Minimum: {min_db:.1f} dB SPL

⏰ Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📍 *Alert Details:*
• Threshold: {self.settings_manager.get('threshold', DEFAULT_THRESHOLD)} dB SPL
• Device: {self.device_name}
"""
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                )

                with open(ogg_path, 'rb') as audio:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendAudio",
                        data={"chat_id": chat_id},
                        files={"audio": audio}
                    )

            os.remove(wav_path)
            os.remove(ogg_path)

        except Exception as e:
            logger.error(f"Alert sending error: {e}")
            self.status_label.setText(f"Alert Error: {str(e)}")

    def toggle_monitoring(self) -> None:
        """Toggle monitoring state."""
        self.is_monitoring = not self.is_monitoring
        self.toggle_button.setIcon(qta.icon('fa5s.play' if not self.is_monitoring else 'fa5s.pause'))
        self.toggle_button.setToolTip("Resume Monitoring" if not self.is_monitoring else "Pause Monitoring")
        self.status_label.setText("Paused" if not self.is_monitoring else "Monitoring...")
        self.status_icon.setPixmap(
            self.status_icon_paused.pixmap(ICON_SIZE) if not self.is_monitoring else
            self.status_icon_active.pixmap(ICON_SIZE)
        )
        self.pause_action.setText("Resume" if not self.is_monitoring else "Pause")

    def show_settings(self) -> None:
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.setup_audio()
            self.threshold_label.setText(f"Threshold: {self.settings_manager.get('threshold', DEFAULT_THRESHOLD)} dB")
            self.filter_label.setText(
                f"Spike Filter: {'Enabled' if self.settings_manager.get('filter_micro_lags', True, type=bool) else 'Disabled'}"
            )

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        event.ignore()
        self.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = NoiseMonitorWindow()
    sys.exit(app.exec())