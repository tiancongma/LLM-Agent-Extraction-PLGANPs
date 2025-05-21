from pypdf import PdfReader
import os
import re

def extract_text_from_pdf(pdf_path):
    """
    从PDF文件中提取所有文本内容。
    (Keep your existing extract_text_from_pdf function, or update to PyMuPDF if it helps)
    """
    # Assuming you are using pypdf for simplicity here.
    # If you switched to PyMuPDF, ensure this function reflects that.
    from pypdf import PdfReader
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            extracted_page_text = page.extract_text()
            if extracted_page_text:
                text += extracted_page_text + "\n" # Adding single newline after each page, common for pypdf
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return None
    return text

def split_text_into_paragraphs(text):
    """
    智能地将文本分割成段落，使用多种启发式规则。
    适用于单换行符 \n 同时代表行内换行和段落换行的情况。
    """
    if not text:
        return []

    # 1. Standardize newlines and split into individual lines
    lines = text.replace('\r\n', '\n').split('\n')

    paragraphs = []
    current_paragraph_lines = []

    # Common sentence ending punctuation
    sentence_enders = ['.', '?', '!']

    for i, line in enumerate(lines):
        stripped_line = line.strip()

        # Rule 1: Empty line signals a new paragraph
        if not stripped_line:
            if current_paragraph_lines: # If there's content in the current paragraph
                paragraphs.append(" ".join(current_paragraph_lines))
                current_paragraph_lines = [] # Reset for next paragraph
            continue # Move to the next line

        # Add the current line to the current paragraph
        current_paragraph_lines.append(stripped_line)

        # Rule 2: Heuristic for end of sentence + start of new line (likely a new paragraph)
        # This is the trickiest part for scientific texts.
        # Check if the line ends with common sentence-ending punctuation
        # AND if the next line exists and starts with an uppercase letter or number (new sentence/heading)
        if i < len(lines) - 1: # Check if it's not the last line
            next_line = lines[i+1].strip()
            # If the current line ends with a sentence terminator
            if stripped_line and stripped_line[-1] in sentence_enders:
                # And the next line exists and starts with an uppercase letter or a digit (common for headings/new sentences)
                if next_line and (next_line[0].isupper() or next_line[0].isdigit() or next_line.lower().startswith(('fig.', 'table'))):
                    # We found a strong candidate for a paragraph break
                    if current_paragraph_lines:
                        paragraphs.append(" ".join(current_paragraph_lines))
                        current_paragraph_lines = []
                        continue # Move to next line (which starts a new paragraph)
            
            # Rule 3: Handling cases where line wraps within a paragraph (e.g., multi-column, no sentence ender)
            # If current line does NOT end with a sentence ender, AND next line does NOT start with uppercase,
            # it's likely a line wrap within the same paragraph.
            # We already appended it. We just *don't* force a paragraph break here.

    # Add the last paragraph (if any content remains)
    if current_paragraph_lines:
        paragraphs.append(" ".join(current_paragraph_lines))

    # Final Cleaning: Remove very short paragraphs that might be noise (e.g., page numbers, single words)
    # Be cautious not to remove valid short sentences or titles.
    cleaned_paragraphs = []
    for p in paragraphs:
        # Remove empty or extremely short paragraphs
        if len(p) < 10: # Adjust threshold as needed
            continue
        # Remove lines that are only numbers (likely page numbers)
        if re.fullmatch(r'\d+', p):
            continue
        # Remove common headers/footers if they slipped through (customize as needed)
        # if "Journal of" in p or "Copyright" in p:
        #     continue

        # Replace multiple spaces with a single space (from joining lines)
        cleaned_paragraphs.append(re.sub(r'\s+', ' ', p).strip())

    return cleaned_paragraphs
# 在你的 src/pdf_parser.py 文件中添加或修改一个函数

def remove_references_section(text):
    """
    尝试从文本末尾移除参考文献部分。
    """
    if not text:
        return ""

    # 常见参考文献标题的正则表达式模式（不区分大小写，可能前面有数字或空格）
    # 使用 \b 确保是整个单词匹配，避免匹配到其他地方的 "reference"
    # 使用 re.IGNORECASE 忽略大小写
    reference_patterns = [
        r'\bReferences?\b',          # "References", "Reference"
        r'\bBIBLIOGRAPHY\b',         # "BIBLIOGRAPHY"
        r'\bLITERATURE\s+CITED\b',   # "LITERATURE CITED"
        r'\bAcknowledgement(s)?\b',  # 有些文献References前会有致谢
        r'\bAppendix(es)?\b',        # 附录通常也在最后
        r'\bSUPPORTING\s+INFORMATION\b', # 某些期刊的补充信息
        r'\bSUPPLEMENTARY\s+MATERIALS?\b', # 补充材料
    ]

    # 将所有模式组合成一个大的正则表达式，并编译以提高效率
    combined_pattern = re.compile(r'|'.join(reference_patterns), re.IGNORECASE)

    # 从文本末尾开始向前查找，或者直接从头开始查找第一个匹配
    # 因为 References 通常在文档的末尾，我们假设找到的第一个匹配就是它
    match = combined_pattern.search(text)

    if match:
        # 如果找到匹配，截断文本到匹配开始的位置
        print(f"--- INFO: Identified and removing references section starting at index {match.start()} ---")
        return text[:match.start()].strip()
    else:
        # 如果没有找到，返回原始文本
        print("--- INFO: No explicit references section header found to remove. ---")
        return text.strip()