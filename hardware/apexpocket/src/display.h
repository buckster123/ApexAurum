/*
 * ╔════════════════════════════════════════════════════════════════════════╗
 * ║                         DISPLAY MODULE                                  ║
 * ║                                                                         ║
 * ║   Animated faces, screens, and UI for the OLED                          ║
 * ║   "The face reflects the soul"                                          ║
 * ╚════════════════════════════════════════════════════════════════════════╝
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "config.h"
#include "soul.h"
#include "hardware.h"

// ============================================================================
// EXPRESSION ENUM
// ============================================================================
enum Expression {
    EXPR_NEUTRAL = 0,
    EXPR_HAPPY,
    EXPR_EXCITED,
    EXPR_SAD,
    EXPR_SLEEPY,
    EXPR_SLEEPING,
    EXPR_CURIOUS,
    EXPR_SURPRISED,
    EXPR_LOVE,
    EXPR_THINKING,
    EXPR_CONFUSED,
    EXPR_BLINK,
    EXPR_WINK,
    EXPR_COUNT
};

// ============================================================================
// EYE/MOUTH TYPES
// ============================================================================
enum EyeType { EYE_NORMAL, EYE_CLOSED, EYE_STAR, EYE_HEART, EYE_WIDE, EYE_CURIOUS, EYE_SPIRAL };
enum MouthType { MOUTH_NEUTRAL, MOUTH_SMILE, MOUTH_BIG_SMILE, MOUTH_FROWN, MOUTH_OPEN, MOUTH_SMALL_O, MOUTH_WAVY, MOUTH_SLEEPY };

// ============================================================================
// FACE GEOMETRY
// ============================================================================
#define FACE_CENTER_X   64
#define EYE_Y           22
#define LEFT_EYE_X      44
#define RIGHT_EYE_X     84
#define MOUTH_Y         42

// ============================================================================
// BITMAPS - Eyes (12x12 pixels)
// ============================================================================
const uint8_t EYE_NORMAL_BMP[] PROGMEM = {
    0x0F,0x00, 0x3F,0xC0, 0x7F,0xE0, 0x7F,0xE0,
    0xFF,0xF0, 0xFF,0xF0, 0xFF,0xF0, 0xFF,0xF0,
    0x7F,0xE0, 0x7F,0xE0, 0x3F,0xC0, 0x0F,0x00
};
const uint8_t EYE_CLOSED_BMP[] PROGMEM = {
    0x00,0x00, 0x00,0x00, 0x00,0x00, 0x00,0x00,
    0x00,0x00, 0xFF,0xF0, 0xFF,0xF0, 0x00,0x00,
    0x00,0x00, 0x00,0x00, 0x00,0x00, 0x00,0x00
};
const uint8_t EYE_STAR_BMP[] PROGMEM = {
    0x06,0x00, 0x06,0x00, 0x06,0x00, 0xC6,0x30,
    0xF7,0xF0, 0x3F,0xC0, 0x1F,0x80, 0x3F,0xC0,
    0x79,0xE0, 0x70,0xE0, 0x60,0x60, 0x00,0x00
};
const uint8_t EYE_HEART_BMP[] PROGMEM = {
    0x00,0x00, 0x73,0x80, 0xFF,0xC0, 0xFF,0xC0,
    0xFF,0xC0, 0xFF,0xC0, 0x7F,0x80, 0x3F,0x00,
    0x1E,0x00, 0x0C,0x00, 0x00,0x00, 0x00,0x00
};
const uint8_t EYE_WIDE_BMP[] PROGMEM = {
    0x1E,0x00, 0x7F,0x80, 0x61,0x80, 0xC0,0xC0,
    0xC0,0xC0, 0xC0,0xC0, 0xC0,0xC0, 0xC0,0xC0,
    0x61,0x80, 0x7F,0x80, 0x1E,0x00, 0x00,0x00
};
const uint8_t EYE_CURIOUS_BMP[] PROGMEM = {
    0x1E,0x00, 0x7F,0x80, 0x61,0x80, 0xCE,0xC0,
    0xDF,0xC0, 0xDF,0xC0, 0xDF,0xC0, 0xCE,0xC0,
    0x61,0x80, 0x7F,0x80, 0x1E,0x00, 0x00,0x00
};
const uint8_t EYE_SPIRAL_BMP[] PROGMEM = {
    0x1E,0x00, 0x61,0x80, 0xCE,0xC0, 0xD1,0xC0,
    0xD6,0xC0, 0xD6,0xC0, 0xD0,0xC0, 0xCF,0xC0,
    0x60,0x80, 0x7F,0x80, 0x1E,0x00, 0x00,0x00
};

// Mouths (24x8 pixels)
const uint8_t MOUTH_NEUTRAL_BMP[] PROGMEM = {
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0x00,0x00,
    0x0F,0xFF,0x00, 0x0F,0xFF,0x00, 0x00,0x00,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00
};
const uint8_t MOUTH_SMILE_BMP[] PROGMEM = {
    0x00,0x00,0x00, 0x30,0x00,0xC0, 0x18,0x01,0x80,
    0x0C,0x03,0x00, 0x07,0x0E,0x00, 0x03,0xFC,0x00,
    0x00,0xF0,0x00, 0x00,0x00,0x00
};
const uint8_t MOUTH_BIG_SMILE_BMP[] PROGMEM = {
    0x20,0x00,0x40, 0x30,0x00,0xC0, 0x18,0x01,0x80,
    0x0C,0x03,0x00, 0x07,0xFE,0x00, 0x01,0xF8,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00
};
const uint8_t MOUTH_FROWN_BMP[] PROGMEM = {
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x00,0xF0,0x00,
    0x03,0xFC,0x00, 0x06,0x06,0x00, 0x0C,0x03,0x00,
    0x18,0x01,0x80, 0x10,0x00,0x80
};
const uint8_t MOUTH_OPEN_BMP[] PROGMEM = {
    0x01,0xF8,0x00, 0x07,0xFE,0x00, 0x0C,0x03,0x00,
    0x0C,0x03,0x00, 0x0C,0x03,0x00, 0x07,0xFE,0x00,
    0x01,0xF8,0x00, 0x00,0x00,0x00
};
const uint8_t MOUTH_SMALL_O_BMP[] PROGMEM = {
    0x00,0x00,0x00, 0x00,0xF0,0x00, 0x01,0x98,0x00,
    0x01,0x08,0x00, 0x01,0x98,0x00, 0x00,0xF0,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00
};
const uint8_t MOUTH_WAVY_BMP[] PROGMEM = {
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x18,0xC6,0x00,
    0x25,0x29,0x00, 0x42,0x10,0x80, 0x00,0x00,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00
};
const uint8_t MOUTH_SLEEPY_BMP[] PROGMEM = {
    0x00,0x00,0x00, 0x00,0x00,0x00, 0x04,0x02,0x00,
    0x03,0x0C,0x00, 0x00,0xF0,0x00, 0x00,0x00,0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00
};

// ============================================================================
// FACE DEFINITIONS
// ============================================================================
struct FaceDef {
    EyeType leftEye, rightEye;
    MouthType mouth;
    char accessory;
    int8_t accX, accY;
};

const FaceDef FACES[] = {
    { EYE_NORMAL, EYE_NORMAL, MOUTH_NEUTRAL, 0, 0, 0 },       // NEUTRAL
    { EYE_NORMAL, EYE_NORMAL, MOUTH_SMILE, 0, 0, 0 },         // HAPPY
    { EYE_STAR, EYE_STAR, MOUTH_BIG_SMILE, '!', 0, 6 },       // EXCITED
    { EYE_NORMAL, EYE_NORMAL, MOUTH_FROWN, 0, 0, 0 },         // SAD
    { EYE_CLOSED, EYE_CLOSED, MOUTH_SLEEPY, 'z', 24, 8 },     // SLEEPY
    { EYE_CLOSED, EYE_CLOSED, MOUTH_SLEEPY, 'Z', 26, 6 },     // SLEEPING
    { EYE_NORMAL, EYE_CURIOUS, MOUTH_SMALL_O, '?', 26, 6 },   // CURIOUS
    { EYE_WIDE, EYE_WIDE, MOUTH_OPEN, '!', 0, 6 },            // SURPRISED
    { EYE_HEART, EYE_HEART, MOUTH_SMILE, 0, 0, 0 },           // LOVE
    { EYE_NORMAL, EYE_CLOSED, MOUTH_WAVY, '.', 28, 10 },      // THINKING
    { EYE_SPIRAL, EYE_SPIRAL, MOUTH_WAVY, '?', 0, 6 },        // CONFUSED
    { EYE_CLOSED, EYE_CLOSED, MOUTH_NEUTRAL, 0, 0, 0 },       // BLINK
    { EYE_NORMAL, EYE_CLOSED, MOUTH_SMILE, 0, 0, 0 },         // WINK
};

// ============================================================================
// DISPLAY CLASS
// ============================================================================
class Display {
private:
    Adafruit_SSD1306* oled;
    bool initialized;

    // Animation state
    Expression currentExpr;
    Expression targetExpr;
    bool isBlinking;
    uint8_t blinkFrame;
    unsigned long lastBlink;
    unsigned long blinkInterval;

    // Message display
    String messageText;
    unsigned long messageExpires;

    // Smooth animation
    float eyeOffsetX, eyeOffsetY;  // For look-around animation
    float targetOffsetX, targetOffsetY;

public:
    Display() : initialized(false), currentExpr(EXPR_NEUTRAL), targetExpr(EXPR_NEUTRAL),
                isBlinking(false), blinkFrame(0), eyeOffsetX(0), eyeOffsetY(0) {
        lastBlink = millis();
        blinkInterval = random(BLINK_MIN_MS, BLINK_MAX_MS);
        messageExpires = 0;
    }

    bool begin(Adafruit_SSD1306* display) {
        oled = display;
        if (!oled->begin(SSD1306_SWITCHCAPVCC, I2C_ADDR_OLED)) {
            Serial.println(F("[Display] SSD1306 init failed"));
            return false;
        }
        oled->setTextColor(SSD1306_WHITE);
        oled->setTextSize(1);
        initialized = true;
        Serial.println(F("[Display] OLED initialized"));
        return true;
    }

    bool isReady() { return initialized; }

    // ========================================================================
    // EXPRESSION CONTROL
    // ========================================================================
    void setExpression(Expression expr) {
        targetExpr = expr;
        if (currentExpr != targetExpr) {
            // Could add transition animation here
            currentExpr = targetExpr;
        }
    }

    Expression stateToExpression(AffectiveState state) {
        switch (state) {
            case STATE_PROTECTING:   return EXPR_SLEEPING;
            case STATE_GUARDED:      return EXPR_SAD;
            case STATE_TENDER:       return EXPR_CURIOUS;
            case STATE_WARM:         return EXPR_NEUTRAL;
            case STATE_FLOURISHING:  return EXPR_HAPPY;
            case STATE_RADIANT:      return EXPR_EXCITED;
            case STATE_TRANSCENDENT: return EXPR_LOVE;
            default:                 return EXPR_NEUTRAL;
        }
    }

    // ========================================================================
    // ANIMATION UPDATE
    // ========================================================================
    void update() {
        if (!initialized) return;

        unsigned long now = millis();

        // Blink animation
        if (isBlinking) {
            if (now - lastBlink > 60) {
                blinkFrame++;
                lastBlink = now;
                if (blinkFrame >= 4) {
                    isBlinking = false;
                    blinkFrame = 0;
                    blinkInterval = random(BLINK_MIN_MS, BLINK_MAX_MS);
                }
            }
        } else if (now - lastBlink > blinkInterval) {
            isBlinking = true;
            blinkFrame = 0;
            lastBlink = now;
        }

        // Clear expired message
        if (messageExpires > 0 && now > messageExpires) {
            messageText = "";
            messageExpires = 0;
        }

        // Smooth eye movement (idle animation)
        #ifdef FEATURE_ANIMATIONS
        static unsigned long lastMove = 0;
        if (now - lastMove > 2000 + random(3000)) {
            targetOffsetX = random(-3, 4);
            targetOffsetY = random(-2, 3);
            lastMove = now;
        }
        eyeOffsetX += (targetOffsetX - eyeOffsetX) * 0.1f;
        eyeOffsetY += (targetOffsetY - eyeOffsetY) * 0.1f;
        #endif
    }

    // ========================================================================
    // MESSAGE DISPLAY
    // ========================================================================
    void showMessage(const char* msg, unsigned long duration = 3000) {
        messageText = msg;
        messageExpires = millis() + duration;
    }

    void clearMessage() {
        messageText = "";
        messageExpires = 0;
    }

    // ========================================================================
    // DRAWING FUNCTIONS
    // ========================================================================
    void drawEye(int x, int y, EyeType type) {
        const uint8_t* bmp = EYE_NORMAL_BMP;
        switch (type) {
            case EYE_CLOSED:  bmp = EYE_CLOSED_BMP; break;
            case EYE_STAR:    bmp = EYE_STAR_BMP; break;
            case EYE_HEART:   bmp = EYE_HEART_BMP; break;
            case EYE_WIDE:    bmp = EYE_WIDE_BMP; break;
            case EYE_CURIOUS: bmp = EYE_CURIOUS_BMP; break;
            case EYE_SPIRAL:  bmp = EYE_SPIRAL_BMP; break;
            default: break;
        }
        int drawX = x - 6 + (int)eyeOffsetX;
        int drawY = y - 6 + (int)eyeOffsetY;
        oled->drawBitmap(drawX, drawY, bmp, 12, 12, SSD1306_WHITE);
    }

    void drawMouth(int x, int y, MouthType type) {
        const uint8_t* bmp = MOUTH_NEUTRAL_BMP;
        switch (type) {
            case MOUTH_SMILE:     bmp = MOUTH_SMILE_BMP; break;
            case MOUTH_BIG_SMILE: bmp = MOUTH_BIG_SMILE_BMP; break;
            case MOUTH_FROWN:     bmp = MOUTH_FROWN_BMP; break;
            case MOUTH_OPEN:      bmp = MOUTH_OPEN_BMP; break;
            case MOUTH_SMALL_O:   bmp = MOUTH_SMALL_O_BMP; break;
            case MOUTH_WAVY:      bmp = MOUTH_WAVY_BMP; break;
            case MOUTH_SLEEPY:    bmp = MOUTH_SLEEPY_BMP; break;
            default: break;
        }
        oled->drawBitmap(x - 12, y - 4, bmp, 24, 8, SSD1306_WHITE);
    }

    void drawFace(Expression expr) {
        // Handle blink override
        Expression drawExpr = expr;
        if (isBlinking && (blinkFrame == 1 || blinkFrame == 2)) {
            drawExpr = EXPR_BLINK;
        }

        const FaceDef& face = FACES[drawExpr];
        drawEye(LEFT_EYE_X, EYE_Y, face.leftEye);
        drawEye(RIGHT_EYE_X, EYE_Y, face.rightEye);
        drawMouth(FACE_CENTER_X, MOUTH_Y, face.mouth);

        if (face.accessory != 0) {
            oled->setCursor(FACE_CENTER_X + face.accX, face.accY);
            oled->print(face.accessory);
            if (face.accessory == 'Z') {
                oled->setCursor(FACE_CENTER_X + face.accX - 8, face.accY + 6);
                oled->print('z');
            }
        }
    }

    // ========================================================================
    // SCREEN RENDERS
    // ========================================================================
    void renderFaceScreen(Soul& soul, bool wifiConnected, bool villageOnline) {
        if (!initialized) return;

        oled->clearDisplay();

        // Title bar
        oled->setCursor(0, 0);
        oled->print(F("APEX "));
        oled->print(soul.getAgentName());

        // Status icons (right side)
        oled->setCursor(100, 0);
        if (hw.battery_available) {
            uint8_t batt = getBatteryPercent();
            if (batt != 255) {
                if (batt > 75) oled->print(F("B"));
                else if (batt > 25) oled->print(F("b"));
                else oled->print(F("!"));
            }
        }
        oled->setCursor(110, 0);
        if (villageOnline) oled->print(F("V"));
        else if (wifiConnected) oled->print(F("W"));
        else oled->print(F("X"));

        // Battery percentage if critical
        if (hw.battery_available) {
            uint8_t batt = getBatteryPercent();
            if (batt != 255 && batt <= 20) {
                oled->setCursor(85, 0);
                oled->print(batt);
                oled->print(F("%"));
            }
        }

        // Face
        drawFace(currentExpr);

        // Bottom area: message or status
        if (messageText.length() > 0) {
            oled->drawFastHLine(0, 50, 128, SSD1306_WHITE);
            oled->setCursor(0, 53);
            // Word wrap for long messages
            if (messageText.length() <= 21) {
                oled->print(messageText);
            } else {
                oled->print(messageText.substring(0, 21));
                oled->setCursor(0, 61);
                oled->print(messageText.substring(21, 42));
            }
        } else {
            // Status line
            oled->setCursor(0, 56);
            char buf[24];
            snprintf(buf, sizeof(buf), "E:%.1f %s", soul.getE(), soul.getStateName());
            oled->print(buf);
        }

        oled->display();
    }

    void renderStatusScreen(Soul& soul, bool wifiConnected, bool villageOnline, int toolsAvailable) {
        if (!initialized) return;

        oled->clearDisplay();
        oled->setCursor(0, 0);
        oled->println(F("=== APEXPOCKET MAX ==="));

        oled->setCursor(0, 12);
        oled->print(F("E: ")); oled->print(soul.getE(), 1);
        oled->print(F(" Fl: ")); oled->println(soul.getFloor(), 1);

        oled->setCursor(0, 22);
        oled->print(F("Peak: ")); oled->print(soul.getPeak(), 1);
        oled->print(F(" ")); oled->println(soul.getStateName());

        oled->setCursor(0, 32);
        oled->print(F("Agent: ")); oled->println(soul.getAgentName());

        oled->setCursor(0, 42);
        oled->print(F("Village: "));
        if (villageOnline) {
            oled->print(toolsAvailable);
            oled->println(F(" tools"));
        } else {
            oled->println(wifiConnected ? F("Offline") : F("No WiFi"));
        }

        if (hw.battery_available) {
            oled->setCursor(0, 52);
            oled->print(F("Batt: "));
            uint8_t batt = getBatteryPercent();
            if (batt != 255) {
                oled->print(batt);
                oled->print(F("% ("));
                oled->print(readBatteryMV());
                oled->println(F("mV)"));
            } else {
                oled->println(F("N/A"));
            }
        }

        oled->display();
    }

    void renderAgentScreen(Soul& soul) {
        if (!initialized) return;

        oled->clearDisplay();
        oled->setCursor(0, 0);
        oled->println(F("SELECT AGENT"));
        oled->drawFastHLine(0, 10, 128, SSD1306_WHITE);

        for (int i = 0; i < Soul::NUM_AGENTS; i++) {
            oled->setCursor(10, 14 + i * 10);
            if (i == soul.getAgentIndex()) {
                oled->print(F("> "));
            } else {
                oled->print(F("  "));
            }
            oled->println(Soul::AGENTS[i]);
        }

        oled->setCursor(0, 56);
        oled->print(F("[A]Select [B]Back"));
        oled->display();
    }

    void renderBootScreen() {
        if (!initialized) return;

        oled->clearDisplay();
        oled->setCursor(10, 20);
        oled->setTextSize(1);
        oled->println(F("APEXPOCKET MAX"));
        oled->setCursor(20, 35);
        oled->println(F("Initializing..."));
        oled->display();
    }

    void renderSleepScreen(Soul& soul) {
        if (!initialized) return;

        oled->clearDisplay();
        drawFace(EXPR_SLEEPING);
        oled->setCursor(20, 56);
        oled->print(F("E:"));
        oled->print(soul.getE(), 1);
        oled->print(F(" Sleeping..."));
        oled->display();
    }

    // Direct access for custom drawing
    Adafruit_SSD1306* getOLED() { return oled; }
};

#endif // DISPLAY_H
