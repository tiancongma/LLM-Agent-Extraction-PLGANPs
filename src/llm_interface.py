# src/llm_interface.py

import os
import json
import re
import google.generativeai as genai

# IMPORTANT: Remove these if they are still present from previous versions
# from dotenv import load_dotenv
# load_dotenv()

def initialize_gemini_model(model_name: str = "gemini-1.5-flash"): # <-- CHANGED DEFAULT MODEL HERE
    """
    Initializes and configures the Google Gemini model.

    Args:
        model_name (str): The specific Gemini model to use (e.g., "gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash").
                          The default is now "gemini-1.5-flash" for better compatibility.

    Returns:
        google.generativeai.GenerativeModel: The initialized Gemini model object.
    """
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment variables. "
            "Please ensure it's set in Colab Secrets and Notebook access is enabled."
        )

    genai.configure(api_key=api_key)
    print(f"[LLM Interface] Initializing Gemini model: {model_name}")
    
    # You can uncomment the following lines to list available models for debugging
    # for m in genai.list_models():
    #     if "generateContent" in m.supported_generation_methods:
    #         print(m.name)
    
    model = genai.GenerativeModel(model_name)
    return model

def call_llm_for_extraction(prompt: str, model_name: str = "gemini-1.5-flash") -> dict | None: # <-- CHANGED DEFAULT MODEL HERE TOO
    """
    Sends a constructed prompt to the Gemini LLM for information extraction
    and attempts to parse the JSON response.

    Args:
        prompt (str): The full prompt string prepared by prompt_builder.py.
        model_name (str): The specific Gemini model to use.

    Returns:
        dict | None: A dictionary containing the extracted data if successful and
                     valid JSON is returned, otherwise None.
    """
    model = initialize_gemini_model(model_name)

    try:
        print(f"[LLM Interface] Sending prompt (length: {len(prompt)} chars) to LLM...")
        # Use generate_content for single-turn conversations
        response = model.generate_content(prompt, stream=False) # stream=False waits for full response

        # Check for response safety attributes or other issues before accessing text
        if not response.candidates:
            print("[LLM Interface Error] LLM returned no candidates (possible safety filter or empty response).")
            # You might want to inspect response.prompt_feedback or response.candidates[0].safety_ratings here
            return None

        response_text = ""
        # Access the text from the response's first candidate
        if hasattr(response.candidates[0], 'text'):
            response_text = response.candidates[0].text
        elif hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
            # This is a more robust way to get text from parts, especially if it's structured
            response_text = "".join([part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')])

        if not response_text:
            print("[LLM Interface Error] LLM returned an empty text response from candidates.")
            return None

        print(f"[LLM Interface] LLM response received (length: {len(response_text)} chars).")

        # Attempt to parse the response as JSON
        json_match = re.search(r'```json\n(.*)\n```', response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(1).strip()
            print("[LLM Interface] Detected JSON markdown block.")
        else:
            json_string = response_text.strip()
            print("[LLM Interface] No JSON markdown block found. Attempting to parse raw response.")

        parsed_data = json.loads(json_string)
        print("[LLM Interface] LLM response successfully parsed as JSON.")
        return parsed_data

    except ValueError as e:
        print(f"[LLM Interface Error] API Key/Model Error: {e}. Please ensure your API key is correctly set and model name is valid.")
        return None
    except json.JSONDecodeError as e:
        print(f"[LLM Interface Error] Failed to parse LLM response as JSON: {e}")
        print(f"  Problematic response text (first 500 chars): {response_text[:500]}...")
        return None
    except Exception as e:
        print(f"[LLM Interface Error] An unexpected error occurred during LLM call: {e}")
        # The original error might be caught here if it's not a ValueError or JSONDecodeError
        print(f"  Response object (if available): {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        return None

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    test_prompt = """You are a helpful AI. Extract product and price from: The new SuperWidget 5000 is $199.99. Output as JSON."""
    print("--- Testing call_llm_for_extraction with a dummy prompt ---")
    try:
        extracted_product_info = call_llm_for_extraction(test_prompt)
        if extracted_product_info:
            print("\n--- Extracted Product Info ---")
            print(json.dumps(extracted_product_info, indent=2))
        else:
            print("\n--- Failed to extract product info ---")
    except Exception as e: print(f"Test error: {e}")

    test_prompt_complex = """You are a scientific information extractor. From the text, identify name and concentration of chemical. Output as JSON array. Text: Solution A contains NaCl at 0.9%. Solution B has glucose at 5%."""
    print("\n--- Testing call_llm_for_extraction with a complex dummy prompt ---")
    try:
        extracted_chemicals = call_llm_for_extraction(test_prompt_complex)
        if extracted_chemicals:
            print("\n--- Extracted Chemicals ---")
            print(json.dumps(extracted_chemicals, indent=2))
        else:
            print("\n--- Failed to extract chemicals ---")
    except Exception as e: print(f"Test error: {e}")