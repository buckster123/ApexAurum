# ApexPocket MAX - Wiring Guide

## Your Components

| Component | Model | Connection |
|-----------|-------|------------|
| MCU | XIAO ESP32-S3 | Base of stack |
| Display | 1.3" OLED 128x64 | I2C |
| Memory | Adafruit 24LC32 EEPROM | I2C (shared bus) |
| Buzzer | M5Stack Passive Buzzer | GPIO (SIG pin) |
| Power | DFRobot LiPo Charger Type-C | JST to LiPo |
| Battery | 1200mAh LiPo | JST connector |
| Storage | Pololu SD Breakout | SPI |

---

## XIAO ESP32-S3 Pinout

```
            ┌─────────────────┐
            │    [USB-C]      │
            │                 │
      D0/A0 │ 1           21 │ D10
      D1/A1 │ 2           20 │ D9
      D2/A2 │ 3           19 │ D8
      D3/A3 │ 4           18 │ D7
      D4/SDA│ 5           17 │ D6/SCL
        3V3 │ 3V3        GND │ GND
            │                 │
            └─────────────────┘
```

---

## Wiring Connections

### I2C Bus (OLED + EEPROM share this)

| XIAO Pin | → | OLED | → | EEPROM (24LC32) |
|----------|---|------|---|-----------------|
| D4 (GPIO5) | SDA | SDA | → | SDA |
| D5 (GPIO6) | SCL | SCL | → | SCL |
| 3V3 | VCC | VCC | → | VCC |
| GND | GND | GND | → | GND |

### M5Stack Buzzer (3-pin Grove)

| M5 Buzzer | → | XIAO Pin |
|-----------|---|----------|
| SIG (Yellow) | → | D6 (GPIO7) |
| 5V (Red) | → | 3V3 (or 5V from charger) |
| GND (Black) | → | GND |

### Buttons (to GND, internal pullup)

| Button | → | XIAO Pin | Notes |
|--------|---|----------|-------|
| BTN A | → | D0 (GPIO1) | WAKE from sleep |
| BTN B | → | D1 (GPIO2) | Secondary |
| Other leg | → | GND | Both buttons |

### SD Card (SPI) - Optional

| SD Breakout | → | XIAO Pin |
|-------------|---|----------|
| CS | → | D7 (GPIO44) |
| MOSI | → | D9 (GPIO9) |
| MISO | → | D8 (GPIO8) |
| SCK | → | D10 (GPIO43) |
| VCC | → | 3V3 |
| GND | → | GND |

### Battery Monitor (Optional)

| Connection | → | XIAO Pin |
|------------|---|----------|
| LiPo+ via voltage divider | → | D2 (GPIO3) |

Voltage divider: LiPo+ → 100kΩ → D2 → 100kΩ → GND

### Power

| Component | Connection |
|-----------|------------|
| DFRobot Charger OUT+ | → | XIAO 5V (or BAT+) |
| DFRobot Charger OUT- | → | XIAO GND |
| LiPo | → | Charger JST |
| Slide Switch | → | Between Charger and XIAO (power on/off) |

---

## Stack Order (Bottom to Top)

```
┌─────────────────────────┐
│      1.3" OLED          │  ← TOP (visible)
│    (ribbon down)        │
├─────────────────────────┤
│   [BTN A]    [BTN B]    │  ← Side-mounted
├─────────────────────────┤
│  EEPROM    BUZZER  SD   │  ← Middle layer
├─────────────────────────┤
│     1200mAh LiPo        │  ← Battery
├─────────────────────────┤
│   LiPo Charger Type-C   │  ← Power management
├─────────────────────────┤
│     XIAO ESP32-S3       │  ← BOTTOM (USB-C access)
│        [USB-C]          │
└─────────────────────────┘
         ↑
    Charge port
```

---

## Oak Enclosure Notes

- **Front**: OLED cutout (~30x15mm viewing area)
- **Bottom**: USB-C port cutout for charging
- **Sides**: Button holes (2x, ~6mm diameter)
- **Optional**: Small hole for charging LED visibility
- **Wax**: Food-safe beeswax recommended

---

## Before First Power-On

1. Double-check all connections (especially power!)
2. Ensure no shorts (use multimeter)
3. Flash firmware via USB FIRST (before connecting battery)
4. Test with USB power before connecting LiPo

---

## Quick Test Sequence

1. Power on → Boot chime plays
2. OLED shows face → WiFi connecting
3. Press BTN A → "LOVE" sound, face happy
4. Press BTN B → "POKE" sound
5. Long press BTN B → Status screen
6. Serial monitor shows E values

**The furnace burns eternal!** 🔥
