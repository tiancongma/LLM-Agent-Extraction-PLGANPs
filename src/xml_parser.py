from lxml import etree
import os
import re # Used for regular expressions, specifically for cleaning and reference removal

# --- Helper Function: To be called internally by extract_from_xml ---
def _remove_references_from_paragraphs(paragraphs: list) -> list:
    """
    Helper function: Filters out paragraphs that belong to the references,
    acknowledgements, or appendix sections.

    This function assumes it receives a list of cleaned paragraph strings
    extracted from the XML body. It identifies section headers like
    "References", "Acknowledgements", etc., and removes all subsequent paragraphs.

    Args:
        paragraphs (list): A list of strings, where each string is a paragraph.

    Returns:
        list: A filtered list of paragraphs, with reference/appendix sections removed.
    """
    if not paragraphs:
        return []

    # Common section titles that typically mark the end of main content
    # and the beginning of ancillary sections like References, Appendices, etc.
    # Using regex to match these as whole lines, case-insensitively.
    reference_section_patterns = [
        r'^\s*References?\s*$',
        r'^\s*BIBLIOGRAPHY\s*$',
        r'^\s*LITERATURE\s+CITED\s*$',
        r'^\s*Acknowledgement(s)?\s*$',
        r'^\s*Appendix(es)?\s*$',
        r'^\s*SUPPORTING\s+INFORMATION\s*$',
        r'^\s*SUPPLEMENTARY\s+MATERIALS?\s*$',
        r'^\s*Note(s)?\s+on\s+Contributor(s)?\s*$',
        r'^\s*AUTHOR\s+CONTRIBUTIONS?\s*$',
        r'^\s*FUNDING\s*$',
        r'^\s*CONFLICTS?\s+OF\s+INTEREST\s*$',
        r'^\s*DATA\s+AVAILABILITY\s+STATEMENT\s*$',
        r'^\s*ORCID\s*$',
    ]

    in_ancillary_section = False  # Flag to track if we've entered a section to be removed
    processed_paragraphs = []     # List to store paragraphs that are kept

    for p in paragraphs:
        # Check if the current paragraph matches any known ancillary section header
        is_ancillary_header = any(re.fullmatch(pattern, p, re.IGNORECASE) for pattern in reference_section_patterns)

        if is_ancillary_header:
            in_ancillary_section = True
            # print(f"  [Parser Debug] Detected ancillary section start: '{p[:50]}...'") # For debugging
            continue # Do not include the header itself

        if in_ancillary_section:
            # print(f"  [Parser Debug] Skipping paragraph in ancillary section: '{p[:50]}...'") # For debugging
            continue # If we're in an ancillary section, skip this paragraph

        # If not in an ancillary section, add the paragraph
        processed_paragraphs.append(p)

    # Final cleanup: Remove very short paragraphs that might be noise
    # (e.g., stray single words, page numbers, or leftover section numbers)
    # Threshold (20 chars) and excluding pure numbers. Adjust as needed.
    final_cleaned_paragraphs = [
        p for p in processed_paragraphs
        if len(p) > 20 and not re.fullmatch(r'^\s*\d+\.?\s*$', p.strip()) # Exclude lines that are just numbers/section numbers
    ]

    return final_cleaned_paragraphs


def extract_from_xml(xml_file_path: str) -> dict | None:
    """
    Extracts common literary information from an XML file, including title, authors,
    abstract, keywords, and body paragraphs. It attempts to remove reference/ancillary
    sections and to extract table data into a text-friendly format for the LLM.

    XPath expressions might need adjustment based on the actual XML structure (JATS vs. custom).

    Args:
        xml_file_path (str): The path to the XML file.

    Returns:
        dict | None: A dictionary containing the extracted information if successful,
                     otherwise None.
    """
    extracted_data = {
        'file_path': xml_file_path, # Add file path for reference
        'title': None,
        'authors': [],
        'abstract': None,
        'keywords': [],
        'body_paragraphs': [],  # Main text paragraphs (references removed)
        'tables_data': []       # List of dictionaries, each containing table ID, caption, and markdown data
    }

    try:
        tree = etree.parse(xml_file_path)
        root = tree.getroot()

        # --- 1. Extract Article Title ---
        title_element_text = root.xpath('//article-title/text()')
        if not title_element_text:
            title_element_text = root.xpath('//title/text()') # Fallback for generic <title>
        if title_element_text:
            extracted_data['title'] = title_element_text[0].strip()

        # --- 2. Extract Authors ---
        authors_elements = root.xpath('//contrib[@contrib-type="author"]/name')
        if not authors_elements:
            authors_elements = root.xpath('//author') # Fallback for simpler structures

        for author_elem in authors_elements:
            surname = author_elem.xpath('./surname/text()')
            given_names = author_elem.xpath('./given-names/text()')
            if surname and given_names:
                extracted_data['authors'].append(f"{given_names[0].strip()} {surname[0].strip()}")
            elif author_elem.text:
                extracted_data['authors'].append(author_elem.text.strip())

        # --- 3. Extract Abstract ---
        abstract_elements = root.xpath('//abstract//p/text()')
        if not abstract_elements:
            abstract_elements = root.xpath('//abstract/text()') # Fallback
        if abstract_elements:
            extracted_data['abstract'] = " ".join([re.sub(r'\s+', ' ', a).strip() for a in abstract_elements if a.strip()])

        # --- 4. Extract Keywords ---
        keyword_elements = root.xpath('//kwd-group/kwd/text()')
        if keyword_elements:
            extracted_data['keywords'] = [k.strip() for k in keyword_elements]

        # --- 5. Extract Body Paragraphs (and remove ancillary sections like References) ---
        # Get all <p> tags within the <body>.
        # This XPath is a common strategy for JATS: it selects <p> inside <body>
        # but *excludes* those that are descendants of <ref-list> (reference list).
        raw_body_p_elements_text = root.xpath('//body//p[not(ancestor::ref-list)]/text()')

        # If the above XPath doesn't yield results (e.g., non-JATS XML, or ref-list not defined),
        # fall back to getting all p tags from body and rely more on keyword-based removal.
        if not raw_body_p_elements_text:
             raw_body_p_elements_text = root.xpath('//body//p/text()')
             # print("  [Parser Warning] Precise XPath for body paragraphs (excluding refs) failed. Falling back to all body p tags.")

        # Clean and prepare paragraphs before feeding to the reference remover
        cleaned_raw_paragraphs = [re.sub(r'\s+', ' ', p_text).strip() for p_text in raw_body_p_elements_text if p_text.strip()]

        # Apply the helper function to remove references and other ancillary sections
        extracted_data['body_paragraphs'] = _remove_references_from_paragraphs(cleaned_raw_paragraphs)


        # --- 6. Extract Table Data ---
        # This section is crucial for structured data.
        # It's an example, and you might need to adjust XPaths for your specific XML table structures.
        table_wraps = root.xpath('//table-wrap') # Common JATS tag for a table container

        for tw in table_wraps:
            table_id = tw.xpath('./@id')[0] if tw.xpath('./@id') else 'N/A'
            table_caption = " ".join(tw.xpath('./caption//p/text()')).strip() if tw.xpath('./caption//p/text()') else ''
            
            # --- Attempt to extract table content into a list of lists (rows and cells) ---
            # This is a common structure that can then be converted to a Markdown table or Pandas DataFrame
            table_content_rows = []
            
            # Try to get header rows first if available (<thead>/<tr>/<td>)
            header_rows = tw.xpath('.//thead/tr')
            for h_row in header_rows:
                cells = h_row.xpath('.//td/text() | .//th/text()') # Get text from <td> or <th>
                table_content_rows.append([c.strip() for c in cells])

            # Then get body rows (<tbody>/<tr>/<td>)
            body_rows = tw.xpath('.//tbody/tr') # Assuming standard HTML-like table structure within XML
            for b_row in body_rows:
                cells = b_row.xpath('.//td/text() | .//th/text()') # Get text from <td> or <th>
                table_content_rows.append([c.strip() for c in cells])
            
            # If a table was found and data extracted, convert to a text format for LLM
            if table_content_rows:
                markdown_table_text = ""
                if table_content_rows:
                    # Header row
                    markdown_table_text += "| " + " | ".join(table_content_rows[0]) + " |\n"
                    # Separator line
                    # Adjust separator length based on header cell content
                    markdown_table_text += "|-" + "-|-".join(["-" * len(col) for col in table_content_rows[0]]) + "-|\n"
                    # Data rows
                    for row in table_content_rows[1:]:
                        markdown_table_text += "| " + " | ".join(row) + " |\n"


                extracted_data['tables_data'].append({
                    'id': table_id,
                    'caption': table_caption,
                    'data_rows': table_content_rows, # Store raw rows for potential later use
                    'text_representation': markdown_table_text # This is what you'll feed to LLM
                })
        

    except etree.XMLSyntaxError as e:
        print(f"  [Parser Error] XML syntax error in {xml_file_path}: {e}")
        return None
    except Exception as e:
        print(f"  [Parser Error] An unexpected error occurred processing {xml_file_path}: {e}")
        return None

    return extracted_data


# --- Testing Block (Only runs if the script is executed directly) ---
if __name__ == '__main__':
    # Define a sample XML content that simulates a scientific article with references and tables
    # This content includes: Title, Authors, Abstract, Keywords, Body, a Table, and References section.
    sample_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<article dtd-version="1.1d3" xml:lang="en">
    <front>
        <article-meta>
            <title-group>
                <article-title>Advanced PLGA Nanoparticles for Targeted Drug Delivery: Synthesis and Characterization</article-title>
            </title-group>
            <contrib-group>
                <contrib contrib-type="author"><name><surname>Chen</surname><given-names>Li</given-names></name></contrib>
                <contrib contrib-type="author"><name><surname>Wang</surname><given-names>Jian</given-names></name></contrib>
            </contrib-group>
            <abstract>
                <p>This study focuses on the synthesis and characterization of PLGA nanoparticles (MW 60 kDa, LA:GA 50:50) for targeted drug delivery. The particles were prepared via nanoprecipitation, yielding a size of 180 nm and a zeta potential of -22 mV. Encapsulation efficiency for DrugX was 90%.</p>
                <p>The method involved dissolving PLGA in acetone and adding it dropwise to an aqueous phase containing PVA (0.5%).</p>
            </abstract>
            <kwd-group>
                <kwd>PLGA</kwd><kwd>Nanoparticles</kwd><kwd>Drug delivery</kwd><kwd>Nanoprecipitation</kwd>
            </kwd-group>
        </article-meta>
    </front>
    <body>
        <sec id="s1" sec-type="intro"><title>1. Introduction</title>
            <p>Nanotechnology offers novel approaches for drug delivery. PLGA polymers are widely used due to their biocompatibility.</p>
        </sec>
        <sec id="s2" sec-type="methods"><title>2. Materials and Methods</title>
            <p>PLGA (MW 60 kDa, 50:50 LA:GA ratio, Sigma-Aldrich) was dissolved in 5 mL acetone at 10 mg/mL. DrugX (5 mg) was dispersed in this organic phase. The mixture was added dropwise to 20 mL of 0.5% (w/v) PVA solution in water under magnetic stirring (700 rpm, 2 hours, 25 °C). Sonication was not used in this primary step.</p>
            <table-wrap id="T1">
                <caption><p>Table 1. Physicochemical Properties of PLGA Nanoparticles</p></caption>
                <table>
                    <thead>
                        <tr>
                            <th>Property</th>
                            <th>Value</th>
                            <th>Unit</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Particle Size (DLS)</td>
                            <td>180</td>
                            <td>nm</td>
                        </tr>
                        <tr>
                            <td>PDI</td>
                            <td>0.12</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td>Zeta Potential</td>
                            <td>-22</td>
                            <td>mV</td>
                        </tr>
                        <tr>
                            <td>Encapsulation Eff.</td>
                            <td>90</td>
                            <td>%</td>
                        </tr>
                    </tbody>
                </table>
            </table-wrap>
            <p>Drug loading content was found to be 10% (w/w).</p>
        </sec>
        <sec id="s3" sec-type="results"><title>3. Results and Discussion</title>
            <p>The synthesized nanoparticles showed a narrow size distribution. The high encapsulation efficiency indicates suitability for drug loading.</p>
            <p>Drug release studies confirmed sustained release over 7 days.</p>
        </sec>
        <sec id="s4" sec-type="acknowledgements"><title>Acknowledgements</title>
            <p>The authors thank funding agency X for support.</p>
        </sec>
    </body>
    <back>
        <ref-list>
            <ref id="B1"><label>1.</label><mixed-citation>Author A. et al., J. Science, 2020.</mixed-citation></ref>
            <ref id="B2"><label>2.</label><mixed-citation>Author B. et al., J. Research, 2021.</mixed-citation></ref>
            <ref id="B3"><label>3.</label><mixed-citation>Author C. et al., J. Discovery, 2022.</mixed-citation></ref>
        </ref-list>
        <app-group>
            <app id="app1"><label>Appendix A</label>
                <p>Supplementary materials and methods are provided.</p>
            </app>
        </app-group>
    </back>
</article>
"""
    # Create directory if it doesn't exist
    xml_dir = 'data/raw_xmls'
    os.makedirs(xml_dir, exist_ok=True)
    test_xml_path = os.path.join(xml_dir, 'sample_article.xml')

    with open(test_xml_path, 'w', encoding='utf-8') as f:
        f.write(sample_xml_content)

    print(f"Sample XML created at: {test_xml_path}")

    # Call the extraction function
    extracted = extract_from_xml(test_xml_path)

    if extracted:
        print("\n--- Extracted Data Summary from Sample XML ---")
        for key, value in extracted.items():
            if key == 'body_paragraphs':
                print(f"{key}: {len(value)} paragraphs")
                # Print last 5 paragraphs to check reference removal
                print(f"  Last {min(5, len(value))} Body Paragraphs:")
                for i, p in enumerate(value[-min(5, len(value)):]):
                    print(f"    - {p[:150]}...") # Print first 150 chars
            elif key == 'tables_data':
                print(f"{key}: {len(value)} tables found.")
                for table_info in value:
                    print(f"  Table ID: {table_info.get('id', 'N/A')}, Caption: {table_info.get('caption', 'N/A')}")
                    # Print text representation of the table for LLM check
                    print("  Table Text Representation (for LLM):")
                    print(table_info.get('text_representation', 'N/A'))
            elif isinstance(value, list):
                print(f"{key}: {'; '.join(value)}")
            else:
                print(f"{key}: {value}")
    else:
        print("XML extraction failed.")