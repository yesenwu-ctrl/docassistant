import base64

import requests
from docx import Document
from pypdf import PdfReader
from bs4 import BeautifulSoup

class ContentProcessor:
    @staticmethod
    def read_docx(file):
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])

    @staticmethod
    def read_pdf(file):
        reader = PdfReader(file)
        return "\n".join([(page.extract_text() or "") for page in reader.pages])

    @staticmethod
    def image_to_data_url(file):
        """Convert an uploaded image into a chat-completions compatible data URL."""
        mime_type = getattr(file, "type", None) or "image/png"
        data = file.getvalue()
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def list_models(api_key, base_url, require_vision=False):
        """Fetch OpenAI-compatible model metadata from the configured provider."""
        if not api_key or not api_key.strip():
            return [], "請先輸入 API Key，才能讀取可用模型清單。"
        if not base_url or not base_url.strip():
            return [], "請先輸入 OpenAI 相容 API Base URL。"

        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        try:
            response = requests.get(f"{base_url.strip().rstrip('/')}/models", headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            return [], f"讀取模型清單失敗（HTTP {status}），請確認 API Key 與服務商網址。"
        except requests.exceptions.RequestException:
            return [], "讀取模型清單時發生網路錯誤，請稍後再試。"
        except ValueError:
            return [], "服務商回傳的模型清單格式無法解析。"

        raw_models = payload.get("data", payload if isinstance(payload, list) else [])
        models = []
        for item in raw_models:
            if not isinstance(item, dict) or not item.get("id"):
                continue

            architecture = item.get("architecture") or {}
            input_modalities = architecture.get("input_modalities") or item.get("input_modalities") or []
            output_modalities = architecture.get("output_modalities") or item.get("output_modalities") or []
            model_id = item["id"]
            model_text = str(item).lower()
            supports_vision = "image" in input_modalities or "vision" in model_text
            supports_text = not input_modalities or "text" in input_modalities
            outputs_text = not output_modalities or "text" in output_modalities
            non_chat_keywords = ("embedding", "moderation", "whisper", "tts", "dall-e", "image", "rerank")

            if any(keyword in model_id.lower() for keyword in non_chat_keywords):
                continue
            if require_vision and not supports_vision:
                continue
            if not require_vision and (supports_vision or not supports_text or not outputs_text):
                continue

            models.append({
                "id": model_id,
                "name": item.get("name") or model_id,
                "supports_vision": supports_vision,
            })

        models.sort(key=lambda model: (not model["supports_vision"], model["id"]))
        return models, None

    @staticmethod
    def fetch_url(url):
        """嘗試讀取 URL 內容，並處理權限問題"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 檢查是否為 Google 表單登入頁面 (通常代表無權限)
            if "ServiceLogin" in response.url or "docs.google.com/forms" not in url:
                if "docs.google.com" in response.url:
                    return None, "權限錯誤：此表單需要登入權限，請確認表單已開啟『知道連結的人皆可查看』，或改用下載檔案/貼上文字方式。"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # 簡單抓取表單標題與描述
            content = soup.get_text(separator='\n', strip=True)
            return content, None
        except requests.exceptions.ConnectionError:
            return None, "無法連線至該網址，請確認連結是否正確或網路是否正常。"
        except requests.exceptions.Timeout:
            return None, "讀取網頁逾時，對方伺服器回應過慢，請稍後再試。"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            return None, f"無法存取網頁（HTTP {status}），請確認連結是否有效或是否需要登入權限。"
        except Exception:
            return None, "讀取網頁時發生未預期的錯誤，請確認連結格式是否正確。"

    @staticmethod
    def call_ai(api_key, base_url, model, system_prompt, user_content, image_data_urls=None):
        """呼叫 AI API，回傳 (結果, 錯誤訊息) tuple。"""
        if not api_key or not api_key.strip():
            return None, "請先在左側側邊欄輸入 API Key。"
        if not base_url or not base_url.strip():
            return None, "請先在左側側邊欄輸入 OpenAI 相容 API Base URL。"

        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        user_message_content = user_content
        if image_data_urls:
            user_message_content = [{"type": "text", "text": user_content}]
            user_message_content.extend([
                {"type": "image_url", "image_url": {"url": image_url}}
                for image_url in image_data_urls
            ])

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message_content}
            ],
            "temperature": 0.35,
        }
        try:
            response = requests.post(
                f"{base_url.strip().rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
        except requests.exceptions.ConnectionError:
            return None, "無法連線至 AI 服務，請確認網路連線是否正常。"
        except requests.exceptions.Timeout:
            return None, "AI 服務回應逾時，請稍後再試。"
        except requests.exceptions.RequestException:
            return None, "送出請求時發生網路錯誤，請稍後再試。"

        status = response.status_code
        if status == 401:
            return None, "API Key 無效或已過期，請重新確認金鑰是否正確。"
        elif status == 402:
            return None, "API 帳戶額度不足，請前往服務商頁面儲值。"
        elif status == 403:
            return None, "沒有使用此模型的權限，請確認您的方案是否支援所選模型。"
        elif status == 404:
            return None, f"找不到模型「{model}」，請確認模型名稱是否正確或該模型是否仍在服務中。"
        elif status == 429:
            return None, "請求過於頻繁，已超過速率限制，請稍待片刻後再試。"
        elif status == 503:
            return None, "AI 服務目前暫時無法使用，請稍後再試。"
        elif not response.ok:
            return None, f"無法取得 AI 回應（HTTP {status}），請稍後再試或聯絡服務商。"

        try:
            content = response.json()['choices'][0]['message']['content']
            return content, None
        except (KeyError, IndexError, ValueError):
            return None, "AI 回傳的格式有誤，請確認所選模型是否支援對話功能。"
