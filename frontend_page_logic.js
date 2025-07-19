// 初始化狀態
let personNear = true;
let weather = "暴雨"; // 例如："晴天", "陰天", "小雨", "暴雨"
let rainDuration = 130; // 單位：秒
let buttonPressed = false;
let crackShown = false;

// 主邏輯判斷函式
function handleMirrorState() {
  if (!personNear) {
    playWeatherVideo(weather);
    return;
  }

  // 雨天且超過兩分鐘：播放裂痕動畫
  if ((weather === "小雨" || weather === "暴雨") && rainDuration > 120) {
    if (!crackShown) {
      crackShown = true;
      playCrackAnimation();
      logEvent("crackAnimation");
    }
    return;
  }

  // 若已裂痕，但天氣變晴 → 動畫消失
  if (crackShown && weather === "晴天") {
    crackShown = false;
    fadeOutCrackAnimation();
    logEvent("crackFadeOut");
    return;
  }

  // 晴天／陰天時
  if (weather === "晴天" || weather === "陰天") {
    if (buttonPressed) {
      openBiasRecordPage();
      logEvent("biasEventRecord");
    } else {
      keepUnchanged();
    }
  }
}

// 功能執行函式（可連接畫面或硬體控制）
function playWeatherVideo(weather) {
  console.log(`🌤 播放 ${weather} 影片與字幕`);
}

function playCrackAnimation() {
  console.log("💥 播放裂痕動畫");
}

function fadeOutCrackAnimation() {
  console.log("💨 裂痕動畫消失");
}

function openBiasRecordPage() {
  console.log("📘 進入偏見事件紀錄頁面");
}

function keepUnchanged() {
  console.log("🔲 畫面不變化");
}

// 後端紀錄功能
function logEvent(eventName) {
  fetch("http://localhost:8000/log", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      timestamp: new Date().toISOString(),
      event: eventName,
      weather: weather,
      person_near: personNear,
    }),
  }).then((res) => console.log(`✅ 已紀錄事件: ${eventName}`));
}

// 模擬偵測執行（每 2 秒跑一次邏輯）
setInterval(handleMirrorState, 2000);
