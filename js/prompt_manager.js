import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Global cache for LoRA names
let cachedLoraList = ["None"];

app.registerExtension({
    name: "Comfy.PromptTemplateManager",
    
    async setup() {
        try {
            const resp = await api.fetchApi("/object_info/LoraLoader");
            if (resp.status === 200) {
                const data = await resp.json();
                if (data && data.LoraLoader && data.LoraLoader.input && data.LoraLoader.input.required && data.LoraLoader.input.required.lora_name) {
                    cachedLoraList = ["None", ...data.LoraLoader.input.required.lora_name[0]];
                }
            }
        } catch (error) {
            console.error("PromptTemplateManager: Could not fetch LoRA list via API.", error);
        }
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PromptTemplateManager") {
            
            // ‼️ Helper function is now crucial for the widget config
            const getLoraList = () => {
                return cachedLoraList;
            };

            // ‼️ FIX: Explicitly define default properties. 
            // This ensures that when a node is reloaded or deserialized, LiteGraph knows 
            // these fields are essential and shouldn't be discarded as temporary junk.
            nodeType.prototype.default_properties = {
                templates: {},
                loraCount: 0
            };

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // ‼️ Safety check: Only truncate outputs if we are in a fresh/clean state 
                // to avoid breaking existing connections on reload.
                if (this.outputs && this.outputs.length > 1) {
                    // Check if we have connections; if so, this might be a reload on an active node.
                    // However, to enforce the "clean" look, we usually truncate. 
                    // We'll trust the configure step to restore outputs if needed.
                    this.outputs.length = 1;
                }

                // ‼️ Ensure properties object exists and has defaults (defensive coding)
                if (!this.properties) this.properties = {};
                // We use 'Object.assign' to merge defaults if they are missing, preventing overwrite of existing data
                if (!this.properties.templates) this.properties.templates = {};
                if (this.properties.loraCount === undefined) this.properties.loraCount = 0;

                const loadWidget = this.widgets.find((w) => w.name === "load_template");
                
                const loraInfoWidget = this.widgets.find((w) => w.name === "lora_info");
                if (loraInfoWidget) {
                    loraInfoWidget.type = "hidden";
                    loraInfoWidget.computeSize = () => [0, -4];
                }

                this.updateLoraInfo = () => {
                    if (!loraInfoWidget) return;
                    
                    const loraData = [];
                    for (const w of this.widgets) {
                        if (w.name.startsWith("lora_") && w.name.endsWith("_name")) {
                            const parts = w.name.split("_");
                            if (parts.length >= 3) {
                                const id = parts[1];
                                const strengthName = `lora_${id}_strength`;
                                const strengthWidget = this.widgets.find(sw => sw.name === strengthName);
                                
                                loraData.push({
                                    index: parseInt(id),
                                    name: w.value,
                                    strength: strengthWidget ? strengthWidget.value : 1.0
                                });
                            }
                        }
                    }
                    loraData.sort((a, b) => a.index - b.index);
                    loraInfoWidget.value = JSON.stringify(loraData);
                };

                this.moveButtonsToBottom = () => {
                    if(!this.widgets) return;
                    const buttons = [];
                    const others = [];
                    for(const w of this.widgets) {
                        if(w.type === "button") {
                            buttons.push(w);
                        } else {
                            others.push(w);
                        }
                    }
                    this.widgets = [...others, ...buttons];
                };

                this.smartResize = () => {
                    const minSize = this.computeSize();
                    const currentSize = this.size;
                    this.setSize([Math.max(currentSize[0], minSize[0]), minSize[1]]);
                };

                this.addLoraInputs = (nameValue = "None", strengthValue = 1.0) => {
                    this.properties.loraCount++;
                    const id = this.properties.loraCount;
                    
                    const wName = this.addWidget("combo", `lora_${id}_name`, "None", (v) => {
                        this.updateLoraInfo();
                    }, { values: getLoraList }); 

                    if (nameValue) wName.value = nameValue;

                    const wStrength = this.addWidget("number", `lora_${id}_strength`, strengthValue, (v) => {
                        this.updateLoraInfo();
                    }, { min: -10.0, max: 10.0, step: 0.01, default: 1.0, precision: 2 });

                    this.addOutput(`lora_${id}_name`, "STRING");
                    this.addOutput(`lora_${id}_strength`, "FLOAT");
                    
                    this.moveButtonsToBottom();
                    
                    // Update immediately after adding
                    this.updateLoraInfo();
                };

                this.addWidget("button", "Add LoRA", null, () => {
                    this.addLoraInputs();
                    this.smartResize();
                });

                const updateDropdown = () => {
                    if (!this.properties || !this.properties.templates) return;
                    const templates = Object.keys(this.properties.templates);
                    loadWidget.options.values = ["None", ...templates];
                    if (!loadWidget.options.values.includes(loadWidget.value)) {
                        loadWidget.value = "None";
                    }
                };
                this.updateTemplateDropdown = updateDropdown;
                updateDropdown();

                const originalCallback = loadWidget.callback;
                loadWidget.callback = (value) => {
                    if (originalCallback) originalCallback(value);
                    if (value === "None") return;

                    const template = this.properties.templates[value];
                    if (template) {
                        let maxLoraId = 0;
                        for (const key in template) {
                            if (key.startsWith("lora_") && key.endsWith("_name")) {
                                const parts = key.split("_");
                                if (parts.length >= 3) {
                                    const id = parseInt(parts[1]);
                                    if (id > maxLoraId) maxLoraId = id;
                                }
                            }
                        }

                        let changed = false;

                        // ‼️ FIX: Remove excess LoRAs if the new template has fewer than current
                        // This ensures the node state matches the template exactly (shrinking if needed)
                        while (this.properties.loraCount > maxLoraId) {
                            const id = this.properties.loraCount;
                            
                            // Remove Name Widget
                            const nameIndex = this.widgets.findIndex(w => w.name === `lora_${id}_name`);
                            if (nameIndex > -1) this.widgets.splice(nameIndex, 1);
                            
                            // Remove Strength Widget
                            const strengthIndex = this.widgets.findIndex(w => w.name === `lora_${id}_strength`);
                            if (strengthIndex > -1) this.widgets.splice(strengthIndex, 1);

                            // Remove Outputs (corresponding to this LoRA layer)
                            // We assume the last 2 outputs are the ones to go. 
                            // Guard against removing the main Prompt output (index 0).
                            if (this.outputs.length > 1) this.removeOutput(this.outputs.length - 1);
                            if (this.outputs.length > 1) this.removeOutput(this.outputs.length - 1);

                            this.properties.loraCount--;
                            changed = true;
                        }

                        while (this.properties.loraCount < maxLoraId) {
                            this.addLoraInputs();
                            changed = true;
                        }
                        
                        if (changed) {
                            this.moveButtonsToBottom();
                            this.smartResize();
                        }

                        for (const key in template) {
                            const w = this.widgets.find((w) => w.name === key);
                            if (w) {
                                w.value = template[key];
                            }
                        }
                        this.updateLoraInfo();
                    }
                };

                this.addWidget("button", "Save Template", null, () => {
                    const currentSelection = loadWidget.value;
                    const isExistingLoaded = currentSelection !== "None";

                    const dialog = document.createElement("div");
                    Object.assign(dialog.style, {
                        position: "fixed", left: "50%", top: "50%", transform: "translate(-50%, -50%)",
                        backgroundColor: "#222", padding: "20px", borderRadius: "8px", 
                        border: "1px solid #444", zIndex: 10000, color: "white", 
                        fontFamily: "sans-serif", display: "flex", flexDirection: "column", gap: "10px",
                        minWidth: "300px", boxShadow: "0 4px 6px rgba(0,0,0,0.5)"
                    });

                    const title = document.createElement("h3");
                    title.textContent = "Save Template";
                    title.style.margin = "0 0 10px 0";
                    dialog.appendChild(title);

                    const nameInput = document.createElement("input");
                    nameInput.type = "text";
                    nameInput.placeholder = "Template Name";
                    Object.assign(nameInput.style, { padding: "5px", backgroundColor: "#333", color: "white", border: "1px solid #555" });
                    
                    if (isExistingLoaded) nameInput.value = currentSelection; 
                    dialog.appendChild(nameInput);

                    const overwriteContainer = document.createElement("div");
                    Object.assign(overwriteContainer.style, { display: "flex", alignItems: "center", gap: "8px" });

                    const overwriteCheckbox = document.createElement("input");
                    overwriteCheckbox.type = "checkbox";
                    overwriteCheckbox.id = "overwrite-cb";
                    
                    const overwriteLabel = document.createElement("label");
                    overwriteLabel.htmlFor = "overwrite-cb";
                    overwriteLabel.textContent = isExistingLoaded ? `Overwrite current ("${currentSelection}")` : "Overwrite current";
                    
                    if (!isExistingLoaded) {
                        overwriteCheckbox.disabled = true;
                        overwriteLabel.style.color = "#777";
                    } else {
                        overwriteCheckbox.checked = false;
                    }

                    overwriteContainer.appendChild(overwriteCheckbox);
                    overwriteContainer.appendChild(overwriteLabel);
                    dialog.appendChild(overwriteContainer);

                    overwriteCheckbox.addEventListener("change", (e) => {
                        if (e.target.checked) {
                            nameInput.disabled = true;
                            nameInput.style.opacity = "0.5";
                            nameInput.value = currentSelection;
                        } else {
                            nameInput.disabled = false;
                            nameInput.style.opacity = "1";
                        }
                    });

                    const btnContainer = document.createElement("div");
                    Object.assign(btnContainer.style, { display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" });

                    const cancelBtn = document.createElement("button");
                    cancelBtn.textContent = "Cancel";
                    cancelBtn.onclick = () => document.body.removeChild(dialog);

                    const saveBtn = document.createElement("button");
                    saveBtn.textContent = "Save";
                    saveBtn.onclick = () => {
                        let finalName = "";
                        if (overwriteCheckbox.checked && isExistingLoaded) {
                            finalName = currentSelection;
                        } else {
                            finalName = nameInput.value.trim();
                        }

                        if (!finalName) {
                            alert("Please enter a template name.");
                            return;
                        }

                        const newTemplate = {};
                        const exclude = ["load_template", "Add LoRA", "Save Template", "Delete Template", "lora_info"];
                        
                        this.widgets.forEach(w => {
                            if (w.type !== "button" && !exclude.includes(w.name)) {
                                newTemplate[w.name] = w.value;
                            }
                        });

                        // Ensure templates object exists before assignment
                        if (!this.properties.templates) this.properties.templates = {};
                        this.properties.templates[finalName] = newTemplate;
                        
                        updateDropdown();
                        loadWidget.value = finalName;
                        
                        document.body.removeChild(dialog);
                        app.graph.setDirtyCanvas(true, true);
                    };

                    btnContainer.appendChild(cancelBtn);
                    btnContainer.appendChild(saveBtn);
                    dialog.appendChild(btnContainer);
                    document.body.appendChild(dialog);
                });

                this.addWidget("button", "Delete Template", null, () => {
                    const current = loadWidget.value;
                    if (current === "None") return;
                    if (confirm(`Are you sure you want to delete template "${current}"?`)) {
                        if (this.properties.templates) {
                            delete this.properties.templates[current];
                            updateDropdown();
                            loadWidget.value = "None";
                        }
                    }
                });
                
                return r;
            };

            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                if (onConfigure) onConfigure.apply(this, arguments);
                
                // ‼️ FIX: Better property checking during configure
                if (this.properties && typeof this.properties.loraCount !== 'undefined') {
                    const count = this.properties.loraCount;
                    this.properties.loraCount = 0; 
                    
                    for (let i = 0; i < count; i++) {
                        this.addLoraInputs(undefined, undefined);
                    }
                }

                if (this.updateTemplateDropdown) {
                    this.updateTemplateDropdown();
                }
                
                if (this.updateLoraInfo) {
                    this.updateLoraInfo();
                }
                
                if (this.moveButtonsToBottom) {
                    this.moveButtonsToBottom();
                }

                if(this.smartResize) {
                    this.smartResize();
                } else {
                     this.setSize(this.computeSize());
                }
            };
        }
    }
});
