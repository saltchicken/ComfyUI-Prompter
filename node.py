import os
import json
import random
import re
import logging


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CustomizablePromptGenerator")

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

        logger.error(f"Error loading {path}: {e}")
        return {}


def get_data_cached(key, loader_func):
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


            # Ensure we only load lists, ignoring config objects or other JSON types
            if isinstance(data, list):
                # Filter out empty strings just in case
                clean_data = [str(item) for item in data if str(item).strip()]
                categories[category_name] = clean_data
            else:
                logger.warning(f"Skipping {filename}: content is not a list.")

    return categories


def get_available_categories():
    return get_data_cached("categories", _load_categories_from_disk)


def get_templates():
    def _load():
        data = load_json(TEMPLATE_PATH)
        # Handle legacy format
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


        template_list = list(templates.keys()) if templates else ["Default"]

        inputs = {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "template": (template_list,),
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

            # If a user puts "BREAK" in the template, it should pass through to CLIP.

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


            # or keys that were not in kwargs (e.g. from a file that was deleted)
            elif segment in selected_values:
                val = selected_values[segment]
                if val:
                    final_parts.append(val)
            else:
                # Pass through static text (e.g. "masterpiece", "BREAK", "art by")
                final_parts.append(segment)

        # 3. Assemble and Clean
        full_string = " ".join(final_parts)



        # 1. Replace multiple spaces
        full_string = re.sub(r"\s+", " ", full_string)

        # 2. Remove connectors before punctuation (e.g. "wearing ,")
        full_string = re.sub(
            r"\b(and|with|wearing|in|of)\s+([,.:;])", r"\2", full_string
        )


        # Keep the second one usually makes more sense in English grammar flow here
        full_string = re.sub(
            r"\b(and|with|wearing|in)\s+(and|with|wearing|in)\b", r"\2", full_string
        )

        # 4. Remove connectors at the end of string
        full_string = re.sub(r"\s+\b(and|with|wearing|in|of)\s*$", "", full_string)

        # 5. Fix space before punctuation (e.g. "foo , bar") -> "foo, bar"
        full_string = re.sub(r"\s+([,.:;])", r"\1", full_string)

        # 6. Fix double punctuation (e.g. "foo,, bar") -> "foo, bar"
        full_string = re.sub(r"([,.:;])\1+", r"\1", full_string)


        full_string = re.sub(r"\(\s*\)", "", full_string)

        # 8. Clean leading/trailing punctuation/spaces
        full_string = full_string.strip(" ,.:;")

        return (full_string,)