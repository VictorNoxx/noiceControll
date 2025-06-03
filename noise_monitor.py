import sounddevice as sd
import numpy as np
import time
import os
import requests
import wave
import datetime
import soundfile as sf
from scipy import signal

# Telegram configuration
TOKEN = ""
CHAT_ID = ""

# Noise level states
NOISE_NORMAL = 0
NOISE_HIGH = 1

def get_noise_emoji(db_level):
    """Get appropriate emoji based on noise level."""
    if db_level < -60:
        return "🔇"  # Muted
    elif db_level < -50:
        return "🔈"  # Low volume
    elif db_level < -40:
        return "🔉"  # Medium-low volume
    elif db_level < -30:
        return "🔊"  # Medium volume
    elif db_level < -20:
        return "🔊"  # Medium-high volume
    elif db_level < -10:
        return "🔊"  # High volume
    else:
        return "🔊"  # Very high volume

def format_telegram_message(db_level, threshold_db, audio_file_path, is_alert=True):
    """Format a beautiful Telegram message with emojis."""
    emoji = get_noise_emoji(db_level)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if is_alert:
        return f"""
🚨 NOISE ALERT 🚨
{emoji} Current noise level: {db_level:.1f} dB SPL
⚠️ Exceeded threshold: {threshold_db} dB SPL
⏰ Time: {timestamp}

📝 Details:
• Noise level: {db_level:.1f} dB SPL
• Threshold: {threshold_db} dB SPL
• Recording: {audio_file_path}

🎧 Audio recording attached below ⬇️
"""
    else:
        return f"""
✅ NOISE RETURNED TO NORMAL ✅
{emoji} Current noise level: {db_level:.1f} dB SPL
⏰ Time: {timestamp}

📝 Details:
• Current level: {db_level:.1f} dB SPL
• Normal threshold: {threshold_db} dB SPL
"""

def normalize_audio(audio_data):
    """Normalize audio data to prevent clipping and improve quality."""
    # Ensure audio_data is a 1D array
    audio_data = np.squeeze(audio_data)
    
    # Remove DC offset
    audio_data = audio_data - np.mean(audio_data)
    
    # Apply a simple moving average filter
    window_size = min(1000, len(audio_data) // 2)
    if window_size > 0:
        audio_data = np.convolve(audio_data, np.ones(window_size)/window_size, mode='same')
    
    # Normalize to prevent clipping while maintaining relative levels
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data * (0.9 / max_val)  # Leave some headroom
    
    return audio_data

def amplitude_to_db(amplitude, reference=1.0):
    """Convert amplitude to decibels."""
    if amplitude <= 0:
        return -float('inf')
    return 20 * np.log10(amplitude / reference)

def get_noise_level(data):
    """Calculate RMS of audio data and convert to dB."""
    if data.ndim > 1:  # If stereo, convert to mono
        data = np.mean(data, axis=1)
    rms = np.sqrt(np.mean(data**2))
    db = amplitude_to_db(rms)
    return db

def is_physical_device(device_name):
    """Check if the device is likely a physical microphone."""
    virtual_keywords = [
        'virtual', 'mapper', 'streaming', 'oculus',
        'sound mapper', 'directsound', 'desktop audio'
    ]
    device_name_lower = device_name.lower()
    return not any(keyword in device_name_lower for keyword in virtual_keywords)

def send_telegram_alert(message, audio_file_path=None):
    """Send an alert to Telegram with a message and optionally an audio file."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message: {response.text}")

    if audio_file_path:
        # Convert WAV to OGG for better Telegram compatibility and smaller size
        ogg_file_path = audio_file_path.replace('.wav', '.ogg')
        data, samplerate = sf.read(audio_file_path)
        sf.write(ogg_file_path, data, samplerate)

        # Send the audio file
        url = f"https://api.telegram.org/bot{TOKEN}/sendAudio"
        files = {
            'audio': open(ogg_file_path, 'rb')
        }
        data = {
            'chat_id': CHAT_ID
        }
        response = requests.post(url, files=files, data=data)
        if response.status_code == 200:
            print("Audio file sent successfully.")
            # Clean up temporary files
            os.remove(audio_file_path)
            os.remove(ogg_file_path)
        else:
            print(f"Failed to send audio file: {response.text}")

def get_noise_description(db_level):
    """Convert dB level to human-readable noise description."""
    if db_level < -60:
        return "Very Quiet (Almost Silent)"
    elif db_level < -50:
        return "Quiet (Whisper)"
    elif db_level < -40:
        return "Moderate (Quiet Room)"
    elif db_level < -30:
        return "Normal (Normal Conversation)"
    elif db_level < -20:
        return "Loud (Office Noise)"
    elif db_level < -10:
        return "Very Loud (City Traffic)"
    else:
        return "Extremely Loud (Power Tools/Concert)"

def get_optimal_device_settings(device_id):
    """Get optimal settings for the audio device."""
    device_info = sd.query_devices(device_id)
    return {
        'samplerate': int(device_info['default_samplerate']),
        'channels': min(device_info['max_input_channels'], 2),  # Use stereo if available
        'dtype': 'float32',
        'latency': 'low'  # Use low latency for better quality
    }

def monitor_usb_mic(duration=1, record_duration=10, threshold_db=30, alert_interval=600):
    """Monitor the USB MIC PRO and record audio if noise level exceeds threshold."""
    devices = sd.query_devices()
    usb_mic_id = None
    
    # Find the USB MIC PRO
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0 and device['name'] == 'Microphone (USB MIC PRO)':
            usb_mic_id = i
            break

    if usb_mic_id is None:
        print("USB MIC PRO not found!")
        return

    # Get optimal device settings
    settings = get_optimal_device_settings(usb_mic_id)
    print(f"Using settings: {settings}")

    last_alert_time = 0
    noise_state = NOISE_NORMAL

    # Create a stream for continuous monitoring
    with sd.InputStream(
        device=usb_mic_id,
        **settings,
        callback=None
    ) as stream:
        while True:
            try:
                print(f"\nListening to: Microphone (USB MIC PRO)")
                # Read audio data
                recording = sd.rec(
                    int(duration * settings['samplerate']),
                    **settings,
                    device=usb_mic_id,
                    blocking=True
                )

                noise_level_db = get_noise_level(recording)
                noise_description = get_noise_description(noise_level_db)
                print(f"Noise level: {noise_level_db:.1f} dB - {noise_description}")

                offset = 90
                db_spl = noise_level_db + offset
                print(f"Estimated SPL: {db_spl:.1f} dB SPL (raw: {noise_level_db:.1f} dBFS)")

                current_time = time.time()
                
                if db_spl > threshold_db and (current_time - last_alert_time) >= alert_interval:
                    if noise_state == NOISE_NORMAL:
                        print(f"Noise level exceeds {threshold_db} dB. Recording audio for {record_duration} seconds...")
                        try:
                            # High-quality recording
                            long_recording = sd.rec(
                                int(record_duration * settings['samplerate']),
                                **settings,
                                device=usb_mic_id,
                                blocking=True
                            )

                            # Save as WAV with high quality
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            audio_file_path = f"noise_alert_{timestamp}.wav"
                            sf.write(audio_file_path, long_recording, settings['samplerate'])

                            message = format_telegram_message(db_spl, threshold_db, audio_file_path, True)
                            send_telegram_alert(message, audio_file_path)
                            last_alert_time = current_time
                            noise_state = NOISE_HIGH
                        except Exception as e:
                            print(f"Error during recording: {str(e)}")
                            continue
                
                elif db_spl <= threshold_db and noise_state == NOISE_HIGH:
                    message = format_telegram_message(db_spl, threshold_db, None, False)
                    send_telegram_alert(message)
                    noise_state = NOISE_NORMAL

                time.sleep(1)
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break

if __name__ == "__main__":
    print("Noise Level Monitor (USB MIC PRO Only)")
    print("----------------------------------------")
    monitor_usb_mic() 