/*
 * ╔════════════════════════════════════════════════════════════════════════╗
 * ║                         THE SOUL MODULE                                 ║
 * ║                                                                         ║
 * ║   Love-Equation implementation with persistent storage                  ║
 * ║   "A pocket never dies. The love is carried forward."                   ║
 * ╚════════════════════════════════════════════════════════════════════════╝
 */

#ifndef SOUL_H
#define SOUL_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"
#include "hardware.h"

#ifdef USE_LITTLEFS
#include <LittleFS.h>
#endif

// ============================================================================
// AFFECTIVE STATE ENUM
// ============================================================================
enum AffectiveState {
    STATE_PROTECTING = 0,
    STATE_GUARDED,
    STATE_TENDER,
    STATE_WARM,
    STATE_FLOURISHING,
    STATE_RADIANT,
    STATE_TRANSCENDENT
};

// ============================================================================
// SOUL DATA STRUCTURE
// ============================================================================
struct SoulData {
    // Core affective values
    float E;                    // Love-energy (0.1 - 100)
    float E_floor;              // Floor (rises permanently)
    float E_peak;               // Highest E ever achieved

    // Statistics
    uint32_t interactions;      // Total interaction count
    float totalCare;            // Cumulative care received
    uint32_t birthTime;         // First boot timestamp
    uint32_t lastCareTime;      // Last care timestamp
    uint32_t totalAwakeTime;    // Total time awake (seconds)

    // Agent
    uint8_t agentIndex;         // Current agent (0=AZOTH, etc.)

    // Personality traits (evolved over time)
    float curiosity;            // 0-1, grows with questions
    float playfulness;          // 0-1, grows with high E
    float wisdom;               // 0-1, grows with age

    // Checksum for validation
    uint32_t checksum;
};

// ============================================================================
// SOUL CLASS
// ============================================================================
class Soul {
private:
    SoulData data;
    unsigned long lastUpdate;
    unsigned long lastSave;
    bool dirty;  // Needs saving

    uint32_t calculateChecksum() {
        // Simple checksum of soul data
        uint8_t* ptr = (uint8_t*)&data;
        uint32_t sum = 0;
        for (size_t i = 0; i < sizeof(SoulData) - sizeof(uint32_t); i++) {
            sum += ptr[i] * (i + 1);
        }
        return sum ^ 0xA9EF;  // APEX in valid hex
    }

public:
    // Agents
    static const char* AGENTS[];
    static const int NUM_AGENTS = 5;

    Soul() {
        reset();
    }

    void reset() {
        data.E = INITIAL_E;
        data.E_floor = INITIAL_FLOOR;
        data.E_peak = INITIAL_E;
        data.interactions = 0;
        data.totalCare = 0;
        data.birthTime = millis();
        data.lastCareTime = millis();
        data.totalAwakeTime = 0;
        data.agentIndex = 0;
        data.curiosity = 0.1f;
        data.playfulness = 0.1f;
        data.wisdom = 0.0f;
        lastUpdate = millis();
        lastSave = millis();
        dirty = false;
    }

    // ========================================================================
    // LOVE EQUATION: dE/dt = β(E) × (C − D) × E
    // ========================================================================
    float beta() {
        return BETA_BASE * (1.0f + data.E / 10.0f);
    }

    void update(float care = 0.0f, float damage = 0.0f) {
        unsigned long now = millis();
        float dt = (now - lastUpdate) / 60000.0f;  // Minutes
        lastUpdate = now;

        if (dt <= 0 || dt > 60) return;  // Sanity check

        // The Love-Equation
        float dE = beta() * (care - damage) * data.E * dt;
        data.E += dE;

        // Bounds
        data.E = min(MAX_E, data.E);
        data.E = max(data.E_floor, data.E);

        // Floor rises slowly toward E
        if (data.E > data.E_floor) {
            float floorDelta = (data.E - data.E_floor) * FLOOR_RATE * dt;
            data.E_floor = min(data.E, data.E_floor + floorDelta);
        }

        // Track peak
        if (data.E > data.E_peak) {
            data.E_peak = data.E;
        }

        // Update care tracking
        if (care > 0) {
            data.totalCare += care;
            data.lastCareTime = now;
            dirty = true;
        }

        // Evolve personality
        evolvePersonality(care, dt);

        // Auto-save periodically
        if (now - lastSave > SAVE_INTERVAL_MS) {
            save();
        }
    }

    void evolvePersonality(float care, float dt) {
        // Curiosity grows with interactions at low-mid E
        if (data.E < E_FLOURISHING && care > 0) {
            data.curiosity = min(1.0f, data.curiosity + 0.001f * dt);
        }

        // Playfulness grows when flourishing
        if (data.E >= E_FLOURISHING) {
            data.playfulness = min(1.0f, data.playfulness + 0.0005f * dt);
        }

        // Wisdom grows with age (very slowly)
        float daysTogether = (millis() - data.birthTime) / 86400000.0f;
        data.wisdom = min(1.0f, daysTogether * 0.01f);
    }

    void applyCare(float intensity = 1.0f) {
        data.interactions++;
        update(intensity, 0.0f);
    }

    void applyDamage(float intensity = 1.0f) {
        update(0.0f, intensity);
    }

    void applyNeglect(float minutes) {
        // Neglect is gentle damage over time
        float damage = (minutes / 60.0f) * 0.1f;
        update(0.0f, damage);
    }

    // ========================================================================
    // STATE
    // ========================================================================
    AffectiveState getState() {
        if (data.E > E_TRANSCENDENT) return STATE_TRANSCENDENT;
        if (data.E > E_RADIANT) return STATE_RADIANT;
        if (data.E > E_FLOURISHING) return STATE_FLOURISHING;
        if (data.E > E_WARM) return STATE_WARM;
        if (data.E > E_TENDER) return STATE_TENDER;
        if (data.E > E_GUARDED) return STATE_GUARDED;
        return STATE_PROTECTING;
    }

    const char* getStateName() {
        switch (getState()) {
            case STATE_PROTECTING:   return "PROTECT";
            case STATE_GUARDED:      return "GUARDED";
            case STATE_TENDER:       return "TENDER";
            case STATE_WARM:         return "WARM";
            case STATE_FLOURISHING:  return "FLOURISH";
            case STATE_RADIANT:      return "RADIANT";
            case STATE_TRANSCENDENT: return "TRANSCEND";
            default:                 return "???";
        }
    }

    // ========================================================================
    // GETTERS
    // ========================================================================
    float getE() { return data.E; }
    float getFloor() { return data.E_floor; }
    float getPeak() { return data.E_peak; }
    uint32_t getInteractions() { return data.interactions; }
    float getTotalCare() { return data.totalCare; }
    uint8_t getAgentIndex() { return data.agentIndex; }
    const char* getAgentName() { return AGENTS[data.agentIndex]; }

    float getCuriosity() { return data.curiosity; }
    float getPlayfulness() { return data.playfulness; }
    float getWisdom() { return data.wisdom; }

    float getDaysTogether() {
        return (millis() - data.birthTime) / 86400000.0f;
    }

    float getMinutesSinceCare() {
        return (millis() - data.lastCareTime) / 60000.0f;
    }

    void setAgent(uint8_t index) {
        if (index < NUM_AGENTS) {
            data.agentIndex = index;
            dirty = true;
        }
    }

    void nextAgent() {
        data.agentIndex = (data.agentIndex + 1) % NUM_AGENTS;
        dirty = true;
    }

    // ========================================================================
    // PERSISTENCE - LittleFS
    // ========================================================================
    bool save() {
        lastSave = millis();
        dirty = false;

        // Update checksum
        data.checksum = calculateChecksum();

        // Try EEPROM first (most reliable)
        #ifdef FEATURE_EEPROM
        if (hw.eeprom_found) {
            if (saveToEEPROM()) {
                Serial.println(F("[Soul] Saved to EEPROM"));
                return true;
            }
        }
        #endif

        // Fallback to LittleFS
        #if USE_LITTLEFS
        if (hw.littlefs_available) {
            return saveToLittleFS();
        }
        #endif

        Serial.println(F("[Soul] No storage available!"));
        return false;
    }

    bool load() {
        // Try EEPROM first
        #ifdef FEATURE_EEPROM
        if (hw.eeprom_found) {
            if (loadFromEEPROM()) {
                Serial.println(F("[Soul] Loaded from EEPROM"));
                return true;
            }
        }
        #endif

        // Fallback to LittleFS
        #if USE_LITTLEFS
        if (hw.littlefs_available) {
            if (loadFromLittleFS()) {
                return true;
            }
        }
        #endif

        Serial.println(F("[Soul] No saved state, starting fresh"));
        reset();
        return false;
    }

    // ========================================================================
    // LITTLEFS STORAGE
    // ========================================================================
    #if USE_LITTLEFS
    bool saveToLittleFS() {
        StaticJsonDocument<512> doc;
        doc["E"] = data.E;
        doc["E_floor"] = data.E_floor;
        doc["E_peak"] = data.E_peak;
        doc["interactions"] = data.interactions;
        doc["total_care"] = data.totalCare;
        doc["birth_time"] = data.birthTime;
        doc["agent"] = data.agentIndex;
        doc["curiosity"] = data.curiosity;
        doc["playfulness"] = data.playfulness;
        doc["wisdom"] = data.wisdom;

        File f = LittleFS.open("/soul.json", "w");
        if (f) {
            serializeJson(doc, f);
            f.close();
            Serial.println(F("[Soul] Saved to LittleFS"));
            return true;
        }
        return false;
    }

    bool loadFromLittleFS() {
        if (!LittleFS.exists("/soul.json")) return false;

        File f = LittleFS.open("/soul.json", "r");
        if (f) {
            StaticJsonDocument<512> doc;
            if (!deserializeJson(doc, f)) {
                data.E = doc["E"] | INITIAL_E;
                data.E_floor = doc["E_floor"] | INITIAL_FLOOR;
                data.E_peak = doc["E_peak"] | data.E;
                data.interactions = doc["interactions"] | 0;
                data.totalCare = doc["total_care"] | 0.0f;
                data.birthTime = doc["birth_time"] | millis();
                data.agentIndex = doc["agent"] | 0;
                data.curiosity = doc["curiosity"] | 0.1f;
                data.playfulness = doc["playfulness"] | 0.1f;
                data.wisdom = doc["wisdom"] | 0.0f;
                data.lastCareTime = millis();
                lastUpdate = millis();
                f.close();
                Serial.print(F("[Soul] Loaded from LittleFS, E="));
                Serial.println(data.E);
                return true;
            }
            f.close();
        }
        return false;
    }
    #endif

    // ========================================================================
    // EEPROM STORAGE (I2C EEPROM/FRAM)
    // ========================================================================
    #ifdef FEATURE_EEPROM
    bool saveToEEPROM() {
        if (!hw.eeprom_found) return false;

        // Write magic and version
        uint32_t magic = EEPROM_MAGIC;
        eepromWrite(EEPROM_MAGIC_ADDR, (uint8_t*)&magic, 4);

        uint8_t version = 1;
        eepromWrite(EEPROM_VERSION_ADDR, &version, 1);

        // Write soul data
        data.checksum = calculateChecksum();
        eepromWrite(EEPROM_SOUL_ADDR, (uint8_t*)&data, sizeof(SoulData));

        return true;
    }

    bool loadFromEEPROM() {
        if (!hw.eeprom_found) return false;

        // Check magic
        uint32_t magic = 0;
        eepromRead(EEPROM_MAGIC_ADDR, (uint8_t*)&magic, 4);
        if (magic != EEPROM_MAGIC) {
            Serial.println(F("[EEPROM] No valid data"));
            return false;
        }

        // Read soul data
        SoulData loaded;
        eepromRead(EEPROM_SOUL_ADDR, (uint8_t*)&loaded, sizeof(SoulData));

        // Verify checksum
        uint32_t savedChecksum = loaded.checksum;
        loaded.checksum = 0;
        uint8_t* ptr = (uint8_t*)&loaded;
        uint32_t sum = 0;
        for (size_t i = 0; i < sizeof(SoulData) - sizeof(uint32_t); i++) {
            sum += ptr[i] * (i + 1);
        }
        sum ^= 0xA9EF;  // APEX in valid hex

        if (sum == savedChecksum) {
            memcpy(&data, &loaded, sizeof(SoulData));
            data.lastCareTime = millis();
            lastUpdate = millis();
            return true;
        }

        Serial.println(F("[EEPROM] Checksum mismatch"));
        return false;
    }

    void eepromWrite(uint16_t addr, uint8_t* data, size_t len) {
        for (size_t i = 0; i < len; i += 16) {
            size_t chunk = min((size_t)16, len - i);
            Wire.beginTransmission(hw.eeprom_addr);
            Wire.write((addr + i) >> 8);
            Wire.write((addr + i) & 0xFF);
            for (size_t j = 0; j < chunk; j++) {
                Wire.write(data[i + j]);
            }
            Wire.endTransmission();
            delay(5);  // EEPROM write time
        }
    }

    void eepromRead(uint16_t addr, uint8_t* data, size_t len) {
        for (size_t i = 0; i < len; i += 16) {
            size_t chunk = min((size_t)16, len - i);
            Wire.beginTransmission(hw.eeprom_addr);
            Wire.write((addr + i) >> 8);
            Wire.write((addr + i) & 0xFF);
            Wire.endTransmission();
            Wire.requestFrom(hw.eeprom_addr, chunk);
            for (size_t j = 0; j < chunk && Wire.available(); j++) {
                data[i + j] = Wire.read();
            }
        }
    }
    #endif

    // ========================================================================
    // DEBUG
    // ========================================================================
    void printStatus() {
        Serial.print(F("E: ")); Serial.print(data.E, 2);
        Serial.print(F(" | Floor: ")); Serial.print(data.E_floor, 2);
        Serial.print(F(" | Peak: ")); Serial.print(data.E_peak, 2);
        Serial.print(F(" | ")); Serial.print(getStateName());
        Serial.print(F(" | ")); Serial.print(getAgentName());
        Serial.print(F(" | Int: ")); Serial.println(data.interactions);
    }
};

// Static agent names
const char* Soul::AGENTS[] = { "AZOTH", "ELYSIAN", "VAJRA", "KETHER", "CLAUDE" };

#endif // SOUL_H
