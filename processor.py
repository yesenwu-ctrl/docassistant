import io
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
        return "\n".join([page.extract_text() for page in reader.pages])

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
                    return None, "🔒 權限錯誤：此表單需要登入權限，請確認表單已開啟『知道連結的人皆可查看』，或改用下載檔案/貼上文字方式。"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # 簡單抓取表單標題與描述
            content = soup.get_text(separator='\n', strip=True)
            return content, None
        except requests.exceptions.ConnectionError:
            return None, "❌ 無法連線至該網址，請確認連結是否正確或網路是否正常。"
        except requests.exceptions.Timeout:
            return None, "❌ 讀取網頁逾時，對方伺服器回應過慢，請稍後再試。"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            return None, f"❌ 無法存取網頁（HTTP {status}），請確認連結是否有效或是否需要登入權限。"
        except Exception:
            return None, "❌ 讀取網頁時發生未預期的錯誤，請確認連結格式是否正確。"

    @staticmethod
    def call_ai(api_key, base_url, model, system_prompt, user_content):
        """呼叫 AI API，回傳 (結果, 錯誤訊息) tuple。"""
        if not api_key or not api_key.strip():
            return None, "❌ 請先在左側側邊欄輸入 API Key。"

        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
        except requests.exceptions.ConnectionError:
            return None, "❌ 無法連線至 AI 服務，請確認網路連線是否正常。"
        except requests.exceptions.Timeout:
            return None, "❌ AI 服務回應逾時，請稍後再試。"
        except requests.exceptions.RequestException:
            return None, "❌ 送出請求時發生網路錯誤，請稍後再試。"

        status = response.status_code
        if status == 401:
            return None, "❌ API Key 無效或已過期，請重新確認金鑰是否正確。"
        elif status == 402:
            return None, "❌ API 帳戶額度不足，請前往服務商頁面儲值。"
        elif status == 403:
            return None, "❌ 沒有使用此模型的權限，請確認您的方案是否支援所選模型。"
        elif status == 404:
            return None, f"❌ 找不到模型「{model}」，請確認模型名稱是否正確或該模型是否仍在服務中。"
        elif status == 429:
            return None, "❌ 請求過於頻繁，已超過速率限制，請稍待片刻後再試。"
        elif status == 503:
            return None, "❌ AI 服務目前暫時無法使用，請稍後再試。"
        elif not response.ok:
            return None, f"❌ 無法取得 AI 回應（HTTP {status}），請稍後再試或聯絡服務商。"

        try:
            content = response.json()['choices'][0]['message']['content']
            return content, None
        except (KeyError, IndexError, ValueError):
            return None, "❌ AI 回傳的格式有誤，請確認所選模型是否支援對話功能。"