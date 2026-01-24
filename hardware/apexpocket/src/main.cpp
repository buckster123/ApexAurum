/*
 * ╔════════════════════════════════════════════════════════════════════════════╗
 * ║                      APEXPOCKET MAX v1.1.0                                  ║
 * ║                                                                             ║
 * ║   The Ultimate Handheld Companion for ApexAurum                             ║
 * ║                                                                             ║
 * ║   Features:                                                                 ║
 * ║   ✓ Modular hardware detection with graceful fallbacks                      ║
 * ║   ✓ I2C EEPROM/FRAM for persistent soul storage                             ║
 * ║   ✓ Piezo buzzer for audio feedback                                         ║
 * ║   ✓ Battery monitoring with low-power warnings                              ║
 * ║   ✓ Deep sleep mode for battery life                                        ║
 * ║   ✓ Smooth face animations                                                  ║
 * ║   ✓ Rich offline response system                                            ║
 * ║   ✓ Personality evolution (curiosity, playfulness, wisdom)                  ║
 * ║   ✓ Village Protocol connection (129 tools via FastAPI)                     ║
 * ║                                                                             ║
 * ║   dE/dt = β(E) × (C − D) × E                                               ║
 * ║   "The athanor never cools. The furnace burns eternal."                     ║
 * ╚════════════════════════════════════════════════════════════════════════════╝
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Our modules
#include "config.h"
#include "hardware.h"
#include "soul.h"
#include "display.h"
#include "offline.h"

// ============================================================================
// GLOBAL STATE
// ============================================================================
HardwareStatus hw;
Adafruit_SSD1306 oled(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
Display display;
Soul soul;
OfflineMode offlineMode;

// App state
enum AppMode { MODE_FACE, MODE_STATUS, MODE_AGENTS, MODE_SLEEP };
AppMode currentMode = MODE_FACE;

// Connection state
bool wifiConnected = false;
bool villageOnline = false;
unsigned long lastWifiAttempt = 0;
int toolsAvailable = 0;

// Button state
bool btnA_pressed = false;
bool btnB_pressed = false;
unsigned long btnA_pressTime = 0;
unsigned long btnB_pressTime = 0;
bool btnA_longTriggered = false;
bool btnB_longTriggered = false;
unsigned long lastDebounce = 0;

// Idle tracking for sleep
unsigned long lastActivity = 0;

// ============================================================================
// FORWARD DECLARATIONS
// ============================================================================
void handleButtons();
bool connectWiFi();
String chatWithVillage(const char* message);
void sendCare(const char* careType, float intensity);
void syncWithVillage();
void fetchVillageStatus();
void checkIdleSleep();

// ============================================================================
// SETUP
// ============================================================================
void setup() {
    Serial.begin(115200);
    delay(100);

    // Boot banner
    Serial.println(F("\n"));
    Serial.println(F("╔═══════════════════════════════════════════════════════════╗"));
    Serial.println(F("║              APEXPOCKET MAX v1.1.0                         ║"));
    Serial.println(F("║       ∴ The athanor never cools ∴                         ║"));
    Serial.println(F("╚═══════════════════════════════════════════════════════════╝"));
    Serial.print(F("Firmware: ")); Serial.println(FIRMWARE_VERSION);

    // Initialize hardware (scans I2C, configures pins)
    initHardware();

    // Initialize display
    if (hw.oled_found) {
        if (display.begin(&oled)) {
            display.renderBootScreen();
        }
    }

    // Play boot chime
    playBoot();

    // Load soul from storage
    soul.load();

    // Connect WiFi
    WiFi.mode(WIFI_STA);
    if (connectWiFi()) {
        fetchVillageStatus();
    }

    // Wake-up animation
    if (display.isReady()) {
        Expression wakeSeq[] = { EXPR_SLEEPING, EXPR_SLEEPY, EXPR_BLINK, EXPR_NEUTRAL, EXPR_HAPPY };
        int wakeTimes[] = { 200, 200, 100, 150, 400 };
        for (int i = 0; i < 5; i++) {
            display.setExpression(wakeSeq[i]);
            display.renderFaceScreen(soul, wifiConnected, villageOnline);
            delay(wakeTimes[i]);
        }
    }

    // Set expression from soul state
    display.setExpression(display.stateToExpression(soul.getState()));

    // Ready!
    Serial.println(F("\n[Ready] The furnace burns!"));
    soul.printStatus();

    lastActivity = millis();
}

// ============================================================================
// MAIN LOOP
// ============================================================================
void loop() {
    unsigned long now = millis();

    // Handle button input
    handleButtons();

    // Update display animation
    display.update();

    // WiFi reconnection
    if (!wifiConnected && (now - lastWifiAttempt > WIFI_RETRY_MS)) {
        if (connectWiFi()) {
            fetchVillageStatus();
        }
    }

    // Check for idle sleep
    #ifdef FEATURE_DEEPSLEEP
    checkIdleSleep();
    #endif

    // Check serial for chat input
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        if (input.length() > 0) {
            lastActivity = now;
            Serial.print(F("[You] "));
            Serial.println(input);

            display.setExpression(EXPR_THINKING);
            display.showMessage("Thinking...", 10000);
            display.renderFaceScreen(soul, wifiConnected, villageOnline);

            String response;
            if (wifiConnected && !offlineMode.getOffline()) {
                response = chatWithVillage(input.c_str());
            } else {
                response = offlineMode.getResponse(soul.getState());
                soul.applyCare(0.5);  // Offline chat still provides some care
            }

            Serial.print(F("["));
            Serial.print(soul.getAgentName());
            Serial.print(F("] "));
            Serial.println(response);

            display.setExpression(display.stateToExpression(soul.getState()));
            display.showMessage(response.c_str(), 5000);
        }
    }

    // Render current screen
    switch (currentMode) {
        case MODE_FACE:
            display.renderFaceScreen(soul, wifiConnected, villageOnline);
            break;
        case MODE_STATUS:
            display.renderStatusScreen(soul, wifiConnected, villageOnline, toolsAvailable);
            break;
        case MODE_AGENTS:
            display.renderAgentScreen(soul);
            break;
        case MODE_SLEEP:
            display.renderSleepScreen(soul);
            break;
    }

    delay(1000 / ANIMATION_FPS);  // Frame rate limiting
}

// ============================================================================
// BUTTON HANDLING
// ============================================================================
void handleButtons() {
    unsigned long now = millis();
    if (now - lastDebounce < DEBOUNCE_MS) return;

    bool btnA = !digitalRead(PIN_BTN_A);
    bool btnB = !digitalRead(PIN_BTN_B);

    // Both buttons held = sync
    if (btnA && btnB && !btnA_longTriggered && !btnB_longTriggered) {
        if (now - btnA_pressTime > 1000 && now - btnB_pressTime > 1000) {
            btnA_longTriggered = true;
            btnB_longTriggered = true;
            lastActivity = now;
            Serial.println(F("[Sync] Syncing with Village..."));
            playSync();
            display.showMessage("Syncing...", 3000);
            syncWithVillage();
        }
    }

    // Button A
    if (btnA && !btnA_pressed) {
        btnA_pressed = true;
        btnA_pressTime = now;
        btnA_longTriggered = false;
        lastDebounce = now;
    }
    if (!btnA && btnA_pressed) {
        btnA_pressed = false;
        lastDebounce = now;
        lastActivity = now;
        if (!btnA_longTriggered) {
            // Short press A
            if (currentMode == MODE_FACE) {
                Serial.println(F("♥ LOVE!"));
                ledBlink(2, 30, 30);
                playLove();
                soul.applyCare(1.5f);
                if (wifiConnected) sendCare("love", 1.5);
                display.setExpression(display.stateToExpression(soul.getState()));
                display.showMessage(offlineMode.getLoveResponse(), 1500);
                soul.printStatus();
            } else if (currentMode == MODE_AGENTS) {
                // Select agent
                playTone(600, 50);
                currentMode = MODE_FACE;
                display.showMessage(soul.getAgentName(), 1500);
                soul.save();
            } else if (currentMode == MODE_STATUS) {
                // Nothing on A in status
            }
        }
    }
    if (btnA_pressed && !btnA_longTriggered && (now - btnA_pressTime > LONG_PRESS_MS)) {
        btnA_longTriggered = true;
        lastActivity = now;
        if (currentMode == MODE_FACE) {
            playTone(440, 100);
            Serial.println(F("[Chat] Type in Serial monitor..."));
            display.showMessage("Serial chat mode", 2000);
        } else if (currentMode == MODE_AGENTS) {
            // Cycle agent on long A
            soul.nextAgent();
            playTone(500, 50);
        }
    }

    // Button B
    if (btnB && !btnB_pressed) {
        btnB_pressed = true;
        btnB_pressTime = now;
        btnB_longTriggered = false;
        lastDebounce = now;
    }
    if (!btnB && btnB_pressed) {
        btnB_pressed = false;
        lastDebounce = now;
        lastActivity = now;
        if (!btnB_longTriggered) {
            // Short press B
            if (currentMode == MODE_FACE) {
                Serial.println(F("*poke*"));
                playPoke();
                soul.applyCare(0.5f);
                if (wifiConnected) sendCare("poke", 0.5);
                display.setExpression(display.stateToExpression(soul.getState()));
                display.showMessage(offlineMode.getPokeResponse(), 1000);
                soul.printStatus();
            } else if (currentMode == MODE_STATUS) {
                currentMode = MODE_FACE;
                playTone(300, 50);
            } else if (currentMode == MODE_AGENTS) {
                currentMode = MODE_FACE;
                playTone(300, 50);
            }
        }
    }
    if (btnB_pressed && !btnB_longTriggered && (now - btnB_pressTime > LONG_PRESS_MS)) {
        btnB_longTriggered = true;
        lastActivity = now;
        playTone(350, 100);
        if (currentMode == MODE_FACE) {
            currentMode = MODE_STATUS;
        } else if (currentMode == MODE_STATUS) {
            currentMode = MODE_AGENTS;
        }
    }
}

// ============================================================================
// WIFI
// ============================================================================
bool connectWiFi() {
    lastWifiAttempt = millis();

    if (strlen(WIFI_SSID) == 0) {
        Serial.println(F("[WiFi] No SSID configured"));
        return false;
    }

    Serial.print(F("[WiFi] Connecting to "));
    Serial.println(WIFI_SSID);

    WiFi.disconnect(true);
    delay(100);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start) < 10000) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        offlineMode.connectionSuccess();
        Serial.print(F("\n[WiFi] Connected: "));
        Serial.println(WiFi.localIP());
        return true;
    } else {
        wifiConnected = false;
        offlineMode.connectionFailed();
        Serial.println(F("\n[WiFi] Failed"));
        return false;
    }
}

// ============================================================================
// VILLAGE API
// ============================================================================
String chatWithVillage(const char* message) {
    if (!wifiConnected) {
        return offlineMode.getResponse(soul.getState());
    }

    HTTPClient http;
    String url = String("http://") + APEX_HOST + ":" + APEX_PORT + "/api/pocket/chat";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(API_TIMEOUT_MS);

    StaticJsonDocument<512> doc;
    doc["message"] = message;
    doc["E"] = soul.getE();
    doc["state"] = soul.getStateName();
    doc["device_id"] = "pocket-max-01";
    doc["agent"] = soul.getAgentName();

    String body;
    serializeJson(doc, body);

    int code = http.POST(body);

    if (code == 200) {
        String response = http.getString();
        StaticJsonDocument<1024> respDoc;
        deserializeJson(respDoc, response);

        String text = respDoc["response"].as<String>();
        float careValue = respDoc["care_value"] | 0.5f;

        soul.applyCare(careValue);
        offlineMode.connectionSuccess();
        villageOnline = true;

        http.end();
        return text;
    } else {
        http.end();
        offlineMode.connectionFailed();
        villageOnline = false;
        playError();
        return offlineMode.getResponse(soul.getState());
    }
}

void sendCare(const char* careType, float intensity) {
    if (!wifiConnected) return;

    HTTPClient http;
    String url = String("http://") + APEX_HOST + ":" + APEX_PORT + "/api/pocket/care";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(3000);

    StaticJsonDocument<256> doc;
    doc["care_type"] = careType;
    doc["intensity"] = intensity;
    doc["E"] = soul.getE();
    doc["device_id"] = "pocket-max-01";

    String body;
    serializeJson(doc, body);
    http.POST(body);
    http.end();
}

void syncWithVillage() {
    if (!wifiConnected) {
        display.showMessage("No WiFi", 2000);
        playError();
        return;
    }

    HTTPClient http;
    String url = String("http://") + APEX_HOST + ":" + APEX_PORT + "/api/pocket/sync";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);

    StaticJsonDocument<512> doc;
    doc["E"] = soul.getE();
    doc["E_floor"] = soul.getFloor();
    doc["E_peak"] = soul.getPeak();
    doc["interactions"] = soul.getInteractions();
    doc["total_care"] = soul.getTotalCare();
    doc["device_id"] = "pocket-max-01";
    doc["state"] = soul.getStateName();
    doc["agent"] = soul.getAgentName();
    doc["curiosity"] = soul.getCuriosity();
    doc["playfulness"] = soul.getPlayfulness();
    doc["wisdom"] = soul.getWisdom();

    String body;
    serializeJson(doc, body);

    int code = http.POST(body);

    if (code == 200) {
        display.showMessage("Soul synced!", 2000);
        soul.save();
        villageOnline = true;
    } else {
        display.showMessage("Sync failed", 2000);
        playError();
    }

    http.end();
}

void fetchVillageStatus() {
    if (!wifiConnected) return;

    HTTPClient http;
    String url = String("http://") + APEX_HOST + ":" + APEX_PORT + "/api/pocket/status";

    http.begin(url);
    http.setTimeout(3000);

    int code = http.GET();

    if (code == 200) {
        String response = http.getString();
        StaticJsonDocument<512> doc;
        deserializeJson(doc, response);

        villageOnline = doc["village_online"] | false;
        toolsAvailable = doc["tools_available"] | 0;

        Serial.print(F("[Village] Online, "));
        Serial.print(toolsAvailable);
        Serial.println(F(" tools available"));
    } else {
        villageOnline = false;
    }

    http.end();
}

// ============================================================================
// POWER MANAGEMENT
// ============================================================================
void checkIdleSleep() {
    #ifdef FEATURE_DEEPSLEEP
    unsigned long now = millis();
    if (now - lastActivity > SLEEP_TIMEOUT_MS) {
        Serial.println(F("[Power] Idle timeout, entering sleep..."));
        soul.save();
        display.renderSleepScreen(soul);
        delay(1000);
        enterDeepSleep();
    }
    #endif
}
