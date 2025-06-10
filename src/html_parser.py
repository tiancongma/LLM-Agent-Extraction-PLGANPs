from bs4 import BeautifulSoup
import os

def extract_content_from_html(html_file_path):
    """
    Reads an HTML file and extracts main text content.
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # --- Example Strategy 1: Extract all paragraph text ---
        paragraphs = []
        for p_tag in soup.find_all('p'):
            text = p_tag.get_text(separator=' ', strip=True) # Use separator to handle line breaks within <p>
            if text:
                paragraphs.append(text)

        # --- Example Strategy 2: Extract text from specific article body tags (e.g., common for journals) ---
        # Look for common article body containers (these will vary by publisher)
        # E.g., <div class="article-body">, <article>
        article_body_tag = soup.find('div', class_='article-body') or soup.find('article')
        if article_body_tag:
            # Get all text from within the main article body, or specifically target <p> tags within it
            body_paragraphs = [p.get_text(separator=' ', strip=True) for p in article_body_tag.find_all('p') if p.get_text(strip=True)]
            # You might also want to extract headings, lists etc.
            return body_paragraphs

        # If specific tags are not found, fallback to general paragraph extraction
        return paragraphs

    except Exception as e:
        print(f"Error extracting content from {html_file_path}: {e}")
        return []

def extract_tables_from_html(html_file_path):
    """
    Reads an HTML file and extracts tables into pandas DataFrames.
    """
    try:
        import pandas as pd # pandas is excellent for HTML tables
        tables = pd.read_html(html_file_path) # Returns a list of DataFrames
        return tables
    except Exception as e:
        print(f"Error extracting tables from {html_file_path}: {e}")
        return []

# Example of how you would use it in your Colab notebook:
# !pip install beautifulsoup4 pandas # Install necessary libraries

# from src.html_parser import extract_content_from_html, extract_tables_from_html

# html_file_path = 'data/raw_htmls/sample_article.html' # Assuming you put HTML files here

# paragraphs = extract_content_from_html(html_file_path)
# print(f"Extracted {len(paragraphs)} paragraphs from HTML.")
# for p in paragraphs[:3]:
#     print(p[:200])

# tables_df_list = extract_tables_from_html(html_file_path)
# if tables_df_list:
#     print(f"Extracted {len(tables_df_list)} tables.")
#     print("First table head:")
#     print(tables_df_list[0].head())