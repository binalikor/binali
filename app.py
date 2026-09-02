# Hugging Face API 호출 함수 (최신 라우터 엔드포인트 및 예외 처리 적용)
def query_huggingface(prompt, token, model_name, max_retries=3):
    # 토큰 앞머리 'hf_' 누락 시 자동 보정
    clean_token = token.strip()
    if not clean_token.startswith("hf_"):
        clean_token = "hf_" + clean_token

    # 최신 허깅페이스 인퍼런스 라우터 URL
    api_url = f"https://router.huggingface.co/hf-inference/models/{model_name}"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Content-Type": "application/json"
    }
    
    # 16:9 정규 와이드 해상도
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1152,
            "height": 648,
            "negative_prompt": "blurry, deformed, cropped, ugly, extra limbs, stretched, 1:1 aspect ratio, modern clothing, photo, 3d render"
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                return response.content, None
            
            # 모델 로딩 중(503) 발생 시 자동 대기 후 재시도
            elif response.status_code == 503:
                wait_time = 15
                try:
                    err_data = response.json()
                    wait_time = int(err_data.get("estimated_time", 15))
                except Exception:
                    pass
                st.info(f"⏳ Hugging Face 서버가 모델을 메모리에 로딩 중입니다. {wait_time}초 후 재시도합니다... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            elif response.status_code == 401:
                return None, "인증 실패(401): Hugging Face 토큰이 유효하지 않습니다. 토큰을 다시 확인해주세요."
            else:
                return None, f"서버 응답 오류 (코드 {response.status_code}): {response.text}"
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None, "Hugging Face 서버와의 네트워크 연결이 끊어졌습니다. 잠시 후 다시 시도해 주세요."
        except Exception as e:
            return None, f"통신 중 예외 발생: {e}"
            
    return None, "서버 대기 시간 초과. 잠시 후 다시 시도해 주세요."
