# pdf_parser.py 内容示例

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

def split_text_into_paragraphs(text):
    """
    将提取的文本按双换行符分割成段落。
    """
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs

if __name__ == '__main__':
    # 这是一个简单的测试，在 Colab 中通常不直接运行这个。
    # 更建议在 Notebook 主单元格中导入和测试。
    print("This is pdf_parser.py module.")
    # 假设你有一个PDF文件在 'data/raw_pdfs/' 目录下
    # pdf_example_path = 'data/raw_pdfs/sample.pdf'
    # if os.path.exists(pdf_example_path):
    #     content = extract_text_from_pdf(pdf_example_path)
    #     if content:
    #         print("Extracted text sample:", content[:500])
    #         paragraphs = split_text_into_paragraphs(content)
    #         print(f"Total paragraphs: {len(paragraphs)}")
    # else:
    #     print(f"Test PDF not found at {pdf_example_path}")