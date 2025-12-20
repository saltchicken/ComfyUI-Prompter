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


# Compiling them once here is faster than re-compiling inside the execution loop.
WILDCARD_REGEX = re.compile(r"{([\w_]+)}")
CLEAN_MULTIPLE_SPACES = re.compile(r"\s+")

CLEAN_DANGLING_CONNECTORS = re.compile(
    r"\s+\b(and|with|wearing|in|of|paired with)\s*$", re.IGNORECASE
)
CLEAN_BAD_PUNCTUATION_SPACES = re.compile(r"\s+([,.:;])")
CLEAN_DUPLICATE_PUNCTUATION = re.compile(r"([,.:;])\1+")
CLEAN_EMPTY_PARENTHESES = re.compile(r"\(\s*\)")



# Note: Since 'paired with' has a space, this relies on the regex engine matching the longest alternation correctly.
CLEAN_DUPLICATE_CONNECTORS = re.compile(
    r"\b(and|with|wearing|in|paired with)\s+(and|with|wearing|in|paired with)\b",
    re.IGNORECASE,
)


CLEAN_CONNECTOR_BEFORE_PUNCTUATION = re.compile(
    r"\b(and|with|wearing|in|of|paired with)\s+([,.:;])", re.IGNORECASE
)


class DataManager:
    """
    It checks file modification times to reload data without restarting ComfyUI.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance.categories = {}
            cls._instance.templates = {}
            cls._instance.loaded = False
            cls._instance.file_timestamps = {}
        return cls._instance

    def _get_file_timestamp(self, path):
        """Helper to get modification time."""
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0

    def check_for_updates(self):
        """Checks if any JSON files have been modified."""
        has_changes = False

        # Check template file
        tpl_mtime = self._get_file_timestamp(TEMPLATE_PATH)
        if tpl_mtime != self.file_timestamps.get(TEMPLATE_PATH, 0):
            has_changes = True

        # Check data directory
        if os.path.exists(DATA_DIR):
            for filename in os.listdir(DATA_DIR):
                if filename.endswith(".json"):
                    file_path = os.path.join(DATA_DIR, filename)
                    mtime = self._get_file_timestamp(file_path)
                    if mtime != self.file_timestamps.get(file_path, 0):
                        has_changes = True

        if has_changes:
            logger.info("Changes detected in data files. Reloading...")
            self.load_data(force=True)

    def load_data(self, force=False):
        """Loads data from disk. Added 'force' parameter."""
        if self.loaded and not force:
            return

        logger.info(f"Loading data from {DATA_DIR}...")

        # Reset storage
        self.categories = {}
        self.file_timestamps = {}  # Update timestamps during load

        # Load Categories
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".json"):
                category_name = filename[:-5]
                file_path = os.path.join(DATA_DIR, filename)

                self.file_timestamps[file_path] = self._get_file_timestamp(file_path)

                data = self._safe_load_json(file_path)

                if isinstance(data, list):
                    clean_data = [str(item) for item in data if str(item).strip()]
                    self.categories[category_name] = clean_data
                else:
                    logger.warning(f"Skipping {filename}: content is not a list.")

        # Load Templates

        self.file_timestamps[TEMPLATE_PATH] = self._get_file_timestamp(TEMPLATE_PATH)
        template_data = self._safe_load_json(TEMPLATE_PATH)

        if not template_data:
            logger.warning("Templates empty or missing. Using fallback.")
            template_data = {
                "Fallback": {
                    "structure": [
                        "{subject}",
                        "{style}",
                    ],
                    "formatting": {},
                }
            }

        # Handle legacy format where "structure" might be at root
        if "structure" in template_data:
            self.templates = {"Default": template_data}
        else:
            self.templates = template_data

        self.loaded = True

    def _safe_load_json(self, path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            return {}


# Instantiate the manager once
data_manager = DataManager()


class CustomizablePromptGenerator:
    """
    A dynamic prompt generator that builds its UI and Logic based on external files.
    """

    @classmethod
    def INPUT_TYPES(cls):
        data_manager.check_for_updates()
        if not data_manager.loaded:
            data_manager.load_data()

        categories = data_manager.categories
        templates = data_manager.templates

        template_list = list(templates.keys()) if templates else ["Default"]

        default_template = "Portrait Focus (Complete Outfit)"

        if default_template not in template_list:
            default_template = template_list[0]

        inputs = {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "template": (template_list,),
                "custom_text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "Prepended instructions (e.g. 'score_9, score_8_up, monochrome')...",
                    },
                ),
                "log_prompt": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "Yes",
                        "label_off": "No",
                    },
                ),
            },
            "optional": {},
        }

        default_overrides = {
            "accessories": "disabled",
            "artists": "disabled",
            "background": "a clean studio background",
            "body_type": "random",
            "camera": "random",
            "clothing_bottom": "random",
            "clothing_bottom_color": "random",
            "clothing_bottom_details": "random",
            "clothing_bottom_underwear": "disabled",
            "clothing_bottom_underwear_color": "disabled",
            "clothing_bottom_underwear_details": "disabled",
            "clothing_top": "random",
            "clothing_top_color": "random",
            "clothing_top_details": "random",
            "clothing_top_underwear": "disabled",
            "clothing_top_underwear_color": "disabled",
            "clothing_top_underwear_details": "disabled",
            "emotions": "smug",
            "gaze": "looking directly at the viewer",
            "hair": "random",
            "lighting": "random",
            "pose": "standing with a neutral stance",
            "style": "random",
            "subject": "random",
        }

        for cat_name, items in sorted(categories.items()):
            options = ["disabled", "random"] + sorted(items)
            default_val = default_overrides.get(cat_name, "disabled")

            if default_val not in options:
                default_val = "disabled"

            inputs["optional"][cat_name] = (options, {"default": default_val})

        return inputs

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = (
        "combined_prompt",
        "selection_details",
    )
    FUNCTION = "execute"
    CATEGORY = "Prompt/Custom"

    def execute(self, seed, custom_text, template, log_prompt, **kwargs):
        all_templates = data_manager.templates
        current_template = all_templates.get(template, list(all_templates.values())[0])
        categories = data_manager.categories

        # 1. Resolve Selections

        selected_values = {}

        for key, value in kwargs.items():
            if value == "disabled":
                selected_values[key] = ""
            elif value == "random":
                options = categories.get(key, [])
                if options:
                    # This ensures that changing 'Subject' random roll doesn't change 'Lighting' random roll.
                    field_seed = seed + sum(ord(c) * (i + 1) for i, c in enumerate(key))
                    field_rng = random.Random(field_seed)
                    selected_values[key] = field_rng.choice(options)
                else:
                    selected_values[key] = ""
            else:
                selected_values[key] = value

        # This handles wildcards and ignores disabled fields
        resolved_values = {}

        for key, val in selected_values.items():
            if not val:
                continue

            # Deterministic RNG per field for recursive resolution
            field_seed = seed + sum(ord(c) * (i + 1) for i, c in enumerate(key))
            field_rng = random.Random(field_seed)

            final_val = self._resolve_wildcards(val, categories, field_rng)
            resolved_values[key] = final_val

        # 2. Build Prompt Segments AND Selection Details
        structure_order = current_template.get("structure", [])
        formatting_rules = current_template.get("formatting", {})

        template_parts = []
        selection_details_parts = []


        if custom_text and custom_text.strip():
            selection_details_parts.append(f"custom_text: {custom_text.strip()}")

        for i, segment in enumerate(structure_order):
            if segment == "custom_text":
                continue

            # Check for placeholders like "{subject}"
            key_match = WILDCARD_REGEX.search(segment)

            if key_match:
                key = key_match.group(1)

                value = resolved_values.get(key, "")

                if value:
                    # Note: Value is already fully resolved now

                    selection_details_parts.append(f"{key}: {value}")

                    if key in formatting_rules:
                        fmt = formatting_rules[key]
                        template_parts.append(fmt.replace("{value}", value))
                    else:
                        template_parts.append(value)

            elif segment in resolved_values:
                # Handle direct key references (legacy support)
                val = resolved_values[segment]
                if val:
                    selection_details_parts.append(f"{segment}: {val}")
                    template_parts.append(val)
            else:
                # Static text
                template_parts.append(segment)

                if i == 0:
                    selection_details_parts.append(f"template: {segment}")

        selection_details = "\n".join(selection_details_parts)

        # 3. Assemble and Clean

        template_string = " ".join(template_parts)
        template_string = self._clean_prompt(template_string)

        if custom_text and custom_text.strip():
            full_string = f"{custom_text.strip()}\n\n{template_string}"
        else:
            full_string = template_string

        if log_prompt:
            logger.info(f"Generated Prompt: {full_string}")

        return (full_string, selection_details)

    def _resolve_wildcards(self, text, categories, rng, depth=0):
        """Recursively resolves {wildcards} in the text."""
        if depth > 10:
            return text

        def replacer(match):
            key = match.group(1)
            if key in categories:
                options = categories[key]
                if options:
                    choice = rng.choice(options)
                    return self._resolve_wildcards(choice, categories, rng, depth + 1)
            return match.group(0)

        return WILDCARD_REGEX.sub(replacer, text)

    def _clean_prompt(self, text):
        """
        Dedicated cleaning pipeline.
        """
        # Replace multiple spaces with single space
        text = CLEAN_MULTIPLE_SPACES.sub(" ", text)

        # Remove connectors before punctuation (e.g. "wearing ,") -> "wearing"

        # This prevents "wearing ," from becoming "," (losing the connector).
        # It now becomes "wearing", which is safer if items follow, or removed later if dangling.
        text = CLEAN_CONNECTOR_BEFORE_PUNCTUATION.sub(r"\1", text)

        # Remove duplicate connectors (e.g. "wearing wearing") -> "wearing"
        text = CLEAN_DUPLICATE_CONNECTORS.sub(r"\2", text)

        # Remove connectors at the end of string
        text = CLEAN_DANGLING_CONNECTORS.sub("", text)

        # Fix space before punctuation (e.g. "foo , bar") -> "foo, bar"
        text = CLEAN_BAD_PUNCTUATION_SPACES.sub(r"\1", text)

        # Fix double punctuation (e.g. "foo,, bar") -> "foo, bar"
        text = CLEAN_DUPLICATE_PUNCTUATION.sub(r"\1", text)

        # Remove empty parentheses
        text = CLEAN_EMPTY_PARENTHESES.sub("", text)

        return text.strip(" ,.:;")