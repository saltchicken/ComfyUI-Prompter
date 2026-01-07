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
        lora_list = ["None"] + folder_paths.get_filename_list("loras")
        
        return {
            "required": {

                "load_template": (["None"], ),
                
                "prompt": ("STRING", {"multiline": True, "default": "insert prompt here"}),
                
                "lora_1_name": (lora_list, ),
                "lora_1_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "lora_2_name": (lora_list, ),
                "lora_2_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "lora_3_name": (lora_list, ),
                "lora_3_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "lora_4_name": (lora_list, ),
                "lora_4_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "new_template_name": ("STRING", {"default": "MyNewTemplate"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "lora_1_name", "lora_2_name", "lora_3_name", "lora_4_name")
    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"


    # This enables JS to add custom templates to the list without backend errors.
    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def process_template(self, load_template, prompt, 
                         lora_1_name, lora_1_strength,
                         lora_2_name, lora_2_strength,
                         lora_3_name, lora_3_strength,
                         lora_4_name, lora_4_strength,
                         new_template_name):
        
        # Pass-through logic. 
        # JS handles the "loading" (widget updating) before we get here.
        return (prompt, lora_1_name, lora_2_name, lora_3_name, lora_4_name)

NODE_CLASS_MAPPINGS = {
    "PromptTemplateManager": PromptTemplateManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTemplateManager": "Direct Prompt Template"
}