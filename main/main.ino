#include <Adafruit_NeoPixel.h>

#define LED_PIN    13  // LED燈條連接的Arduino腳位
#define LED_COUNT  60  // LED燈的數量
#define default_brightness 30 // LED 預設亮度

#define TRIG_PIN 7
#define ECHO_PIN 8
#define DIST_THRESHOLD 40
#define DIST_TOUCH_THRESHOLD 5

int state = 0;  // 0: Far, 1: Near, 2: Touch
int dist = 0;
int countClose = 0; 
int countTouch = 0; 

uint8_t brightness = default_brightness;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

unsigned long lastTimeButtonCheck = 0;
unsigned long lastTimeUltrasonicCheck = 0;
unsigned long buttonInterval = 10;
unsigned long ultrasonicInterval = 50;

unsigned long recoverTime = 5000;  // Timeout for state recovery (in milliseconds)
unsigned long endTime = 0;  // When the state should reset (time at which the state changes)

int stableCountThreshold = 3;  // Number of stable readings before changing the state

void setup() {
  strip.begin();           // 初始化LED燈條
  strip.show();            // 初始化所有LED為'關閉'狀態

  Serial.begin(9600);           //設定序列埠監控視窗 (Serial Monitor) 和 Arduino資料傳輸速率為 9600 bps (Bits Per Second)
  pinMode(TRIG_PIN, OUTPUT);      //Arduino 對外啟動距離感測器Trig腳，射出超音波 
  pinMode(ECHO_PIN, INPUT);       //超音波被障礙物反射後，Arduino讀取感測器Echo腳的時間差
  setDefault();
}

void loop() {
  unsigned long currentMillis = millis();  // 獲取當前時間

  // Check ultrasonic sensor
  if (currentMillis - lastTimeUltrasonicCheck >= ultrasonicInterval) {
    lastTimeUltrasonicCheck = currentMillis;
    checkUltrasonic();
  }

  // If the current time exceeds recoverTime, reset state to 0 (far)
  if (state == 1 && currentMillis - endTime >= recoverTime) {
    // Serial.println(currentMillis); // far
    // Serial.println(endTime); // far
    state = 0;  // Reset state to far after the timeout
    Serial.println("MODE:0"); // far
    setDefault();
  }
  if (state == 2 && currentMillis - endTime >= recoverTime) {
    // Serial.println(currentMillis); // far
    // Serial.println(endTime); // far
    state = 1;  // Reset state to far after the timeout
    Serial.println("MODE:1"); // far
    endTime = millis();
    setDefault();
  }

  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');  // Read the input until a newline character

    // Check if the input starts with "WS2812:"
    if (input.startsWith("WS2812:")) {
      String weather = input.substring(7);  // Extract the weather code after "WS2812:"

      // Convert the mode to an integer
      int weatherCode = weather.toInt();
      Serial.print(weatherCode);

      // Control the LED strip based on the weather code
      switch (weatherCode) {
        case 0:  // Sunny (晴天)
          setSunny();  // Set LEDs for sunny weather
          break;
        case 1:  // Cloudy (陰天)
          setCloudy();  // Set LEDs for cloudy weather
          break;
        case 2:  // Light Rain (小雨)
          setLightRain();  // Set LEDs for light rain
          break;
        case 3:  // Thunderstorm (雷陣雨)
          setThunderstorm();  // Set LEDs for thunderstorm
          break;
        default:
          setDefault();  // Default case, if weatherCode is invalid
          break;
      }
    }
  }
}

void checkUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(5);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  pinMode(ECHO_PIN, INPUT);

  int dist = (pulseIn(ECHO_PIN, HIGH) / 2) / 29.1;  

  // Serial.print("Distance: ");
  // Serial.print(dist);
  // Serial.println(" cm");

  // Check if the person is within the near or touch range
  if (dist < DIST_THRESHOLD) {
    countClose++;
  } else {
    countClose = 0;
  }

  if (dist < DIST_TOUCH_THRESHOLD) {
    countTouch++;
  } else {
    countTouch = 0;
  }

  if (countTouch >= 1){
    if(state != 2) {
      state = 2;
      endTime = millis();  // Set the recover time when entering state 2 (touch)
      Serial.println("MODE:2"); // touch
    }
    else{
      endTime = millis();  // Set the recover time when entering state 2 (touch)
    }
  }
  else if (state != 2 && countClose >= stableCountThreshold) {
    if(state != 1){
      state = 1;
      endTime = millis();  // Set the recover time when entering state 1 (near)
      Serial.println("MODE:1"); // approach
    }else{
      endTime = millis();  // Set the recover time when entering state 1 (near)
    }
  } 
  
}

void set_led(int r, int g, int b, int brightness) {  
   for(int i = 0; i < strip.numPixels(); i++) {            
     strip.setPixelColor(i, strip.Color(r, g, b));
     strip.show();              
   }
   strip.setBrightness(brightness);
}

void setSunny() {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(255, 204, 85));  // Sunny color
  }
  strip.show();
  strip.setBrightness(0.8);
}

void setCloudy() {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(180, 190, 200));  // Cloudy color
  }
  strip.show();
  strip.setBrightness(0.6);
}

void setLightRain() {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(100, 160, 255));  // Light rain color
  }
  strip.show();
  strip.setBrightness(0.6);
}

void setThunderstorm() {
  unsigned long currentMillis = millis();
  static unsigned long lastFlashTime = 0;
  static bool isPurple = true;  // Flag to toggle between purple and yellow

  // Flashing interval (milliseconds)
  unsigned long flashInterval = 300;  // Change this value to adjust the speed of flashing

  if (currentMillis - lastFlashTime >= flashInterval) {
    lastFlashTime = currentMillis;

    // Toggle between purple and yellow
    if (isPurple) {
      for (int i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, strip.Color(90, 70, 140));  // Purple color
      }
    } else {
      for (int i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, strip.Color(255, 255, 200));  // Yellow color
      }
    }
    strip.show();

    isPurple = !isPurple;
  }
}

void setDefault() {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(100, 100, 100));  // Default color (grey)
  }
  strip.show();
}
