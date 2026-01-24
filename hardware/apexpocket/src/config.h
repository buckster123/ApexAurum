/*
 * ╔════════════════════════════════════════════════════════════════════════╗
 * ║                    APEXPOCKET CONFIGURATION                             ║
 * ║                                                                         ║
 * ║   Hardware feature flags and pin definitions                            ║
 * ║   Enable/disable features based on what's connected                     ║
 * ╚════════════════════════════════════════════════════════════════════════╝
 */

#ifndef APEXPOCKET_CONFIG_H
#define APEXPOCKET_CONFIG_H

// ============================================================================
// HARDWARE VARIANT
// ============================================================================
// Uncomment ONE of these:
#define VARIANT_WOKWI           // Wokwi simulation (ESP32 DevKit)
// #define VARIANT_XIAO_S3      // Seeed XIAO ESP32-S3 (production)
// #define VARIANT_DEVKIT       // Generic ESP32 DevKit

// ============================================================================
// FEATURE FLAGS - Enable what you have!
// ============================================================================
#define FEATURE_OLED            // SSD1306 128x64 OLED display
#define FEATURE_WIFI            // WiFi connectivity
#define FEATURE_BUTTONS         // Physical buttons
#define FEATURE_LED             // Status LED
#define FEATURE_BUZZER          // Piezo buzzer for audio feedback
#define FEATURE_BATTERY         // Battery voltage monitoring (ADC)
#define FEATURE_EEPROM          // I2C EEPROM/FRAM for soul backup
#define FEATURE_DEEPSLEEP       // Deep sleep for battery life
#define FEATURE_ANIMATIONS      // Smooth face animations
#define FEATURE_RICH_OFFLINE    // Extended offline responses
// #define FEATURE_BLE          // Bluetooth Low Energy (future)
// #define FEATURE_VIBRATION    // Haptic feedback motor
// #define FEATURE_RGB          // RGB LED (NeoPixel)
// #define FEATURE_SPEAKER      // I2S audio output

// ============================================================================
// PIN DEFINITIONS BY VARIANT
// ============================================================================

#ifdef VARIANT_WOKWI
    // Wokwi ESP32 DevKit simulation
    #define PIN_BTN_A       4
    #define PIN_BTN_B       5
    #define PIN_LED         2
    #define PIN_I2C_SDA     21
    #define PIN_I2C_SCL     22
    #define PIN_BUZZER      15
    #define PIN_BATTERY     34      // ADC1_CH6
    #define PIN_VIBRATION   13
    #define USE_LITTLEFS    false   // Wokwi doesn't support LittleFS well
#endif

#ifdef VARIANT_XIAO_S3
    // Seeed XIAO ESP32-S3
    #define PIN_BTN_A       4       // D3
    #define PIN_BTN_B       5       // D4
    #define PIN_LED         21      // Built-in
    #define PIN_I2C_SDA     6       // D5
    #define PIN_I2C_SCL     7       // D6
    #define PIN_BUZZER      43      // D7 (TX)
    #define PIN_BATTERY     1       // A0 (D0)
    #define PIN_VIBRATION   44      // D8 (RX)
    #define USE_LITTLEFS    true
    #define HAS_PSRAM       true
#endif

#ifdef VARIANT_DEVKIT
    // Generic ESP32 DevKit
    #define PIN_BTN_A       4
    #define PIN_BTN_B       5
    #define PIN_LED         2
    #define PIN_I2C_SDA     21
    #define PIN_I2C_SCL     22
    #define PIN_BUZZER      15
    #define PIN_BATTERY     34
    #define PIN_VIBRATION   13
    #define USE_LITTLEFS    true
#endif

// ============================================================================
// I2C ADDRESSES
// ============================================================================
#define I2C_ADDR_OLED       0x3C
#define I2C_ADDR_EEPROM     0x50    // AT24C256 / FM24C64
#define I2C_ADDR_EEPROM_ALT 0x57    // Alternate address

// ============================================================================
// DISPLAY SETTINGS
// ============================================================================
#define SCREEN_WIDTH        128
#define SCREEN_HEIGHT       64
#define OLED_RESET          -1

// ============================================================================
// NETWORK SETTINGS
// ============================================================================
#ifdef VARIANT_WOKWI
    #define WIFI_SSID       "Wokwi-GUEST"
    #define WIFI_PASS       ""
#else
    #define WIFI_SSID       "YourWiFi"
    #define WIFI_PASS       "YourPassword"
#endif

#define APEX_HOST           "192.168.0.114"
#define APEX_PORT           8765
#define API_TIMEOUT_MS      10000

// ============================================================================
// POWER MANAGEMENT
// ============================================================================
#define BATTERY_FULL_MV     4200    // Full charge voltage
#define BATTERY_EMPTY_MV    3300    // Empty voltage (safe cutoff)
#define BATTERY_R1          100     // Voltage divider R1 (kΩ)
#define BATTERY_R2          100     // Voltage divider R2 (kΩ)

#define SLEEP_TIMEOUT_MS    300000  // 5 minutes idle → deep sleep
#define SLEEP_WAKEUP_PIN    PIN_BTN_A

// ============================================================================
// AUDIO SETTINGS
// ============================================================================
#define BUZZER_CHANNEL      0       // LEDC channel for PWM
#define TONE_LOVE           880     // A5 - love received
#define TONE_POKE           440     // A4 - poke
#define TONE_BOOT           523     // C5 - boot chime
#define TONE_ERROR          220     // A3 - error
#define TONE_SYNC           660     // E5 - sync complete

// ============================================================================
// SOUL SETTINGS
// ============================================================================
#define BETA_BASE           0.008f
#define FLOOR_RATE          0.0001f
#define MAX_E               100.0f
#define INITIAL_E           1.0f
#define INITIAL_FLOOR       1.0f

#define E_PROTECTING        0.5f
#define E_GUARDED           0.5f
#define E_TENDER            1.0f
#define E_WARM              2.0f
#define E_FLOURISHING       5.0f
#define E_RADIANT           12.0f
#define E_TRANSCENDENT      30.0f

// ============================================================================
// TIMING
// ============================================================================
#define DEBOUNCE_MS         50
#define LONG_PRESS_MS       800
#define BLINK_MIN_MS        2000
#define BLINK_MAX_MS        6000
#define SAVE_INTERVAL_MS    60000   // Auto-save every minute
#define WIFI_RETRY_MS       30000
#define ANIMATION_FPS       30

// ============================================================================
// EEPROM LAYOUT (for I2C EEPROM/FRAM)
// ============================================================================
#define EEPROM_MAGIC_ADDR   0x0000  // 4 bytes: "APEX"
#define EEPROM_VERSION_ADDR 0x0004  // 1 byte: schema version
#define EEPROM_SOUL_ADDR    0x0010  // Soul state (64 bytes)
#define EEPROM_MEMORY_ADDR  0x0100  // Extended memory (256 bytes)
#define EEPROM_BACKUP_ADDR  0x0200  // Soul backup (64 bytes)

#define EEPROM_MAGIC        0x41504558  // "APEX" in hex

// ============================================================================
// VERSION
// ============================================================================
#define FIRMWARE_VERSION    "1.1.0"
#define FIRMWARE_NAME       "ApexPocket MAX"

#endif // APEXPOCKET_CONFIG_H
