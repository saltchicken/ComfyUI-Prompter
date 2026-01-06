import os

class PromptTemplateManager:
    """
    A ComfyUI node to manage prompt templates and associated LoRAs directly from the node UI.
    No external JSON file required.
    """
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):

        
        default_template = "epic movie scene, shot on 35mm, {text}, dramatic lighting, 8k"
        default_loras = "cinematic_v1.safetensors: 0.8\nnoise_offset.safetensors: 0.3"

        return {
            "required": {
                "template_text": ("STRING", {"multiline": True, "default": default_template}),
                "lora_definitions": ("STRING", {"multiline": True, "default": default_loras}),
                "user_text": ("STRING", {"multiline": True, "default": "insert prompt here"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "lora_info")
    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"

    def process_template(self, template_text, lora_definitions, user_text):

        # We replace the placeholder {text} with the user's input
        final_prompt = template_text.replace("{text}", user_text)


        # Expected format per line: "lora_name.safetensors : strength"
        lora_strings = []
        
        if lora_definitions.strip():
            # Split by newlines or commas
            lines = lora_definitions.replace(',', '\n').split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # specific parsing logic
                if ":" in line:
                    parts = line.split(":")
                    name = parts[0].strip()
                    try:
                        strength = float(parts[1].strip())
                    except ValueError:
                        strength = 1.0 # default if parse fails
                else:
                    name = line.strip()
                    strength = 1.0 # default if no strength provided

                lora_strings.append(f"{name} (str: {strength})")
        
        lora_output = ", ".join(lora_strings) if lora_strings else "None"

        return (final_prompt, lora_output)

# Registration
NODE_CLASS_MAPPINGS = {
    "PromptTemplateManager": PromptTemplateManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTemplateManager": "Direct Prompt Template"
}