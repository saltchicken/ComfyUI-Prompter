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


# We only cache templates now as they are less likely to change frequently during runtime.
_TEMPLATE_CACHE = None


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


def _load_categories_from_disk():
    """Internal function to scan disk for categories."""
    categories = {}
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            category_name = filename[:-5]
            data = load_json(os.path.join(DATA_DIR, filename))

            # Ensure we only load lists
            if isinstance(data, list):
                clean_data = [str(item) for item in data if str(item).strip()]
                categories[category_name] = clean_data
            else:
                logger.warning(f"Skipping {filename}: content is not a list.")

    return categories


def get_templates():
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        data = load_json(TEMPLATE_PATH)
        # Handle legacy format
        if "structure" in data:
            _TEMPLATE_CACHE = {"Default": data}
        else:
            _TEMPLATE_CACHE = data
    return _TEMPLATE_CACHE


# This allows a value in "clothing.json" to be "a {color} dress" and have {color} resolved automatically.
def resolve_wildcards(text, categories, rng, depth=0):
    if depth > 10:  # Prevent infinite loops
        return text

    def replacer(match):
        key = match.group(1)
        # Check if the key exists in our loaded categories
        if key in categories:
            options = categories[key]
            if options:
                # Pick a random option
                choice = rng.choice(options)

                return resolve_wildcards(choice, categories, rng, depth + 1)

        # If key not found, leave it alone (it might be a syntax for another node)
        return match.group(0)

    # Regex looks for {tag_name}
    return re.sub(r"{([\w_]+)}", replacer, text)


class CustomizablePromptGenerator:
    """
    A dynamic prompt generator that builds its UI and Logic based on external files.
    """

    @classmethod
    def INPUT_TYPES(cls):
        categories = _load_categories_from_disk()
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

        categories = _load_categories_from_disk()


        # rng = random.Random(seed)

        # 1. Resolve Selections
        selected_values = {"custom_text": custom_text}

        for key, value in kwargs.items():
            if value == "disabled":
                selected_values[key] = ""
            elif value == "random":
                options = categories.get(key, [])
                if options:

                    field_seed = seed + sum(ord(c) * (i + 1) for i, c in enumerate(key))
                    field_rng = random.Random(field_seed)

                    choice = field_rng.choice(options)
                    selected_values[key] = choice
                else:
                    selected_values[key] = ""
            else:
                selected_values[key] = value

        # 2. Build Prompt Segments
        structure_order = current_template.get("structure", [])
        formatting_rules = current_template.get("formatting", {})

        final_parts = []

        for segment in structure_order:
            # Check if segment is a placeholder like "{subject}"
            key_match = re.search(r"^{([\w_]+)}$", segment)

            if key_match:
                key = key_match.group(1)
                value = selected_values.get(key, "")

                if value:

                    # This ensures wildcards inside a field resolve consistently even if other fields change
                    field_seed = seed + sum(ord(c) * (i + 1) for i, c in enumerate(key))
                    field_rng = random.Random(field_seed)

                    # E.g. if Subject is "a {body_type} warrior", resolve {body_type} now
                    value = resolve_wildcards(value, categories, field_rng)

                    if key in formatting_rules:
                        fmt = formatting_rules[key]
                        final_parts.append(fmt.replace("{value}", value))
                    else:
                        final_parts.append(value)

            # Or if it's a key that matches a category name directly but wasn't wrapped in {} in the structure
            # (Handling backward compatibility or loose structure definitions)
            elif segment in selected_values:
                val = selected_values[segment]
                if val:

                    field_seed = seed + sum(
                        ord(c) * (i + 1) for i, c in enumerate(segment)
                    )
                    field_rng = random.Random(field_seed)

                    val = resolve_wildcards(val, categories, field_rng)
                    final_parts.append(val)
            else:
                # Pass through static text (e.g. "masterpiece", "BREAK")
                final_parts.append(segment)

        # 3. Assemble and Clean
        full_string = " ".join(final_parts)

        # 1. Replace multiple spaces
        full_string = re.sub(r"\s+", " ", full_string)

        # 2. Remove connectors before punctuation (e.g. "wearing ,")
        full_string = re.sub(
            r"\b(and|with|wearing|in|of)\s+([,.:;])", r"\2", full_string
        )

        # 3. Remove duplicate connectors
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