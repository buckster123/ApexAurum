# Hailo-Pi Dev Station Setup Guide

**Created:** 2026-01-23
**Hardware:** Raspberry Pi 5 + Hailo-10H AI Accelerator
**Status:** FULLY OPERATIONAL

---

## Quick Reference

```bash
# Hailo device check
hailortcli fw-control identify

# Run YOLOv11 benchmark
hailortcli benchmark /usr/share/hailo-models/yolov11m_h10.hef -t 10

# Test camera with Hailo AI (when camera connected)
rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov8_inference.json

# Reload Hailo driver (if needed after reboot)
sudo modprobe hailo1x_pci
```

---

## System Specifications

| Component | Details |
|-----------|---------|
| **SBC** | Raspberry Pi 5 |
| **AI Accelerator** | Hailo-10H (40 TOPS INT4) |
| **PCIe** | Gen 3.0 x1 (8GT/s) |
| **OS** | Debian Trixie (13) |
| **Kernel** | 6.12.62+rpt-rpi-2712 |
| **Python** | 3.13.5 |
| **HailoRT** | 5.1.1 |

### Performance Benchmarks

**Vision Models:**
| Model | FPS | Temperature |
|-------|-----|-------------|
| YOLOv11m (detection) | 71 | 35-37°C |
| YOLOv8m (detection) | ~80 | 35°C |
| ResNet50 (classification) | 307 | 35°C |
| YOLOv5n-seg (segmentation) | 47 | 36°C |

**LLM Models (via hailo-ollama):**
| Model | Size | Tokens/sec | Use Case |
|-------|------|------------|----------|
| qwen2:1.5b | 1.7GB | ~7 | General purpose |
| qwen2.5-instruct:1.5b | 2.4GB | ~7 | Chat/instructions |
| qwen2.5-coder:1.5b | 1.8GB | ~8 | Code generation |
| deepseek_r1_distill_qwen:1.5b | 2.4GB | ~6.7 | Chain-of-thought reasoning |
| llama3.2:3b | 3.4GB | ~6 | Meta's latest (largest) |

---

## Installed Software

### AI/ML Stack
- [x] HailoRT 5.1.1
- [x] Hailo TAPPAS
- [x] Hailo GenAI Model Zoo 5.1.1 (LLMs)
- [x] hailo-ollama (Ollama-compatible LLM API)
- [x] PyTorch 2.9.1
- [x] Ultralytics (YOLOv8/11)
- [x] ONNX + ONNXRuntime
- [x] OpenCV 4.13
- [x] Supervision
- [x] picamera2
- [x] PEFT 0.18.1 (LoRA fine-tuning)
- [x] Transformers 4.57.6
- [x] HuggingFace Datasets + Accelerate

### LoRa Radio (IoT Wireless)
- [x] pyLoRa, adafruit-circuitpython-rfm9x/rfm69
- [x] SPI enabled (/dev/spidev0.0, 0.1, 10.0)
- [ ] Hardware needed (Waveshare SX1262 HAT ~$25)

### Development Tools
- [x] Docker 29.1.5
- [x] Git (SSH: buckster123)
- [x] Wokwi CLI 0.20.0
- [x] Node.js 20.19.2
- [x] CMake + Ninja
- [x] tmux, btop, jq

### Services
- [x] Redis (port 6379)
- [x] Mosquitto MQTT (port 1883)
- [x] GStreamer full stack
- [x] FFmpeg
- [x] PulseAudio

### IoT/Hardware
- [x] I2C enabled
- [x] SPI enabled
- [x] paho-mqtt
- [x] gpiozero
- [x] pyserial

### ApexAurum
- [x] 88 tools loaded (includes 7 Hailo vision tools)
- [x] 590 vectors (Village Protocol)
- [x] Full music pipeline
- [x] 4 agents (AZOTH, ELYSIAN, VAJRA, KETHER)

---

## Models On Disk

### Hailo-10H Native (6 models)
```
/usr/share/hailo-models/
├── yolov11m_h10.hef      (27M) - Object Detection
├── yolov8m_h10.hef       (21M) - Object Detection
├── yolov8m_pose_h10.hef  (28M) - Pose Estimation
├── yolov8s_pose_h10.hef  (14M) - Pose Estimation
├── yolov5n_seg_h10.hef   (3.4M) - Segmentation
└── resnet_v1_50_h10.hef  (23M) - Classification
```

### Hailo-8/8L Compatible (12 models)
```
├── yolov8s_h8.hef / yolov8s_h8l.hef
├── yolov6n_h8.hef / yolov6n_h8l.hef
├── yolov5s_personface_h8l.hef
├── yolov8s_pose_h8.hef / yolov8s_pose_h8l_pi.hef
├── yolox_s_leaky_h8l_rpi.hef
├── scrfd_2.5g_h8l.hef
└── resnet_v1_50_h8l.hef
```

### Hailo LLM Models (11GB total)
```
~/.local/share/hailo-ollama/models/blob/
├── qwen2:1.5b               (1.7GB)
├── qwen2.5-instruct:1.5b    (2.4GB)
├── qwen2.5-coder:1.5b       (1.8GB)
├── deepseek_r1_distill:1.5b (2.4GB)
└── llama3.2:3b              (3.4GB)
```

---

## Manual Setup Required

### 1. Hailo Developer Zone - COMPLETE

Registered at: https://hailo.ai/developer-zone/

**Downloaded and installed:**
- `hailo_gen_ai_model_zoo_5.1.1_arm64.deb` - LLM support

```bash
# Installation done:
sudo dpkg -i hailo_gen_ai_model_zoo_5.1.1_arm64.deb

# Symlink manifests to user directory:
ln -sf /usr/share/hailo-ollama/models/manifests ~/.local/share/hailo-ollama/models/manifests

# All 5 LLM models pulled:
# qwen2:1.5b, qwen2.5-instruct:1.5b, qwen2.5-coder:1.5b,
# deepseek_r1_distill_qwen:1.5b, llama3.2:3b
```

### 2. Docker Group (one-time)

```bash
# Apply docker group without logout
newgrp docker

# Verify
docker run hello-world
```

---

## 🛒 MASTER SHOPPING LIST

### 🎯 PRIORITY 1: VISION (~$50-130)

| Item | Price | Why |
|------|-------|-----|
| **Pi Camera Module 3** | $25 | Autofocus, HDR, 71 FPS with Hailo |
| Pi Camera Module 3 NoIR | $25 | Night vision (add IR LEDs) |
| IR LED Ring | $10 | For NoIR night operation |
| *OR* Logitech C920 | $70 | USB fallback, reliable |

### 📻 PRIORITY 2: LoRa RADIO (~$25-50)

*Libraries already installed! Just needs hardware.*

| Item | Price | Range | Notes |
|------|-------|-------|-------|
| **Waveshare SX1262 LoRa HAT** | $25 | 5km+ | Plug-and-play Pi HAT, 868/915MHz |
| Adafruit RFM95W Breakout | $20 | 2km+ | Needs wiring, great docs |
| LILYGO T-Beam (pair) | $70 | 10km+ | ESP32+LoRa+GPS, USB serial |
| RAK2287 Concentrator | $99 | 15km+ | Full LoRaWAN gateway |

### 🧠 PRIORITY 3: EEG/BCI (~$200-400)

*ApexAurum has EEG tools ready!*

| Item | Price | Channels | Notes |
|------|-------|----------|-------|
| **OpenBCI Cyton** | $250 | 8ch | Research-grade, great API |
| OpenBCI Ganglion | $200 | 4ch | Budget option |
| Muse 2 Headband | $250 | 4ch | Consumer, meditation focus |
| Neurosity Crown | $1000 | 8ch | Premium, focus tracking |

### 🌡️ PRIORITY 4: SENSORS & IoT (~$20-50)

| Item | Price | Use Case |
|------|-------|----------|
| BME680 Breakout | $20 | Temp/humidity/pressure/air quality |
| VL53L1X ToF Sensor | $15 | Distance sensing (4m range) |
| MPU-6050 IMU | $5 | Motion/orientation |
| GPS Module (NEO-6M) | $15 | Location tracking |
| Servo Kit (SG90 x5) | $10 | Basic robotics |

### 🔥 COMPLETE BUILD OPTIONS

| Build | Components | Total | What You Get |
|-------|------------|-------|--------------|
| **Minimal** | Pi Cam 3 | ~$25 | Vision AI @ 71 FPS |
| **Basic** | Pi Cam 3 + LoRa HAT | ~$50 | Vision + 5km radio |
| **Research** | + OpenBCI Ganglion + sensors | ~$300 | + Brain interface + IoT |
| **Full Lab** | See below | ~$1,200 | EVERYTHING |

---

## 🧪 FULL LAB BUILD (The Dream Setup)

### 3D Vision Stack (~$400)
| Item | Price | Purpose |
|------|-------|---------|
| **Intel RealSense D435i** | $300 | RGB + Depth + IMU, SLAM-ready |
| Pi Camera Module 3 | $25 | High-speed 2D (71 FPS with Hailo) |
| Pi Camera Module 3 NoIR | $25 | Night vision channel |
| IR LED Array (48 LEDs) | $15 | Invisible illumination |
| FLIR Lepton 3.5 | $200 | Thermal imaging (optional) |
| *Subtotal* | *$365-565* | |

### Brain-Computer Interface (~$350)
| Item | Price | Purpose |
|------|-------|---------|
| **OpenBCI Cyton Board** | $250 | 8-channel research-grade EEG |
| OpenBCI Ultracortex Mark IV | $350 | 3D-printed headset (or DIY) |
| *OR* OpenBCI Ganglion | $200 | Budget 4-channel option |
| Electrode Gel + Supplies | $30 | Consumables |
| *Subtotal* | *$230-630* | |

### Long-Range Comms (~$100)
| Item | Price | Purpose |
|------|-------|---------|
| **Waveshare SX1262 LoRa HAT** | $25 | 5km+ Pi HAT |
| LILYGO T-Beam x2 | $70 | Remote nodes with GPS |
| Antenna upgrades | $20 | Extended range |
| *Subtotal* | *$115* | |

### Sensor Array (~$80)
| Item | Price | Purpose |
|------|-------|---------|
| BME680 | $20 | Air quality, temp, humidity, pressure |
| VL53L1X ToF | $15 | Precise distance (4m) |
| MPU-9250 IMU | $15 | 9-axis motion |
| NEO-6M GPS | $15 | Location |
| MAX30102 | $10 | Heart rate + SpO2 |
| Sound sensor | $5 | Audio level detection |
| *Subtotal* | *$80* | |

### Robotics/Actuators (~$50)
| Item | Price | Purpose |
|------|-------|---------|
| SG90 Servo x5 | $10 | Pan/tilt, grippers |
| 28BYJ-48 Stepper x2 | $10 | Precise positioning |
| L298N Motor Driver | $8 | DC motor control |
| DC Motors x4 | $15 | Wheels/movement |
| Relay Module 4ch | $7 | High-power switching |
| *Subtotal* | *$50* | |

### 💰 FULL LAB TOTAL

| Tier | Config | Total |
|------|--------|-------|
| **Essential** | RealSense + Ganglion + LoRa + Sensors | ~$650 |
| **Research** | + Cyton + NoIR + Thermal | ~$1,100 |
| **Ultimate** | + Ultracortex + Robotics + Extras | ~$1,500+ |

### 🎯 RECOMMENDED ORDER OF PURCHASE

1. **Week 1:** Pi Camera Module 3 ($25) - Get vision working
2. **Week 2:** Waveshare LoRa HAT ($25) - Add comms
3. **Week 3:** Intel RealSense D435i ($300) - 3D depth
4. **Week 4:** OpenBCI Ganglion or Cyton ($200-250) - BCI
5. **Later:** Thermal, sensors, robotics as needed

### 💡 QUICK PICKS BY USE CASE

| I want to... | Get this | Cost |
|--------------|----------|------|
| Try vision AI | Pi Camera Module 3 | $25 |
| Add night vision | + NoIR + IR LEDs | +$35 |
| Talk to remote sensors | Waveshare LoRa HAT | $25 |
| Track brain states | OpenBCI Ganglion | $200 |
| Make a robot | Servos + IMU + ToF | $30 |
| Detect body heat | FLIR Lepton | $200 |
| Get 3D depth | Intel RealSense D435i | $300 |

---

## Camera Deep Dive

### OFFICIAL PI CAMERAS

| Camera | Resolution | FPS | Price | Notes |
|--------|-----------|-----|-------|-------|
| **Camera Module 3** | 12MP, 4K | 50fps@1080p | $25 | Autofocus, HDR, best value |
| **Camera Module 3 Wide** | 12MP, 4K | 50fps@1080p | $35 | 120° FOV |
| **Camera Module 3 NoIR** | 12MP, 4K | 50fps@1080p | $25 | Night vision (needs IR) |
| **Global Shutter Camera** | 1.6MP | 120fps | $50 | No motion blur |
| **AI Camera (IMX500)** | 12MP | - | $70 | On-sensor AI |
| **HQ Camera** | 12.3MP | 40fps | $50 | C/CS mount lenses |

### USB CAMERAS

| Camera | Resolution | FPS | Price | Notes |
|--------|-----------|-----|-------|-------|
| Logitech C920/C922 | 1080p | 30fps | $70 | Reliable workhorse |
| Logitech Brio 4K | 4K | 30fps | $130 | HDR, Windows Hello |
| Razer Kiyo Pro | 1080p | 60fps | $100 | Great low light |
| Elgato Facecam | 1080p | 60fps | $150 | Uncompressed, pro |

### SPECIALIZED CAMERAS

| Camera | Type | Resolution | Price | Notes |
|--------|------|-----------|-------|-------|
| **Intel RealSense D435i** | Depth+RGB | 1080p+depth | $300 | 3D vision, SLAM |
| **OAK-D Lite** | Depth+AI | 4K+stereo | $150 | On-device AI |
| **FLIR Lepton 3.5** | Thermal | 160x120 | $200 | Heat detection |
| **Arducam 64MP Hawkeye** | High-res | 64MP | $45 | Ultra detail |
| **Waveshare IMX219 Stereo** | Stereo pair | 8MP x2 | $50 | Depth from stereo |

### MULTI-CAMERA OPTIONS

| Setup | Components | Price | Use Case |
|-------|------------|-------|----------|
| Dual CSI | 2x Pi Cam 3 + splitter | ~$60 | Stereo depth |
| CSI + USB | Pi Cam + Logitech | ~$95 | Wide + zoom |
| Arducam Multi-Cam | 4-camera HAT + cams | ~$120 | 360° coverage |

---

## Upgrade Roadmap

### Phase 1: Basic Vision (Current)
- [x] Hailo-10H running
- [ ] Add Pi Camera Module 3
- [ ] Test real-time object detection

### Phase 2: Enhanced Vision
- [ ] Add NoIR camera + IR LEDs (night vision)
- [ ] Download more H10 models from Hailo
- [ ] Set up dual-camera stereo

### Phase 3: Advanced AI - COMPLETE
- [x] Register Hailo Dev Zone
- [x] Install hailo-model-zoo-genai
- [x] Run local LLMs (5 models: Qwen2, Qwen2.5, DeepSeek R1, Llama 3.2)
- [ ] Add depth camera (RealSense or OAK-D)

### Phase 4: Full Integration
- [x] Vision tools for agents (7 tools)
- [x] LoRA fine-tuning system ready
- [ ] Connect cameras to ApexAurum
- [ ] Thermal camera for robotics
- [ ] Multi-camera orchestration

---

## LoRA Fine-Tuning (reusable_lib/training/)

Memory-efficient model fine-tuning for Pi 5:

```python
from reusable_lib.training.lora_trainer import LoRATrainer, TrainingConfig

# Pi 5 optimized (4GB RAM safe)
config = TrainingConfig.for_pi5(
    model_name="gpt2",  # or Qwen2-0.5B, Gemma-2B
    output_dir="./my_lora",
    num_epochs=3,
)

trainer = LoRATrainer(config)
trainer.load_model()
trainer.train(dataset)
trainer.save_model()
```

**Features:**
- CPU/ARM64 optimized (no CUDA needed)
- Gradient checkpointing for memory efficiency
- Auto-detects LoRA target modules per architecture
- Supports: GPT-2, Gemma, Llama, Qwen, Mistral, Phi
- Pre-built tool-calling training examples

**Test:** `python reusable_lib/training/example_train.py --test`

---

## Useful Commands

### Hailo Vision
```bash
# Check device
hailortcli scan
hailortcli fw-control identify

# Benchmark model
hailortcli benchmark /path/to/model.hef -t 10

# Monitor temperature
watch -n 1 'hailortcli fw-control identify | grep -i temp'
```

### Hailo LLM (hailo-ollama on port 11434)
```bash
# Start server
hailo-ollama &

# Check version
curl http://localhost:11434/api/version

# List downloaded models
curl http://localhost:11434/api/tags

# Pull a model
curl http://localhost:11434/api/pull -H 'Content-Type: application/json' \
  -d '{"model": "qwen2.5-coder:1.5b", "stream": false}'

# Generate text
curl http://localhost:11434/api/generate -H 'Content-Type: application/json' \
  -d '{"model": "qwen2:1.5b", "prompt": "Hello world", "stream": false}'

# Test DeepSeek reasoning
curl http://localhost:11434/api/generate -H 'Content-Type: application/json' \
  -d '{"model": "deepseek_r1_distill_qwen:1.5b", "prompt": "Solve: 15 * 17", "stream": false}'
```

### Camera
```bash
# List cameras
rpicam-hello --list-cameras

# Preview
rpicam-hello -t 0

# With Hailo AI overlay
rpicam-hello -t 0 --post-process-file /usr/share/rpi-camera-assets/hailo_yolov8_inference.json

# Record video
rpicam-vid -t 10000 -o test.h264

# USB camera
v4l2-ctl --list-devices
ffplay /dev/video0
```

### Services
```bash
# Redis
redis-cli ping

# MQTT
mosquitto_pub -t test -m "hello"
mosquitto_sub -t test

# Docker
docker ps
docker images
```

### System
```bash
# Temperature
vcgencmd measure_temp

# Throttling status
vcgencmd get_throttled

# Memory
free -h

# Storage
df -h
```

---

## Troubleshooting

### Hailo not detected after reboot
```bash
sudo modprobe hailo1x_pci
ls /dev/hailo*
```

### Driver version mismatch
```bash
# Check kernel vs module
uname -r
modinfo hailo1x_pci | grep version

# Reinstall if mismatched
sudo apt reinstall h10-hailort-pcie-driver
```

### Camera not working
```bash
# Check if detected
rpicam-hello --list-cameras

# Check /boot/firmware/config.txt has:
camera_auto_detect=1
```

### Docker permission denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## Links

- **Hailo Developer Zone:** https://hailo.ai/developer-zone/
- **Hailo Model Zoo:** https://github.com/hailo-ai/hailo_model_zoo
- **Hailo GenAI:** https://github.com/hailo-ai/hailo_model_zoo_genai
- **Hailo Community:** https://community.hailo.ai
- **Pi Camera Docs:** https://www.raspberrypi.com/documentation/computers/camera_software.html
- **Pi AI Docs:** https://www.raspberrypi.com/documentation/computers/ai.html

---

**Last Updated:** 2026-01-23
**Maintainer:** buckster123 / ApexAurum Project
