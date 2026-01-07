import folder_paths

# ‼️ Defined a maximum limit for dynamic LoRA outputs. 
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
        }

    # ‼️ CHANGED: We MUST define the outputs here for validation to pass.
    # If we don't, downstream nodes like "ShowText" will crash when validating connections to dynamic ports.
    # We will hide the unused ones in the JS side to avoid UI clutter.
    RETURN_TYPES = tuple(["STRING"] + ["STRING", "FLOAT"] * MAX_DYNAMIC_LORAS)
    
    RETURN_NAMES = tuple(["prompt"] + [
        val for i in range(1, MAX_DYNAMIC_LORAS + 1) 
        for val in (f"lora_{i}_name", f"lora_{i}_strength")
    ])

    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def process_template(self, load_template, prompt, **kwargs):
        results = [prompt]

        # Find all LoRA indices from the keyword arguments (inputs)
        indices = set()
        for k in kwargs.keys():
            if k.startswith("lora_") and "_name" in k:
                try:
                    parts = k.split("_")
                    if len(parts) >= 3:
                        indices.add(int(parts[1]))
                except ValueError:
                    pass
        
        sorted_indices = sorted(list(indices))

        # Append Name and Strength for each LoRA
        for i in sorted_indices:
            name_key = f"lora_{i}_name"
            strength_key = f"lora_{i}_strength"
            
            lora_name = kwargs.get(name_key, "None")
            lora_strength = float(kwargs.get(strength_key, 1.0))
            
            results.append(lora_name)
            results.append(lora_strength)

        # ‼️ CHANGED: Pad the results with None to match RETURN_TYPES length.
        # This ensures that even if you only use 2 LoRAs, the backend returns a tuple 
        # long enough to satisfy the 64-LoRA definition, preventing "index out of range".
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
