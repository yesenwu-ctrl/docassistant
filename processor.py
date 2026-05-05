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
        except Exception as e:
            return None, f"❌ 無法讀取連結：{str(e)}"

    @staticmethod
    def call_ai(api_key, base_url, model, system_prompt, user_content):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']