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
    def _save_template_to_file(cls, name, template_text, lora_definitions):
        templates = cls._load_templates()
        templates[name] = {
            "template_text": template_text,
            "lora_definitions": lora_definitions
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

        default_template = "epic movie scene, shot on 35mm, {text}, dramatic lighting, 8k"
        

        lora_list = ["None"] + folder_paths.get_filename_list("loras")

        return {
            "required": {

                "load_template": (template_names, ),
                
                "template_text": ("STRING", {"multiline": True, "default": default_template}),
                

                "lora_definitions": (lora_list, ),
                

                "lora_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "user_text": ("STRING", {"multiline": True, "default": "insert prompt here"}),
                

                "save_template_name": ("STRING", {"default": "MyNewTemplate"}),
                # Boolean acts as our "Button" - if True, it saves during execution
                "save_action": ("BOOLEAN", {"default": False, "label_on": "Save on Queue", "label_off": "Don't Save"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "lora_info")
    FUNCTION = "process_template"
    CATEGORY = "Custom/Prompting"


    def process_template(self, template_text, lora_definitions, user_text, load_template, save_template_name, save_action, lora_strength):


        if save_action and save_template_name.strip():
            # If lora is None, save empty string, otherwise save "name: strength"
            save_lora_str = ""
            if lora_definitions != "None":
                save_lora_str = f"{lora_definitions}: {lora_strength}"
            
            self._save_template_to_file(save_template_name, template_text, save_lora_str)


        if load_template != "None":
            templates = self._load_templates()
            if load_template in templates:
                data = templates[load_template]
                # Override the inputs with the saved data for processing
                template_text = data.get("template_text", "")
                lora_definitions = data.get("lora_definitions", "")
                print(f"Processing with loaded template: '{load_template}'")

        # We replace the placeholder {text} with the user's input
        final_prompt = template_text.replace("{text}", user_text)


        # Expected format per line: "lora_name.safetensors : strength"
        lora_strings = []
        

        if lora_definitions == "None":
            lora_definitions = ""

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

                    strength = lora_strength 

                lora_strings.append(f"{name} (str: {strength})")
        
        lora_output = ", ".join(lora_strings) if lora_strings else "None"

        return (final_prompt, lora_output)


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