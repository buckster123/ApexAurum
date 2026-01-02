# 🌈 Rainbow Pulse - Interactive LED Controller for Raspberry Pi 5

A fun, interactive Python script that creates mesmerizing color patterns on an RGB LED using your Raspberry Pi 5's GPIO pins. Control speed, brightness, and switch between different animation patterns in real-time!

## ✨ Features

- **4 Beautiful Patterns:**
  - 🌈 **Rainbow** - Smooth cycling through all colors
  - 💓 **Pulse** - Gentle white pulsing effect
  - ⚡ **Strobe** - RGB color strobe
  - 🔥 **Fire** - Flickering fire simulation

- **Interactive Controls:**
  - Real-time speed adjustment
  - Brightness control
  - Pause/resume animation
  - Pattern switching
  - Live status display

- **Smart Design:**
  - Non-blocking keyboard input
  - Smooth PWM control
  - Demo mode if GPIO isn't available
  - Clean resource management

## 🔧 Hardware Requirements

### Components Needed:
1. **Raspberry Pi 5** (or any Pi with GPIO)
2. **Common Cathode RGB LED** (or 3 separate LEDs)
3. **3x 220Ω Resistors** (for current limiting)
4. **Breadboard and jumper wires**

### Wiring Diagram:

```
Raspberry Pi GPIO        RGB LED
─────────────────────────────────
GPIO 17 (Pin 11) ──[220Ω]── Red Anode
GPIO 27 (Pin 13) ──[220Ω]── Green Anode
GPIO 22 (Pin 15) ──[220Ω]── Blue Anode
GND (Pin 9)      ────────── Common Cathode
```

**Pin Reference:**
- GPIO 17 (Physical Pin 11) → Red LED
- GPIO 27 (Physical Pin 13) → Green LED  
- GPIO 22 (Physical Pin 15) → Blue LED
- GND (Physical Pin 9) → LED Common Cathode

> **Note:** If using a common anode RGB LED, you'll need to modify the code to invert the PWM values and connect the common anode to 3.3V instead.

## 📦 Installation

### 1. Install Dependencies

```bash
# Update your system
sudo apt update && sudo apt upgrade -y

# Install RPi.GPIO (usually pre-installed on Raspberry Pi OS)
sudo apt install python3-rpi.gpio

# Or use pip
pip3 install RPi.GPIO
```

### 2. Download the Script

```bash
# Clone or download the script
wget https://your-url/rainbow_pulse.py

# Make it executable
chmod +x rainbow_pulse.py
```

### 3. Run It!

```bash
python3 rainbow_pulse.py
```

Or run directly (if made executable):
```bash
./rainbow_pulse.py
```

## 🎮 Controls

Once running, use these keyboard controls:

| Key | Action |
|-----|--------|
| **↑** | Increase animation speed |
| **↓** | Decrease animation speed |
| **+** | Increase brightness |
| **-** | Decrease brightness |
| **SPACE** | Pause/Resume animation |
| **P** | Cycle through patterns |
| **Q** | Quit program |

## 🎯 How It Works

### PWM (Pulse Width Modulation)
The script uses PWM to control LED brightness. By rapidly switching the GPIO pins on/off at 1000 Hz and varying the duty cycle (0-100%), we can create any color by mixing red, green, and blue at different intensities.

### Color Generation
1. **HSV to RGB Conversion:** Colors are generated in HSV (Hue, Saturation, Value) color space for smooth transitions, then converted to RGB.
2. **Pattern Functions:** Each animation pattern is a mathematical function that returns RGB values based on time.
3. **Real-time Control:** The main loop continuously reads keyboard input and updates the LED colors without blocking.

### Code Highlights

```python
# HSV color space makes rainbow effects easy
def rainbow_pattern(t: float):
    hue = (t % 1.0)  # Cycle through hues 0-1
    return hsv_to_rgb(hue, 1.0, 1.0)

# PWM controls intensity
red_pwm.ChangeDutyCycle(red * brightness * 100)
```

## 🔧 Customization

### Change GPIO Pins
Edit these lines at the top of the script:
```python
RED_PIN = 17    # Change to your red LED pin
GREEN_PIN = 27  # Change to your green LED pin
BLUE_PIN = 22   # Change to your blue LED pin
```

### Add Your Own Pattern
Add a new pattern function:
```python
def my_pattern(t: float) -> Tuple[float, float, float]:
    """Your custom pattern"""
    r = math.sin(t) * 0.5 + 0.5
    g = math.cos(t) * 0.5 + 0.5
    b = 0.5
    return r, g, b
```

Then add it to the pattern list in `main()`:
```python
pattern_funcs = [rainbow_pattern, pulse_pattern, strobe_pattern, fire_pattern, my_pattern]
pattern_names = ["Rainbow", "Pulse", "Strobe", "Fire", "MyPattern"]
```

### Adjust PWM Frequency
Change the frequency (default 1000 Hz):
```python
red_pwm = GPIO.PWM(RED_PIN, 2000)  # 2000 Hz
```

## 🐛 Troubleshooting

### "Permission denied" error
Run with sudo:
```bash
sudo python3 rainbow_pulse.py
```

### "RPi.GPIO not found"
The script will run in demo mode. Install the library:
```bash
sudo apt install python3-rpi.gpio
```

### LED not lighting up
1. Check your wiring matches the pin numbers in the code
2. Verify you're using a common cathode RGB LED (or adjust code for common anode)
3. Test individual colors by setting them to max brightness
4. Check resistor values (220Ω is standard, but 330Ω works too)

### Colors look wrong
- If using common anode LED, invert the PWM values:
  ```python
  red_pwm.ChangeDutyCycle((1.0 - r) * brightness * 100)
  ```

### Keyboard not responding
- Make sure terminal is in focus
- Try running in a direct terminal (not through SSH on some setups)

## 🚀 Advanced Ideas

- **Add sound reactivity** using a microphone module
- **Multiple LEDs** in a strip for wave effects
- **Web interface** using Flask to control from your phone
- **Motion sensor** to trigger patterns when someone walks by
- **Temperature-based colors** using a sensor
- **Sync multiple Pis** for a light show

## 📝 Technical Notes

- **Non-blocking Input:** Uses `select` and terminal raw mode for responsive controls
- **Thread-safe:** Single-threaded with careful timing
- **Resource Management:** Properly cleans up GPIO on exit
- **PWM Frequency:** 1000 Hz is above human flicker perception
- **Color Math:** HSV color space provides intuitive color cycling

## 📜 License

This script is free to use, modify, and share. Have fun!

## 🤝 Contributing

Feel free to add more patterns, improve the code, or create variants!

## ⚠️ Safety Notes

- Use appropriate current-limiting resistors (220-330Ω)
- Don't exceed 16mA per GPIO pin
- Common cathode LEDs work with this code as-is
- Be careful with wiring - double check before powering on

---

**Enjoy your colorful creation! 🎨✨**

Made with 💙 for the Raspberry Pi community
