def mirror_interaction(
    person_near: bool,
    weather: str,
    rain_duration_sec: int,
    button_pressed: bool
):
    """
    person_near: 是否靠近鏡子（True 表示靠近）
    weather: '晴天'、'陰天'、'小雨'、'暴雨'
    rain_duration_sec: 降雨狀態持續時間（秒）
    button_pressed: 是否按下按鈕
    """

    if not person_near:
        # 人遠離，依據天氣播放對應影片＋字幕
        if weather == "晴天":
            play_weather_video("晴天")
        elif weather == "陰天":
            play_weather_video("陰天")
        elif weather == "小雨" or weather == "雨天":
            play_weather_video("雨天")
        elif weather == "暴雨":
            play_weather_video("暴雨")
        else:
            print("⚠️ 未知天氣狀態")
        return

    # 人靠近鏡子，進入鏡子主流程判斷
    if weather in ["小雨", "暴雨"] and rain_duration_sec > 120:
        play_crack_animation()
    elif weather in ["晴天", "陰天"]:
        if button_pressed:
            open_bias_event_record_page()
        else:
            keep_unchanged()
    else:
        print("⚠️ 條件不符，無操作")


# 以下為功能函式實作（可根據實際 UI 或硬體對應替換）
def play_weather_video(weather_type):
    print(f"播放 {weather_type} 影片＋字幕")

def play_crack_animation():
    print("✅ 播放裂痕動畫")

def open_bias_event_record_page():
    print("✅ 開啟偏見事件紀錄頁面")

def keep_unchanged():
    print("✅ 鏡子不變化")

# 測試案例
mirror_interaction(person_near=True, weather="小雨", rain_duration_sec=130, button_pressed=False)
mirror_interaction(person_near=True, weather="晴天", rain_duration_sec=0, button_pressed=True)
mirror_interaction(person_near=False, weather="暴雨", rain_duration_sec=0, button_pressed=False)