import openai

FUNC_SPEC = [{
    "name": "evaluate_emotion",
    "description": "分析文字情緒、時長與偏見次數",
    "parameters": {
        "type": "object",
        "properties": {
            "emotion_label": { "type": "string" },
            "duration":      { "type": "number" },
            "bias_count":    { "type": "integer" }
        },
        "required": ["emotion_label", "duration", "bias_count"],
        "additionalProperties": False
    }
}]

completion = openai.ChatCompletion.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "user", "content": "輸入文字……"}
    ],
    functions=FUNC_SPEC,
    function_call={"name": "evaluate_emotion"}  # 強制使用此函式
)

result = completion.choices[0].message.function_call["arguments"]  # 已是 JSON 物件