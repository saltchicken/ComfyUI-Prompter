import os
import json
import folder_paths

class PromptTemplateManager:
    """
    A ComfyUI node to manage prompt templates and associated LoRAs directly from the node UI.
    Now supports saving and loading templates from a JSON file.
    """
    
    TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "templates.json")

    def __init__(self):
        pass

    @classmethod
    def _load_templates(cls):
        if not os.path.exists(cls.TEMPLATE_FILE):
            return {}
        try:
            with open(cls.TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading templates: {e}")
            return {}

    @classmethod

    def _save_template_to_file(cls, name, prompt, lora_data):
        templates = cls._load_templates()
        templates[name] = {
            "prompt": prompt,
            "lora_data": lora_data
        }
        try:
            with open(cls.TEMPLATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=4)
            print(f"Template '{name}' saved successfully.")
        except Exception as e:
            print(f"Error saving template: {e}")

    @classmethod
    def INPUT_TYPES(cls):
        
        templates = cls._load_templates()
        # Sort keys and ensure 'None' is the first option
        template_names = ["None"] + sorted(list(templates.keys()))

        lora_list = ["None"] + folder_paths.get_filename_list("loras")

        return {
            "required": {
                "load_template": (template_names, ),
                

                "prompt": ("STRING", {"multiline": True, "default": "insert prompt here"}),
                

                "lora_1_name": (lora_list, ),
                "lora_1_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "lora_2_name": (lora_list, ),
                "lora_2_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "lora_3_name": (lora_list, ),
                "lora_3_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "lora_4_name": (lora_list, ),
                "lora_4_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),

                "save_template_name": ("STRING", {"default": "MyNewTemplate"}),
                # Boolean acts as our "Button" - if True, it saves during execution
                "save_action": ("BOOLEAN", {"default": False, "label_on": "Save on Queue", "label_off": "Don't Save"}),
            },
        }


    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "lora_1_name", "lora_2_name", "lora_3_name", "lora_4_name")
    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"

    def process_template(self, load_template, prompt, 
                         lora_1_name, lora_1_strength,
                         lora_2_name, lora_2_strength,
                         lora_3_name, lora_3_strength,
                         lora_4_name, lora_4_strength,
                         save_template_name, save_action):

        # Helper to organize current widget values
        current_loras = [
            {"name": lora_1_name, "strength": lora_1_strength},
            {"name": lora_2_name, "strength": lora_2_strength},
            {"name": lora_3_name, "strength": lora_3_strength},
            {"name": lora_4_name, "strength": lora_4_strength},
        ]

        if save_action and save_template_name.strip():

            self._save_template_to_file(save_template_name, prompt, current_loras)


        if load_template != "None":
            templates = self._load_templates()
            if load_template in templates:
                data = templates[load_template]
                print(f"Processing with loaded template: '{load_template}'")
                

                # Fallback to current widget value if key missing
                prompt = data.get("prompt", prompt)
                

                saved_loras = data.get("lora_data", [])
                
                # Function to extract saved data or fallback to widget default
                def get_lora_data(index, default_name, default_str):
                    if index < len(saved_loras):
                        # Use saved value, or default if saved object is malformed
                        return saved_loras[index].get("name", default_name), saved_loras[index].get("strength", default_str)
                    return default_name, default_str

                # Map saved values to the variables we will return
                # We do not physically update the widgets in the UI (Comfy limitation), 
                # but we process the saved values for the output.
                lora_1_name, lora_1_strength = get_lora_data(0, lora_1_name, lora_1_strength)
                lora_2_name, lora_2_strength = get_lora_data(1, lora_2_name, lora_2_strength)
                lora_3_name, lora_3_strength = get_lora_data(2, lora_3_name, lora_3_strength)
                lora_4_name, lora_4_strength = get_lora_data(3, lora_4_name, lora_4_strength)


        return (prompt, lora_1_name, lora_2_name, lora_3_name, lora_4_name)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("save_action", False):
            return float("nan") # Always re-run if save is checked
        return kwargs.get("load_template", "None")


# Registration
NODE_CLASS_MAPPINGS = {
    "PromptTemplateManager": PromptTemplateManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTemplateManager": "Direct Prompt Template"
}