# src/xml_parser.py

from lxml import etree
import os
import re

# --- Helper Function: _remove_references_from_paragraphs (保持不变) ---
def _remove_references_from_paragraphs(paragraphs: list) -> list:
    """
    Helper function: Filters out paragraphs that belong to the references,
    acknowledgements, or appendix sections.
    ... (函数内容保持不变) ...
    """
    if not paragraphs:
        return []
    reference_section_patterns = [
        r'^\s*References?\s*$', r'^\s*BIBLIOGRAPHY\s*$', r'^\s*LITERATURE\s+CITED\s*$',
        r'^\s*Acknowledgement(s)?\s*$', r'^\s*Appendix(es)?\s*$', r'^\s*SUPPORTING\s+INFORMATION\s*$',
        r'^\s*SUPPLEMENTARY\s+MATERIALS?\s*$', r'^\s*Note(s)?\s+on\s+Contributor(s)?\s*$',
        r'^\s*AUTHOR\s+CONTRIBUTIONS?\s*$', r'^\s*FUNDING\s*$', r'^\s*CONFLICTS?\s+OF\s+INTEREST\s*$',
        r'^\s*DATA\s+AVAILABILITY\s+STATEMENT\s*$', r'^\s*ORCID\s*$',
    ]
    in_ancillary_section = False
    processed_paragraphs = []
    for p in paragraphs:
        is_ancillary_header = any(re.fullmatch(pattern, p, re.IGNORECASE) for pattern in reference_section_patterns)
        if is_ancillary_header:
            in_ancillary_section = True
            continue
        if in_ancillary_section:
            continue
        processed_paragraphs.append(p)
    final_cleaned_paragraphs = [
        p for p in processed_paragraphs
        if len(p) > 20 and not re.fullmatch(r'^\s*\d+\.?\s*$', p.strip())
    ]
    return final_cleaned_paragraphs


def extract_from_xml(xml_file_path: str) -> dict | None:
    """
    Extracts common literary information from an XML file, including title, authors,
    abstract, keywords, and body paragraphs. It attempts to remove reference/ancillary
    sections and to extract table data into a text-friendly format for the LLM.
    Crucially, it now also aims to identify and extract content for specific sections.

    XPath expressions might need adjustment based on the actual XML structure (JATS vs. custom).

    Args:
        xml_file_path (str): The path to the XML file.

    Returns:
        dict | None: A dictionary containing the extracted information if successful,
                     otherwise None.
    """
    extracted_data = {
        'file_path': xml_file_path,
        'title': None,
        'authors': [],
        'abstract': None,
        'keywords': [],
        'body_paragraphs': [],  # Main text paragraphs (flattened, references removed)
        'sections': [],         # New: Structured list of sections (title, content)
        'tables_data': []       # List of dictionaries, each containing table ID, caption, and markdown data
    }

    try:
        tree = etree.parse(xml_file_path)
        root = tree.getroot()

        # --- 1. Extract Article Title ---
        title_element_text = root.xpath('//article-title/text()')
        if not title_element_text:
            title_element_text = root.xpath('//title/text()')
        if title_element_text:
            extracted_data['title'] = title_element_text[0].strip()

        # --- 2. Extract Authors ---
        authors_elements = root.xpath('//contrib[@contrib-type="author"]/name')
        if not authors_elements:
            authors_elements = root.xpath('//author')
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
            abstract_elements = root.xpath('//abstract/text()')
        if abstract_elements:
            extracted_data['abstract'] = " ".join([re.sub(r'\s+', ' ', a).strip() for a in abstract_elements if a.strip()])

        # --- 4. Extract Keywords ---
        keyword_elements = root.xpath('//kwd-group/kwd/text()')
        if keyword_elements:
            extracted_data['keywords'] = [k.strip() for k in keyword_elements]

        # --- 5. Extract Body Sections and Paragraphs (with Ancillary Removal) ---
        # Get all <sec> elements within <body>. These usually represent sections like Intro, Methods, Results.
        sections = root.xpath('//body//sec') # Common for JATS XML to use <sec> tags for sections

        all_body_paragraphs_flat_list = [] # To keep a flat list of all body paragraphs (excluding refs)

        for sec_element in sections:
            section_title_element = sec_element.xpath('./title/text()') # Get title of the section
            section_title = section_title_element[0].strip() if section_title_element else "Untitled Section"

            # Get all <p> tags within this specific section, excluding those in ref-lists
            # This XPath ensures we only get paragraphs belonging to this section, not nested ones from other sections
            section_paragraphs_text = sec_element.xpath('.//p[not(ancestor::ref-list)]/text()')
            
            # Clean paragraphs
            cleaned_section_paragraphs = [re.sub(r'\s+', ' ', p_text).strip() for p_text in section_paragraphs_text if p_text.strip()]
            
            # Filter out ancillary sections (like acknowledgements, appendix, references)
            # Apply _remove_references_from_paragraphs to the *full set* of paragraphs
            # after collecting them, to ensure a global removal based on headers.
            # However, for structured sections, we want to keep the current section's content.
            # We'll rely on the _remove_references_from_paragraphs to work on the *flattened* list later.
            
            # Append paragraphs to the flat list
            all_body_paragraphs_flat_list.extend(cleaned_section_paragraphs)

            # Store section data
            if cleaned_section_paragraphs: # Only add section if it has content
                extracted_data['sections'].append({
                    'title': section_title,
                    'paragraphs': cleaned_section_paragraphs,
                    'content_flat': " ".join(cleaned_section_paragraphs) # Merged content for easier access
                })
        
        # After collecting all sections and their paragraphs, apply global reference removal
        extracted_data['body_paragraphs'] = _remove_references_from_paragraphs(all_body_paragraphs_flat_list)


        # --- 6. Extract Table Data ---
        table_wraps = root.xpath('//table-wrap')

        for tw in table_wraps:
            table_id = tw.xpath('./@id')[0] if tw.xpath('./@id') else 'N/A'
            table_caption = " ".join(tw.xpath('./caption//p/text()')).strip() if tw.xpath('./caption//p/text()') else ''
            
            table_content_rows = []
            
            header_rows = tw.xpath('.//thead/tr')
            for h_row in header_rows:
                cells = h_row.xpath('.//td/text() | .//th/text()')
                table_content_rows.append([c.strip() for c in cells])

            body_rows = tw.xpath('.//tbody/tr')
            for b_row in body_rows:
                cells = b_row.xpath('.//td/text() | .//th/text()')
                table_content_rows.append([c.strip() for c in cells])
            
            if table_content_rows:
                markdown_table_text = ""
                if table_content_rows:
                    markdown_table_text += "| " + " | ".join(table_content_rows[0]) + " |\n"
                    markdown_table_text += "|-" + "-|-".join(["-" * max(3, len(col)) for col in table_content_rows[0]]) + "-|\n"
                    for row in table_content_rows[1:]:
                        markdown_table_text += "| " + " | ".join(row) + " |\n"

                extracted_data['tables_data'].append({
                    'id': table_id,
                    'caption': table_caption,
                    'data_rows': table_content_rows,
                    'text_representation': markdown_table_text
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
    # Define a sample XML content (unchanged, as it's a good test case for sections)
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
    test_xml_path = os.path.join(xml_dir, 'sample_article_for_parser_test.xml') # Changed filename for clarity

    with open(test_xml_path, 'w', encoding='utf-8') as f:
        f.write(sample_xml_content)

    print(f"Sample XML created at: {test_xml_path}")

    # Call the extraction function
    extracted = extract_from_xml(test_xml_path)

    if extracted:
        print("\n--- Extracted Data Summary from Sample XML ---")
        for key, value in extracted.items():
            if key == 'body_paragraphs':
                print(f"{key}: {len(value)} paragraphs (flat list, references removed)")
                print(f"  Last {min(5, len(value))} Body Paragraphs:")
                for i, p in enumerate(value[-min(5, len(value)):]):
                    print(f"    - {p[:150]}...")
            elif key == 'sections':
                print(f"{key}: {len(value)} sections found (structured)")
                for sec in value[:3]: # Print first 3 sections
                    print(f"  - Section Title: '{sec.get('title', 'N/A')}'")
                    print(f"    Paragraphs: {len(sec.get('paragraphs', []))}")
                    print(f"    Content (flat): {sec.get('content_flat', '')[:100]}...")
            elif key == 'tables_data':
                print(f"{key}: {len(value)} tables found.")
                for table_info in value:
                    print(f"  Table ID: {table_info.get('id', 'N/A')}, Caption: {table_info.get('caption', 'N/A')[:50]}...")
                    print("  Table Text Representation (for LLM):")
                    print(table_info.get('text_representation', 'N/A'))
            elif isinstance(value, list):
                print(f"{key}: {'; '.join(value)}")
            else:
                print(f"{key}: {value}")
    else:
        print("XML extraction failed.")