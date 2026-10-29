"""
检查报告解读链：上传的报告文本 → 专业解读 + 建议，并自动归档进知识库。
"""
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from core.prompts import REPORT_PROMPT
from twin.records import save_report


class ReportReaderChain:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.chain = REPORT_PROMPT | llm | StrOutputParser()

    def analyze(self, content: str, filename: str = "粘贴的报告文本") -> str:
        return self.chain.invoke({
            "content": content[:8000],
            "filename": filename,
        })

    def analyze_and_save(self, content: str, filename: str) -> dict:
        analysis = self.analyze(content, filename)
        rep = save_report(filename, content, analysis)
        return {"analysis": analysis, "meta": rep}


def extract_pdf_text(pdf_file) -> Optional[str]:
    """用 pypdf 抽取 PDF 文本（扫描件无法抽取时返回 None，提示用户粘贴文本）。"""
    try:
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_file.getvalue()))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
        if not pages:
            return None
        return "\n".join(pages)
    except Exception:
        return None
