from .node import CustomizablePromptGenerator

NODE_CLASS_MAPPINGS = {"CustomizablePromptGenerator": CustomizablePromptGenerator}

NODE_DISPLAY_NAME_MAPPINGS = {"CustomizablePromptGenerator": "Prompter (Customizable)"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
