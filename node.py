import os
import json
import random
import re


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates.json")


def load_json(path):
    """Safe JSON loader."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return []


def get_available_categories():
    """
    DYNAMIC LOADING:
    Scans the 'data' folder. Every .json file found becomes a category.
    The filename (minus .json) is used as the key.
    """
    categories = {}
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            category_name = filename[:-5]  # Strip .json
            data = load_json(os.path.join(DATA_DIR, filename))
            if isinstance(data, list):
                categories[category_name] = data
    return categories


class CustomizablePromptGenerator:
    """
    A dynamic prompt generator that builds its UI and Logic based on external files.
    """

    @classmethod
    def INPUT_TYPES(cls):
        # Instead of hardcoding keys like "lighting", we generate them from files.
        categories = get_available_categories()

        inputs = {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),

                "custom_text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "Optional custom text to inject...",
                    },
                ),
            },
            "optional": {},
        }

        # Add a dropdown for every JSON file found in /data

        for cat_name, items in sorted(categories.items()):
            # Add "random" and "disabled" options to every list
            options = ["disabled", "random"] + sorted(items)
            inputs["optional"][cat_name] = (options, {"default": "disabled"})

        return inputs

    RETURN_TYPES = ("STRING",)

    RETURN_NAMES = ("combined_prompt",)
    FUNCTION = "execute"
    CATEGORY = "Prompt/Custom"

    def execute(self, seed, custom_text, **kwargs):
        # We load instructions on how to build the prompt from a file, not python code.
        templates = load_json(TEMPLATE_PATH)
        rng = random.Random(seed)

        # 1. Resolve Selections
        # Go through every input provided by ComfyUI (kwargs)
        selected_values = {"custom_text": custom_text}

        categories = get_available_categories()  # Reload to ensure freshness

        for key, value in kwargs.items():
            if value == "disabled":
                selected_values[key] = ""
            elif value == "random":
                # Pick a random item from the data file
                options = categories.get(key, [])
                if options:
                    selected_values[key] = rng.choice(options)
                else:
                    selected_values[key] = ""
            else:
                selected_values[key] = value

        # 2. Build Prompt Segments based on templates.json
        # The structure is defined in the JSON file under "structure"
        structure_order = templates.get("structure", [])
        formatting_rules = templates.get("formatting", {})

        final_parts = []

        for segment in structure_order:
            # Handle special BREAK keywords defined in the JSON structure
            if segment in ["BREAK_CLIPG", "BREAK_CLIPL"]:
                continue

            # If segment is "{lighting}", we look up 'lighting' in selected_values
            # If we find a value, we check if there is a formatter like "lit by {value}"

            # Extract key name (e.g., "{lighting}" -> "lighting")
            key_match = re.search(r"{(.+?)}", segment)
            if key_match:
                key = key_match.group(1)
                value = selected_values.get(key, "")

                if value:
                    # Check if we have a specific phrase pattern for this key
                    # e.g. "lighting": "illuminated by {value}"
                    if key in formatting_rules:
                        formatted_segment = formatting_rules[key].replace(
                            "{value}", value
                        )
                        final_parts.append(formatted_segment)
                    else:
                        # No formatting rule, just use the raw value
                        final_parts.append(value)


            elif segment in selected_values:
                val = selected_values[segment]
                # Only append if the user actually typed something
                if val:
                    final_parts.append(val)


            else:
                final_parts.append(segment)

        # 3. Assemble
        full_string = " ".join(final_parts)

        # Cleanup punctuation (basic)
        full_string = re.sub(r"\s+", " ", full_string).strip()
        full_string = full_string.replace(" ,", ",")
        full_string = full_string.replace(" .", ".")

        # Now returns the simple linear string.

        return (full_string,)