import os
import json
import folder_paths
from aiohttp import web
from server import PromptServer


class TemplateAPIManager:
    TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "templates.json")

    @classmethod
    def load_templates(cls):
        if not os.path.exists(cls.TEMPLATE_FILE):
            return {}
        try:
            with open(cls.TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PromptManager] Error loading templates: {e}")
            return {}

    @classmethod
    def save_template(cls, name, data):
        templates = cls.load_templates()
        templates[name] = data
        try:
            with open(cls.TEMPLATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=4)
            return True
        except Exception as e:
            print(f"[PromptManager] Error saving template: {e}")
            return False


@PromptServer.instance.routes.get("/pmanager/get_templates")
async def get_templates_route(request):
    templates = TemplateAPIManager.load_templates()
    return web.json_response(templates)

@PromptServer.instance.routes.post("/pmanager/save_template")
async def save_template_route(request):
    data = await request.json()
    name = data.get("name")
    content = data.get("content")
    
    if not name or not content:
        return web.json_response({"error": "Missing name or content"}, status=400)
    
    success = TemplateAPIManager.save_template(name, content)
    if success:
        return web.json_response({"status": "success"})
    return web.json_response({"error": "Failed to save"}, status=500)


class PromptTemplateManager:
    """
    A ComfyUI node to manage prompt templates and associated LoRAs directly from the node UI.
    Uses JavaScript for interactivity.
    """
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # We still load initial templates to populate the dropdown on server start
        templates = TemplateAPIManager.load_templates()
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


                "new_template_name": ("STRING", {"default": "MyNewTemplate"}),
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
                         new_template_name):
        

        # The JavaScript updates the widgets *before* this runs. 
        # When this runs, the widgets already contain the correct values from the template 
        # (or what the user manually edited).
        
        return (prompt, lora_1_name, lora_2_name, lora_3_name, lora_4_name)

# Registration
NODE_CLASS_MAPPINGS = {
    "PromptTemplateManager": PromptTemplateManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTemplateManager": "Direct Prompt Template"
}