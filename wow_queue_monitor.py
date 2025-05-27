import cv2
import numpy as np
from mss import mss
import pytesseract

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import logging
import sys
from pathlib import Path
import time
import socket
from PIL import Image

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
PHONE_IP = "192.168.1.130"  # Change this to your phone's IP address
PORT = 9876
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048
CHANNELS = 2
CORRELATION_THRESHOLD = 0.7  # Adjust this value between 0 and 1

# Screen capture settings
def get_screen_region():
    # Get primary monitor resolution
    with mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        width = monitor['width']
        height = monitor['height']
        
        # Calculate region:
        # Vertical: Top 50% of screen
        # Horizontal: Middle third (so starting at 33% and ending at 66%)
        region = {
            'top': 0,  # Start from top
            'height': height // 2,  # Top half of screen
            'left': width // 3,  # Start at 1/3 of screen width
            'width': width // 3   # Take 1/3 of screen width
        }
        logging.info(f"Monitoring region: {region} (Based on {width}x{height} resolution)")
        return region

SCREEN_REGION = get_screen_region()
SCAN_INTERVAL = 1.0  # How often to scan for text (in seconds)
KEYWORDS = ['ready', 'queue', 'solo shuffle', 'arena', 'blitz']  # Keywords to look for

class WoWQueueMonitor:
    def __init__(self, phone_ip="192.168.1.130", port=9876):
        self.phone_ip = phone_ip
        self.port = port
        self.sock = None
        self.sct = mss()
        self.last_notification_time = 0
        self.setup_udp_socket()
        
        # Test if tesseract is installed
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            logging.error("Tesseract is not installed. Please install it from: https://github.com/UB-Mannheim/tesseract/wiki")
            sys.exit(1)

    def capture_screen(self):
        """Capture the top portion of the screen where queue pop appears"""
        try:
            screenshot = self.sct.grab(SCREEN_REGION)
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            return np.array(img)
        except Exception as e:
            logging.error(f"Error capturing screen: {e}")
            return None
            
    def process_image(self, img):
        """Process the image and extract text"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # Threshold to get black text
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # Extract text
            text = pytesseract.image_to_string(binary).lower()
            
            # Log the text if it's not empty
            if text.strip():
                logging.info(f"Detected text: {text.strip()}")
                
            return text
        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return ""

    def setup_udp_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.info(f"UDP socket created, will send to {self.phone_ip}:{self.port}")

    def notify_phone(self):
        try:
            message = "queue_pop"
            self.sock.sendto(message.encode(), (self.phone_ip, self.port))
            logging.info(f"Sent notification to {self.phone_ip}:{self.port} - {message}")
        except Exception as e:
            logging.error(f"Error sending notification: {e}")

    def check_for_queue(self):
        """Check if any queue-related text is visible"""
        try:
            # Capture and process screen
            img = self.capture_screen()
            if img is None:
                return
                
            # Get text from image
            text = self.process_image(img)
            
            # Check for keywords
            current_time = time.time()
            if any(keyword in text.lower() for keyword in KEYWORDS):
                # Prevent spam notifications
                if current_time - self.last_notification_time >= 5:
                    logging.info("Queue pop detected!")
                    self.notify_phone()
                    self.last_notification_time = current_time
                    
        except Exception as e:
            logging.error(f"Error checking queue: {e}")

    def select_audio_device(self):
        # List all audio devices
        devices = sd.query_devices()
        print("\nAvailable audio devices:")
        print("-" * 50)
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Only show input devices
                print(f"{i}: {device['name']} (Inputs: {device['max_input_channels']})")
        
        while True:
            try:
                choice = input("\nSelect the number of your audio output device (e.g., speakers/headphones): ")
                device_id = int(choice)
                if 0 <= device_id < len(devices) and devices[device_id]['max_input_channels'] > 0:
                    logging.info(f"Selected device: {devices[device_id]['name']}")
                    return device_id
                else:
                    print("Invalid device number. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def start_monitoring(self):
        try:
            logging.info("Starting screen monitoring...")
            logging.info(f"Looking for keywords: {KEYWORDS}")
            logging.info(f"Monitoring screen region: {SCREEN_REGION}")
            
            while True:
                self.check_for_queue()
                time.sleep(SCAN_INTERVAL)
                
        except KeyboardInterrupt:
            logging.info("Stopping monitor...")
        except Exception as e:
            logging.error(f"Error in monitoring: {e}")
            sys.exit(1)

if __name__ == "__main__":
    print("WoW Queue Monitor")
    print("----------------")
    print(f"1. Make sure your phone's IP address is correct in the script: {PHONE_IP}")
    print("2. Make sure WoW's audio is not muted")
    print("3. Press Ctrl+C to stop monitoring")
    print("----------------")
    
    monitor = WoWQueueMonitor()
    monitor.start_monitoring()
