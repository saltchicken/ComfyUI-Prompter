import folder_paths
import json


# This must exist to satisfy ComfyUI's backend validation.
MAX_DYNAMIC_LORAS = 64

class PromptTemplateManager:
    """
    A ComfyUI node that stores templates strictly within the workflow metadata (node properties).
    This makes the workflow portable/self-contained.
    """
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "load_template": (["None"], ),
                "prompt": ("STRING", {"multiline": True, "default": "insert prompt here"}),
            },

            # We use "optional" to ensure it doesn't block execution if something glitches,
            # though JS should always provide it.
            "optional": {
                "lora_info": ("STRING", {"default": "[]", "multiline": False}),
            }
        }


    # If we don't, downstream nodes like "ShowText" will crash when validating connections to dynamic ports.
    # ‼️ FIX: Changed "STRING" to "COMBO" to match LoraLoader input requirements
    RETURN_TYPES = tuple(["STRING"] + ["COMBO", "FLOAT"] * MAX_DYNAMIC_LORAS)
    
    RETURN_NAMES = tuple(["prompt"] + [
        val for i in range(1, MAX_DYNAMIC_LORAS + 1) 
        for val in (f"lora_{i}_name", f"lora_{i}_strength")
    ])

    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def process_template(self, load_template, prompt, lora_info="[]", **kwargs):
        # 1. Start with the fixed prompt output
        results = [prompt]


        # we parse the JSON blob sent by the JS frontend.
        try:
            lora_data = json.loads(lora_info)
        except Exception as e:
            print(f"PromptTemplateManager: Error parsing lora_info JSON: {e}")
            lora_data = []

        # lora_data structure expected: [{'index': 1, 'name': '...', 'strength': 1.0}, ...]
        # We need to map this to our flat output list.
        
        # Create a dictionary for quick lookup by index
        lora_map = {item['index']: item for item in lora_data}
        
        # Determine the highest index used to ensure we process them in order
        max_index = 0
        if lora_data:
            max_index = max(item['index'] for item in lora_data)
        
        # 2. Iterate up to the highest index found (or just iterate sorted keys)
        # We iterate specifically through the indices found in the JSON data.
        sorted_indices = sorted(lora_map.keys())

        for i in sorted_indices:
            data = lora_map[i]
            lora_name = data.get('name', "None")
            lora_strength = float(data.get('strength', 1.0))
            
            results.append(lora_name)
            results.append(lora_strength)

        # 3. Pad the results with None to match RETURN_TYPES length.
        expected_len = len(self.RETURN_TYPES)
        if len(results) < expected_len:
            results.extend([None] * (expected_len - len(results)))

        return tuple(results)

NODE_CLASS_MAPPINGS = {
    "PromptTemplateManager": PromptTemplateManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTemplateManager": "Direct Prompt Template"
}
