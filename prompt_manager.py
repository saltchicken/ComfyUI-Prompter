import folder_paths

class PromptTemplateManager:
    """
    A ComfyUI node that stores templates strictly within the workflow metadata (node properties).
    This makes the workflow portable/self-contained.
    """
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):

        # They will be injected dynamically via **kwargs from the JS side.
        return {
            "required": {
                "load_template": (["None"], ),
                "prompt": ("STRING", {"multiline": True, "default": "insert prompt here"}),
            },
        }


    MAX_LORAS = 50


    # This prevents "tuple index out of range" errors when connecting dynamic outputs
    _return_types = ["STRING"]
    _return_names = ["prompt"]
    for i in range(1, MAX_LORAS + 1):
        _return_types.append("STRING")
        _return_types.append("FLOAT")
        _return_names.append(f"lora_{i}_name")
        _return_names.append(f"lora_{i}_strength")

    RETURN_TYPES = tuple(_return_types)
    RETURN_NAMES = tuple(_return_names)
    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"

    # This allows the node to accept any inputs (like our dynamic lora widgets)
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def process_template(self, load_template, prompt, **kwargs):
        # 1. Start with the fixed prompt output
        results = [prompt]

        # 2. Find all LoRA indices from the keyword arguments (inputs)
        indices = set()
        for k in kwargs.keys():
            if k.startswith("lora_") and "_name" in k:
                try:
                    parts = k.split("_")
                    # format is lora_{id}_name
                    if len(parts) >= 3:
                        indices.add(int(parts[1]))
                except ValueError:
                    pass
        
        # 3. Sort indices to ensure output order matches the creation order in JS
        sorted_indices = sorted(list(indices))

        # 4. Append Name and Strength for each LoRA
        for i in sorted_indices:
            name_key = f"lora_{i}_name"
            strength_key = f"lora_{i}_strength"
            
            lora_name = kwargs.get(name_key, "None")

            lora_strength = float(kwargs.get(strength_key, 1.0))
            
            results.append(lora_name)
            results.append(lora_strength)


        # This ensures the tuple length is always consistent with the definition
        while len(results) < len(self.RETURN_TYPES):
            results.append("None")  # Default name for unused slots
            results.append(1.0)     # Default strength for unused slots

        # This matches the dynamic outputs created in JS.
        return tuple(results)

NODE_CLASS_MAPPINGS = {
    "PromptTemplateManager": PromptTemplateManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTemplateManager": "Direct Prompt Template"
}