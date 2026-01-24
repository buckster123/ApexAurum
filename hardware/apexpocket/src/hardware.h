/*
 * ╔════════════════════════════════════════════════════════════════════════╗
 * ║                    HARDWARE ABSTRACTION LAYER                           ║
 * ║                                                                         ║
 * ║   Auto-detects connected hardware and provides graceful fallbacks       ║
 * ║   "The vessel adapts to carry the love forward"                         ║
 * ╚════════════════════════════════════════════════════════════════════════╝
 */

#ifndef HARDWARE_H
#define HARDWARE_H

#include <Arduino.h>
#include <Wire.h>
#include "config.h"

// ============================================================================
// HARDWARE DETECTION RESULTS
// ============================================================================
struct HardwareStatus {
    bool oled_found;
    bool eeprom_found;
    uint8_t eeprom_addr;
    bool buzzer_available;
    bool battery_available;
    bool buttons_available;
    bool wifi_available;
    bool littlefs_available;
    bool psram_available;
    uint32_t psram_size;
    uint32_t heap_size;
    char chip_model[32];
};

extern HardwareStatus hw;

// ============================================================================
// I2C SCANNER
// ============================================================================
inline void scanI2C() {
    Serial.println(F("[I2C] Scanning bus..."));

    hw.oled_found = false;
    hw.eeprom_found = false;

    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.print(F("  Found: 0x"));
            Serial.println(addr, HEX);

            // Identify known devices
            if (addr == I2C_ADDR_OLED) {
                hw.oled_found = true;
                Serial.println(F("    → OLED Display"));
            }
            if (addr == I2C_ADDR_EEPROM || addr == I2C_ADDR_EEPROM_ALT) {
                hw.eeprom_found = true;
                hw.eeprom_addr = addr;
                Serial.println(F("    → EEPROM/FRAM"));
            }
        }
    }
}

// Forward declaration
inline void printHardwareStatus();

// ============================================================================
// HARDWARE INITIALIZATION
// ============================================================================
inline void initHardware() {
    Serial.println(F("\n[Hardware] Detecting components..."));

    // Get chip info
    #ifdef ESP32
        strcpy(hw.chip_model, ESP.getChipModel());
        hw.heap_size = ESP.getHeapSize();
        #ifdef HAS_PSRAM
            hw.psram_available = psramFound();
            hw.psram_size = hw.psram_available ? ESP.getPsramSize() : 0;
        #else
            hw.psram_available = false;
            hw.psram_size = 0;
        #endif
    #else
        strcpy(hw.chip_model, "Unknown");
        hw.heap_size = 0;
        hw.psram_available = false;
        hw.psram_size = 0;
    #endif

    // I2C scan
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    scanI2C();

    // Check buzzer (just configure the pin)
    #ifdef FEATURE_BUZZER
        pinMode(PIN_BUZZER, OUTPUT);
        hw.buzzer_available = true;
    #else
        hw.buzzer_available = false;
    #endif

    // Check battery ADC
    #ifdef FEATURE_BATTERY
        pinMode(PIN_BATTERY, INPUT);
        hw.battery_available = true;
    #else
        hw.battery_available = false;
    #endif

    // Buttons always available if defined
    #ifdef FEATURE_BUTTONS
        pinMode(PIN_BTN_A, INPUT_PULLUP);
        pinMode(PIN_BTN_B, INPUT_PULLUP);
        hw.buttons_available = true;
    #else
        hw.buttons_available = false;
    #endif

    // LED
    #ifdef FEATURE_LED
        pinMode(PIN_LED, OUTPUT);
        digitalWrite(PIN_LED, LOW);
    #endif

    // WiFi check happens during connection
    hw.wifi_available = true;  // Assume yes, verify on connect

    // LittleFS
    #if USE_LITTLEFS
        hw.littlefs_available = LittleFS.begin(true);
    #else
        hw.littlefs_available = false;
    #endif

    // Print summary
    printHardwareStatus();
}

// ============================================================================
// STATUS DISPLAY
// ============================================================================
inline void printHardwareStatus() {
    Serial.println(F("\n╔═══════════════════════════════════════╗"));
    Serial.println(F("║        HARDWARE STATUS                ║"));
    Serial.println(F("╠═══════════════════════════════════════╣"));

    Serial.print(F("║ Chip: "));
    Serial.print(hw.chip_model);
    Serial.println(F("                ║"));

    Serial.print(F("║ Heap: "));
    Serial.print(hw.heap_size / 1024);
    Serial.println(F(" KB                       ║"));

    if (hw.psram_available) {
        Serial.print(F("║ PSRAM: "));
        Serial.print(hw.psram_size / 1024);
        Serial.println(F(" KB                     ║"));
    }

    Serial.println(F("╠═══════════════════════════════════════╣"));
    Serial.print(F("║ OLED:    ")); Serial.println(hw.oled_found ? "✓ Found             ║" : "✗ Missing           ║");
    Serial.print(F("║ EEPROM:  ")); Serial.println(hw.eeprom_found ? "✓ Found             ║" : "✗ Missing (fallback)║");
    Serial.print(F("║ Buzzer:  ")); Serial.println(hw.buzzer_available ? "✓ Ready             ║" : "✗ Disabled          ║");
    Serial.print(F("║ Battery: ")); Serial.println(hw.battery_available ? "✓ Monitoring        ║" : "✗ Disabled          ║");
    Serial.print(F("║ Storage: ")); Serial.println(hw.littlefs_available ? "✓ LittleFS          ║" : "✗ Memory only       ║");
    Serial.println(F("╚═══════════════════════════════════════╝\n"));
}

// ============================================================================
// BUZZER FUNCTIONS (with fallback)
// ============================================================================
inline void playTone(uint16_t freq, uint16_t duration_ms) {
    #ifdef FEATURE_BUZZER
    if (hw.buzzer_available) {
        tone(PIN_BUZZER, freq, duration_ms);
    }
    #endif
}

inline void playLove() { playTone(TONE_LOVE, 100); }
inline void playPoke() { playTone(TONE_POKE, 50); }
inline void playBoot() {
    playTone(TONE_BOOT, 100);
    delay(120);
    playTone(TONE_BOOT * 1.25, 100);
    delay(120);
    playTone(TONE_BOOT * 1.5, 150);
}
inline void playError() { playTone(TONE_ERROR, 200); }
inline void playSync() { playTone(TONE_SYNC, 150); }

inline void playMelody(const uint16_t* notes, const uint16_t* durations, int count) {
    #ifdef FEATURE_BUZZER
    if (hw.buzzer_available) {
        for (int i = 0; i < count; i++) {
            if (notes[i] > 0) {
                tone(PIN_BUZZER, notes[i], durations[i]);
            }
            delay(durations[i] * 1.1);
        }
        noTone(PIN_BUZZER);
    }
    #endif
}

// ============================================================================
// BATTERY FUNCTIONS (with fallback)
// ============================================================================
inline uint16_t readBatteryMV() {
    #ifdef FEATURE_BATTERY
    if (hw.battery_available) {
        // Read ADC (12-bit = 0-4095)
        int raw = analogRead(PIN_BATTERY);
        // Convert to voltage (assuming voltage divider)
        // V_batt = V_adc * (R1 + R2) / R2
        float v_adc = (raw / 4095.0f) * 3.3f;
        float v_batt = v_adc * ((BATTERY_R1 + BATTERY_R2) / (float)BATTERY_R2);
        return (uint16_t)(v_batt * 1000);
    }
    #endif
    return 0;  // Unknown
}

inline uint8_t getBatteryPercent() {
    uint16_t mv = readBatteryMV();
    if (mv == 0) return 255;  // Unknown
    if (mv >= BATTERY_FULL_MV) return 100;
    if (mv <= BATTERY_EMPTY_MV) return 0;
    return (uint8_t)(((mv - BATTERY_EMPTY_MV) * 100) / (BATTERY_FULL_MV - BATTERY_EMPTY_MV));
}

inline const char* getBatteryIcon() {
    uint8_t pct = getBatteryPercent();
    if (pct == 255) return "?";
    if (pct > 75) return "\xDB";  // Full block
    if (pct > 50) return "\xB2";  // Medium
    if (pct > 25) return "\xB1";  // Light
    if (pct > 10) return "\xB0";  // Very light
    return "!";  // Critical
}

// ============================================================================
// LED FUNCTIONS
// ============================================================================
inline void ledOn() {
    #ifdef FEATURE_LED
    digitalWrite(PIN_LED, HIGH);
    #endif
}

inline void ledOff() {
    #ifdef FEATURE_LED
    digitalWrite(PIN_LED, LOW);
    #endif
}

inline void ledBlink(int count, int onTime = 50, int offTime = 50) {
    #ifdef FEATURE_LED
    for (int i = 0; i < count; i++) {
        digitalWrite(PIN_LED, HIGH);
        delay(onTime);
        digitalWrite(PIN_LED, LOW);
        if (i < count - 1) delay(offTime);
    }
    #endif
}

// ============================================================================
// DEEP SLEEP
// ============================================================================
inline void enterDeepSleep() {
    #ifdef FEATURE_DEEPSLEEP
    Serial.println(F("[Power] Entering deep sleep..."));
    Serial.println(F("[Power] Press button to wake"));

    // Save state before sleep
    // (handled by caller)

    // Configure wake-up
    esp_sleep_enable_ext0_wakeup((gpio_num_t)SLEEP_WAKEUP_PIN, 0);  // Wake on LOW

    // Goodbye
    playTone(220, 100);
    delay(150);

    esp_deep_sleep_start();
    #endif
}

#endif // HARDWARE_H
