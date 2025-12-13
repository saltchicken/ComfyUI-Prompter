from .node import CustomizableFluxPromptGenerator

NODE_CLASS_MAPPINGS = {
    "CustomizableFluxPromptGenerator": CustomizableFluxPromptGenerator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CustomizableFluxPromptGenerator": "Flux Prompt Generator (Custom)"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
