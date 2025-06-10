# src/llm_interface.py

import os
import json
import google.generativeai as genai # The Google Gemini API library

# This is crucial for securely loading your Gemini API key

def initialize_gemini_model(model_name: str = "gemini-pro"):
    """
    Initializes and configures the Google Gemini model.

    Args:
        model_name (str): The specific Gemini model to use (e.g., "gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash").

    Returns:
        google.generativeai.GenerativeModel: The initialized Gemini model object.
    """
    # Get the API key from environment variables
    # IMPORTANT: Ensure your .env file is in your repository root
    # and contains GEMINI_API_KEY="YOUR_API_KEY_HERE"
    # Also, ensure .env is in your .gitignore!
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables. "
                         "Please set it in a .env file or your Colab Secrets.")

    genai.configure(api_key=api_key)
    print(f"[LLM Interface] Initializing Gemini model: {model_name}")
    model = genai.GenerativeModel(model_name)
    return model

def call_llm_for_extraction(prompt: str, model_name: str = "gemini-pro") -> dict | None:
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
    model = initialize_gemini_model(model_name) # Initialize model for each call (or pass initialized model)

    try:
        # Generate content from the model
        print(f"[LLM Interface] Sending prompt (length: {len(prompt)} chars) to LLM...")
        # Use generate_content for single-turn conversations
        response = model.generate_content(prompt, stream=False) # stream=False waits for full response

        # Access the text from the response
        # Gemini responses might be structured with parts
        response_text = ""
        if hasattr(response, 'text'):
            response_text = response.text
        elif hasattr(response, 'parts') and response.parts:
            # If parts is a list of text parts
            response_text = "".join([part.text for part in response.parts if hasattr(part, 'text')])

        if not response_text:
            print("[LLM Interface Error] LLM returned an empty response.")
            return None

        print(f"[LLM Interface] LLM response received (length: {len(response_text)} chars).")
        # print(f"Raw LLM response: {response_text[:500]}...") # For debugging

        # Attempt to parse the response as JSON
        # LLM might include markdown fences (```json...```)
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
        print(f"[LLM Interface Error] API Key Error: {e}. Please ensure your API key is correctly set.")
        return None
    except Exception as e:
        print(f"[LLM Interface Error] An error occurred during LLM call or JSON parsing: {e}")
        # print(f"Problematic response text (if available): {response_text[:500]}...")
        # Add more robust error handling, e.g., logging
        return None

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    # This block will run if you execute llm_interface.py directly (e.g., python llm_interface.py)

    # Make sure you have a .env file in the same directory with GEMINI_API_KEY="YOUR_API_KEY"
    # Or set the environment variable directly.

    # Dummy prompt for testing
    test_prompt = """
    You are a helpful AI.
    Extract the product name and price from the following text and output as JSON.
    Text: The new SuperWidget 5000 is available for $199.99.
    Output:
    """
    
    print("--- Testing call_llm_for_extraction with a dummy prompt ---")
    extracted_product_info = call_llm_for_extraction(test_prompt)

    if extracted_product_info:
        print("\n--- Extracted Product Info ---")
        print(json.dumps(extracted_product_info, indent=2))
    else:
        print("\n--- Failed to extract product info ---")

    # Example with a slightly more complex JSON structure
    test_prompt_complex = """
    You are a scientific information extractor.
    From the text, identify name and concentration of chemical. Output as JSON array.
    Text: Solution A contains NaCl at 0.9%. Solution B has glucose at 5%.
    Output:
    """
    print("\n--- Testing call_llm_for_extraction with a complex dummy prompt ---")
    extracted_chemicals = call_llm_for_extraction(test_prompt_complex)

    if extracted_chemicals:
        print("\n--- Extracted Chemicals ---")
        print(json.dumps(extracted_chemicals, indent=2))
    else:
        print("\n--- Failed to extract chemicals ---")