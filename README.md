# 🎤 Server Noise Monitor with Telegram Alerts

[![GitHub license](https://img.shields.io/github/license/artickc/noiceControll)](https://github.com/artickc/noiceControll/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-Alert%20Bot-blue)](https://core.telegram.org/bots)

A powerful Python-based noise monitoring system designed for server rooms, data centers, and remote hardware monitoring. This tool helps system administrators detect abnormal noise levels from server fans, hard drives, or other hardware components, sending instant alerts via Telegram when noise thresholds are exceeded.

## 🚀 Key Features

- **Real-time Noise Monitoring**: Continuous monitoring of ambient noise levels using system microphones
- **Multi-Device Support**: Monitors all available audio input devices simultaneously
- **Telegram Integration**: Instant alerts when noise levels exceed defined thresholds
- **User-friendly GUI**: Easy-to-use interface for monitoring and configuration
- **Hardware Diagnostics**: Help identify potential hardware issues through noise pattern detection
- **Cross-platform Support**: Works on Windows, Linux, and macOS (primary focus on Windows)

## 🔧 Technical Features

- Root Mean Square (RMS) calculation for accurate noise level measurement
- Configurable sampling rates and monitoring intervals
- Low system resource usage
- Customizable alert thresholds
- Historical data logging for trend analysis
- Background operation mode

## 📋 Prerequisites

- Python 3.8 or higher
- Connected microphone or audio input device
- Internet connection (for Telegram alerts)
- Telegram Bot Token (for notifications)

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/artickc/noiceControll.git
cd noiceControll
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Telegram bot (optional):
   - Create a new bot using [@BotFather](https://t.me/botfather)
   - Copy your bot token
   - Add token to configuration file

## 🚀 Usage

### GUI Mode
```bash
python noise_monitor_gui.py
```

### Command Line Mode
```bash
python noise_monitor.py
```

## ⚙️ Configuration

- `NOISE_THRESHOLD`: Default 60 dB (adjustable)
- `SAMPLING_INTERVAL`: Default 2 seconds
- `ALERT_COOLDOWN`: Default 300 seconds (5 minutes)
- `LOG_FILE`: Logs stored in 'noise_logs.txt'

## 🔍 Use Cases

1. **Server Room Monitoring**
   - Detect failing hard drives
   - Monitor cooling system performance
   - Identify abnormal server behavior

2. **Data Center Management**
   - Early warning system for hardware issues
   - Environmental monitoring
   - Preventive maintenance scheduling

3. **Remote Hardware Monitoring**
   - Unattended server monitoring
   - Remote office equipment supervision
   - Infrastructure health checking

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 👥 Contributors

- [@artickc](https://github.com/artickc) - Project maintainer

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- Server Monitoring Tools
- Hardware Diagnostics
- Telegram Bot Implementations
- Audio Analysis Tools

## 🏷️ Keywords

server monitoring, noise detection, hardware diagnostics, server room monitoring, data center management, telegram alerts, acoustic monitoring, preventive maintenance, server health check, remote monitoring, noise threshold detection, hardware failure prediction, audio analysis, system administration tools, server room acoustics

---

Made with ❤️ by [@artickc](https://github.com/artickc) 