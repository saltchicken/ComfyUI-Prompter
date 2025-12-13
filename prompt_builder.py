import torch


class SimplePromptBuilder:
    """
    A custom node to build a prompt from various components like subject,
    description, clothing, pose, environment, and style.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "subject": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "A beautiful woman",
                        "placeholder": "Subject (e.g. A woman)",
                    },
                ),
                "description": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "detailed face, blue eyes, blonde hair",
                        "placeholder": "Physical description",
                    },
                ),
                "clothing": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "wearing a red dress",
                        "placeholder": "Clothing/Attire",
                    },
                ),
                "pose": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "standing confidently, looking at viewer",
                        "placeholder": "Pose/Action",
                    },
                ),
                "environment": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "in a futuristic city street, neon lights",
                        "placeholder": "Background/Environment",
                    },
                ),
                "style": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "cyberpunk style, masterpiece, best quality, 8k",
                        "placeholder": "Art style, Quality tags",
                    },
                ),
                "delimiter": (["comma", "space", "newline"],),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("final_prompt",)
    FUNCTION = "build_prompt"
    CATEGORY = "Custom/Prompting"

    def build_prompt(
        self, subject, description, clothing, pose, environment, style, delimiter
    ):
        parts = [subject, description, clothing, pose, environment, style]

        clean_parts = [p.strip() for p in parts if p and p.strip() != ""]

        if delimiter == "comma":
            separator = ", "
        elif delimiter == "newline":
            separator = "\n"
        else:
            separator = " "

        # Join them together
        final_prompt = separator.join(clean_parts)

        return (final_prompt,)


NODE_CLASS_MAPPINGS = {"SimplePromptBuilder": SimplePromptBuilder}

NODE_DISPLAY_NAME_MAPPINGS = {"SimplePromptBuilder": "✨ Simple Prompt Builder"}

