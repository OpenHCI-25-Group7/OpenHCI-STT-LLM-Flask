#include <Adafruit_NeoPixel.h>
#define LED_PIN 13
#define LED_COUNT 60
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB+NEO_KHZ800);

unsigned long prevMillis = 0;
const unsigned long interval = 30; // 更新間隔

unsigned long t0 = 0, t1 = 0, t2 = 0;
bool breathDir = true;
bool thunderFlash = false;
int brightness = 100;

// 用於閃爍/明暗切換
unsigned long lastChange = 0;
bool flashState = false;

void setup() {
  strip.begin();
  strip.show();
}

// 核心函式：變色 + 閃爍/明暗
void weather(int r, int g, int b, int brightness, int dimness) {
  unsigned long now = millis();
  // 每 interval 切換閃爍狀態
  if (now - lastChange >= interval) {
    lastChange = now;
    flashState = !flashState;
    uint8_t currentB = flashState ? brightness : dimness;
    strip.setBrightness(currentB);
    for(int i=0; i<strip.numPixels(); i++){
      strip.setPixelColor(i, strip.Color(r, g, b));
    }
    strip.show();
  }
}

// 各種天氣包裝
void weatherSunny() {
  weather(255,244,214, 200, 150);
}
void weatherCloudy() {
  weather(180,180,200, 150, 100);
}
void weatherLightRain() {
  weather(100,160,255, 180, 120);
}
void weatherThunder() {
  // 閃電效果：每次呼叫切換紫／黃白
  if (flashState) weather(75, 0, 130, 220, 150);
  else weather(255,255,200, 255, 180);
}

void weatherSunnyPro(){
  unsigned long now = millis();
  if(now - t0 > 20){
    t0 = now;
    if(breathDir) brightness += 2;
    else brightness -= 2;
    if(brightness>=220||brightness<=150) breathDir=!breathDir;
    strip.setBrightness(brightness);

    uint8_t g = 244 + (brightness-150)/7;
    uint8_t b = 214 - (brightness-150)/10;
    for(int i=0;i<LED_COUNT;i++) strip.setPixelColor(i, strip.Color(255, g, b));
    strip.show();
  }
}

void weatherCloudyPro(){
  unsigned long now = millis();
  if(now - t1 > 50){
    t1 = now;
    uint8_t base = 180 + random(-10,10);
    brightness = 120 + random(-20,20);
    strip.setBrightness(brightness);
    for(int i=0;i<LED_COUNT;i++)
      strip.setPixelColor(i, strip.Color(base, base, base+20));
    strip.show();
  }
}

void weatherLightRainPro(){
  unsigned long now = millis();
  if(now - t0 > 30){
    t0 = now;
    uint8_t mod = random(0,30);
    uint8_t currB = 160 + (breathDir ? mod : -mod);
    if(mod>25) breathDir=!breathDir;
    strip.setBrightness(currB);
    for(int i=0;i<LED_COUNT;i++){
      strip.setPixelColor(i, strip.Color(100, 160-mod, 255-mod/2));
    }
    strip.show();
  }
}

void weatherThunderPro(){
  unsigned long now = millis();
  
  if(!thunderFlash && random(0,1000)<5){
    thunderFlash = true;
    t2 = now;
  }

  if(thunderFlash){
    if(now - t2 < 100){
      strip.setBrightness(255);
      for(int i=0;i<LED_COUNT;i++)
        strip.setPixelColor(i, strip.Color(255,255,200));
      strip.show();
    } else {
      thunderFlash = false;
    }
  } else {
    strip.setBrightness(100 + random(-10,10));
    for(int i=0;i<LED_COUNT;i++)
      strip.setPixelColor(i, strip.Color(90,70,140));
    strip.show();
  }
}



void loop() {
  unsigned long now = millis();
  
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    String weather = input.substring(0);  // Extract the weather code after "WS2812:"
    int weatherCode = weather.toInt();
    Serial.print(weatherCode);

    switch(weatherCode) {
      case 0: weatherSunny(); break;
      case 1: weatherCloudy(); break;
      case 2: weatherLightRain(); break;
      case 3: weatherThunder(); break;
      case 4: weatherSunnyPro(); break;
      case 5: weatherCloudyPro(); break;
      case 6: weatherLightRainPro(); break;
      case 7: weatherThunderPro(); break;
    }
  }
}
