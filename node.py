import os
import json
import random
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates.json")


_CACHE = {"categories": None, "templates": None}


def load_json(path):
    """Safe JSON loader."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return {}


def get_data_cached(key, loader_func):
    """‼️ ADDED: generic caching helper."""
    if _CACHE[key] is None:
        _CACHE[key] = loader_func()
    return _CACHE[key]


def _load_categories_from_disk():
    """Internal function to scan disk for categories."""
    categories = {}
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            category_name = filename[:-5]
            data = load_json(os.path.join(DATA_DIR, filename))
            if isinstance(data, list):
                categories[category_name] = data
    return categories


def get_available_categories():
    """‼️ CHANGED: Now uses the cache system."""
    return get_data_cached("categories", _load_categories_from_disk)


def get_templates():
    """‼️ ADDED: Load templates with caching."""

    def _load():
        data = load_json(TEMPLATE_PATH)
        # Handle legacy format (if user hasn't updated templates.json yet)
        if "structure" in data:
            return {"Default": data}
        return data

    return get_data_cached("templates", _load)


class CustomizablePromptGenerator:
    """
    A dynamic prompt generator that builds its UI and Logic based on external files.
    """

    @classmethod
    def INPUT_TYPES(cls):
        categories = get_available_categories()
        templates = get_templates()

        inputs = {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),

                "template": (list(templates.keys()),),
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

        for cat_name, items in sorted(categories.items()):
            options = ["disabled", "random"] + sorted(items)
            inputs["optional"][cat_name] = (options, {"default": "disabled"})

        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("combined_prompt",)
    FUNCTION = "execute"
    CATEGORY = "Prompt/Custom"

    def execute(self, seed, custom_text, template, **kwargs):

        all_templates = get_templates()


        current_template = all_templates.get(template, list(all_templates.values())[0])

        rng = random.Random(seed)

        # 1. Resolve Selections
        selected_values = {"custom_text": custom_text}


        categories = get_available_categories()

        for key, value in kwargs.items():
            if value == "disabled":
                selected_values[key] = ""
            elif value == "random":
                options = categories.get(key, [])
                if options:
                    selected_values[key] = rng.choice(options)
                else:
                    selected_values[key] = ""
            else:
                selected_values[key] = value

        # 2. Build Prompt Segments
        structure_order = current_template.get("structure", [])
        formatting_rules = current_template.get("formatting", {})

        final_parts = []

        for segment in structure_order:
            # Handle special BREAK keywords
            if segment in ["BREAK_CLIPG", "BREAK_CLIPL"]:
                continue


            key_match = re.search(r"^{([\w_]+)}$", segment)

            if key_match:
                key = key_match.group(1)
                value = selected_values.get(key, "")

                if value:
                    if key in formatting_rules:

                        fmt = formatting_rules[key]
                        final_parts.append(fmt.replace("{value}", value))
                    else:
                        final_parts.append(value)

            elif segment in selected_values:
                # Direct reference (like 'custom_text')
                val = selected_values[segment]
                if val:
                    final_parts.append(val)
            else:
                # Static text in template
                final_parts.append(segment)

        # 3. Assemble and Clean
        full_string = " ".join(final_parts)


        # 1. Replace multiple spaces with single space
        full_string = re.sub(r"\s+", " ", full_string)
        # 2. Fix space before punctuation (e.g. "word , word" -> "word, word")
        full_string = re.sub(r"\s+([,.:;])", r"\1", full_string)
        # 3. Fix double punctuation (e.g. "word,, word" -> "word, word")
        full_string = re.sub(r"([,.:;])\1+", r"\1", full_string)
        # 4. Clean leading/trailing punctuation/spaces
        full_string = full_string.strip(" ,.:;")

        return (full_string,)