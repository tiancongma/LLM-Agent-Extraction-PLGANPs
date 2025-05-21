from pypdf import PdfReader
import os

def extract_text_from_pdf(pdf_path):
    """
    从PDF文件中提取所有文本内容。
    """
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            extracted_page_text = page.extract_text()
            if extracted_page_text:
                text += extracted_page_text + "\n" # 每个页面后加一个换行符
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return None
    return text

# 改进的 split_text_into_paragraphs 示例
def split_text_into_paragraphs(text):
    if not text:
        return []

    # 尝试按行切分，并过滤掉空行
    lines = text.split('\n')
    processed_paragraphs = []
    current_paragraph = []

    for line in lines:
        stripped_line = line.strip()
        if stripped_line:
            # 假设非空行都属于当前段落
            current_paragraph.append(stripped_line)
        else:
            # 遇到空行，表示一个段落的结束
            if current_paragraph:
                processed_paragraphs.append(" ".join(current_paragraph))
                current_paragraph = [] # 重置，准备下一个段落

    # 处理最后一个段落（如果文件末尾没有空行）
    if current_paragraph:
        processed_paragraphs.append(" ".join(current_paragraph))

    # 过滤掉太短的段落，这些可能是页眉页脚的残余或不重要的单行文字
    # 但要注意，有些关键信息（如标题）也可能很短，需谨慎过滤
    # processed_paragraphs = [p for p in processed_paragraphs if len(p) > 30]

    return processed_paragraphs