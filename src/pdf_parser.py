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

def split_text_into_paragraphs_heuristic_v3(text):
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