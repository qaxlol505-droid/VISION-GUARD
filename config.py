import torch

# ==========================================
# SERVER & DEVICE CONFIGURATION
# ==========================================
SERVER_IP = "10.100.8.120" 
SERVER_PORT = "8000"
API_URL = f"http://{SERVER_IP}:{SERVER_PORT}/api"

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# ==========================================
# AI SETTINGS & THRESHOLDS
# ==========================================
TARGET_CLASSES = [
    24,  # backpack
    39,  # bottle
    41,  # cup
    43,  # knife
    67   # cellphone
]

CONF_PISTOL = 0.75
CONF_KNIFE = 0.40
CONF_GENERAL = 0.65
FACE_TOLERANCE = 0.65