#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>

// WiFi Credentials
const char* ssid = "College_WiFi";
const char* password = "College_Password";

// Server
const char* serverURL = "http://your-server-ip:5000/api/update";  // Update this IP
const String reader_id = "reader_1";  // Change per block: reader_2, reader_3...

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 22

MFRC522 mfrc522(SS_PIN, RST_PIN);
String lastUID = "";
unsigned long lastSendTime = 0;

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi Connected: " + WiFi.localIP().toString());
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();

  // Prevent duplicate rapid reads (within 3 sec)
  if (uid == lastUID && millis() - lastSendTime < 3000) return;

  Serial.println("RFID Tag: " + uid);
  sendToServer(uid);
  lastUID = uid;
  lastSendTime = millis();

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void sendToServer(String tag) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"device_id\":\"ESP32_" + reader_id + "\",\"source\":\"rfid\",\"reader_id\":\"" + reader_id + "\",\"rfid_tag\":\"" + tag + "\"}";

    int httpCode = http.POST(payload);
    if (httpCode > 0) {
      String response = http.getString();
      Serial.println("Server response: " + response);
    } else {
      Serial.println("Error sending data. HTTP code: " + String(httpCode));
    }

    http.end();
  } else {
    Serial.println("WiFi not connected");
  }
}
