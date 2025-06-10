# src/prompt_builder.py

import json

def build_extraction_prompt(text_content: str, desired_info: list, examples: list = None) -> str:
    """
    Constructs a comprehensive prompt for an LLM to extract specific information from text.

    Args:
        text_content (str): The document excerpt (e.g., abstract, body paragraph, table text)
                            from which to extract information.
        desired_info (list): A list of strings, where each string is a specific piece of
                             information to extract (e.g., "Particle Size (nm)"). These
                             should be detailed to guide the LLM on what to look for.
        examples (list, optional): A list of dictionaries, where each dict contains
                                   'input_text' and 'output_json' for few-shot learning.
                                   Defaults to None.

    Returns:
        str: The full prompt string ready to be sent to the LLM.
    """

    # --- 1. System/Role Instruction ---
    system_instruction = (
        "You are a highly accurate scientific information extraction AI. "
        "Your task is to meticulously extract specific physicochemical properties, synthesis parameters, "
        "and characterization data of PLGA nanoparticles from scientific literature. "
        "You must identify and extract data for ALL distinct nanoparticle formulations or batches found in the text. " # 新增：强调提取所有不同的配方或批次
        "You must provide output ONLY in the specified JSON format."
    )

    # --- 2. Task Description ---
    task_description = (
        "From the following scientific text excerpt, identify and extract the exact values "
        "for the requested information types for EVERY distinct PLGA nanoparticle formulation/batch described. " # 新增：强调每一个不同的配方/批次
        "Each distinct formulation's data should be an individual JSON object within a JSON array. " # 新增：明确输出是一个JSON数组，每个元素是JSON对象
        "If a specific piece of information is explicitly stated, provide it. "
        "If a unit is provided in the text (e.g., nm, mg, mL, %), include it with the value. "
        "If the information is not found or explicitly stated as 'N/A' in the text, represent it as 'N/A'. "
        "Do not make assumptions, infer values, or include any extra text or explanations outside the JSON."
    )

    # --- 3. Requested Information List ---
    requested_info_str = "\n".join([f"- {info}" for info in desired_info])
    information_list_section = f"Here is the list of information you need to extract for EACH nanoparticle formulation:\n{requested_info_str}" # 新增：强调对每个配方提取


    # --- 4. Few-shot Examples (Crucial for Multiple Entries) ---
    examples_section = ""
    if examples:
        examples_section = "Here are some examples of input text and their corresponding expected JSON ARRAY output:\n" # 新增：强调是JSON ARRAY输出
        for example in examples:
            examples_section += f"---BEGIN EXAMPLE---\nTEXT:\n{example['input_text']}\n"
            # 确保这里的 output_json 是一个 JSON 数组的字符串表示
            examples_section += f"OUTPUT:\n{json.dumps(example['output_json'], indent=2)}\n---END EXAMPLE--...\n\n" # 新增：提示可能还有更多示例

        examples_section = examples_section.strip() + "\n\n"


    # --- 5. The Actual Text Content to Process ---
    text_content_section = f"---BEGIN TEXT TO PROCESS---\nTEXT:\n{text_content}\n---END TEXT TO PROCESS---"

    # --- 6. Output Instruction ---
    output_instruction = (
        "Provide ONLY the JSON ARRAY object. Do not include any additional text, " # 新增：强调是JSON ARRAY
        "comments, or explanations outside the JSON."
    )

    # --- Combine all parts into the final prompt ---
    full_prompt = (
        f"{system_instruction}\n\n"
        f"{task_description}\n\n"
        f"{information_list_section}\n\n"
        f"{examples_section}"
        f"{text_content_section}\n\n"
        f"{output_instruction}\n"
    )

    return full_prompt

# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    sample_text_multiple = (
        "Two types of PLGA nanoparticles were prepared. Batch A used 50 kDa PLGA (50:50 LA:GA) "
        "and resulted in particles with 120 nm size and -25 mV zeta potential. Encapsulation was 88%. "
        "Batch B utilized 75 kDa PLGA (75:25 LA:GA) synthesized via double emulsion. "
        "These particles showed a size of 250 nm and a zeta potential of -18 mV. Encapsulation was 75%."
    )

    desired_info_list = [
        "Batch Name/ID", # 新增：用于区分不同批次
        "PLGA Molecular Weight (MW; e.g., kDa, Da)",
        "PLGA LA:GA Ratio (e.g., 50:50)",
        "DLS Size (nm; average diameter)",
        "Zeta Potential (mV)",
        "Encapsulation Efficiency (%)",
        "Emulsion Type (Single/Double)", # 可以帮助区分
    ]

    # --- CRUCIAL: Example output must now be a JSON ARRAY ---
    few_shot_examples_multiple = [
        {
            "input_text": sample_text_multiple, # 使用包含多个配方的文本作为输入示例
            "output_json": [ # 输出必须是一个JSON数组
                {
                    "Batch Name/ID": "Batch A",
                    "PLGA Molecular Weight (MW; e.g., kDa, Da)": "50 kDa",
                    "PLGA LA:GA Ratio (e.g., 50:50)": "50:50",
                    "DLS Size (nm; average diameter)": "120 nm",
                    "Zeta Potential (mV)": "-25 mV",
                    "Encapsulation Efficiency (%)": "88%",
                    "Emulsion Type (Single/Double)": "N/A" # Batch A 未明确说明乳液类型
                },
                {
                    "Batch Name/ID": "Batch B",
                    "PLGA Molecular Weight (MW; e.g., kDa, Da)": "75 kDa",
                    "PLGA LA:GA Ratio (e.g., 50:50)": "75:25",
                    "DLS Size (nm; average diameter)": "250 nm",
                    "Zeta Potential (mV)": "-18 mV",
                    "Encapsulation Efficiency (%)": "75%",
                    "Emulsion Type (Single/Double)": "Double"
                }
            ]
        }
    ]

    # Build the prompt with examples for multiple entries
    prompt_for_multiple = build_extraction_prompt(
        sample_text_multiple,
        desired_info_list,
        examples=few_shot_examples_multiple
    )
    print("--- PROMPT FOR MULTIPLE NANOPARTICLE ENTRIES ---")
    print(prompt_for_multiple)