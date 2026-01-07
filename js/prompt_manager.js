import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.PromptTemplateManager",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PromptTemplateManager") {
            
            // ‼️ Helper to get LoRA list from the standard LoraLoader definition
            // This avoids needing a custom API endpoint, reusing what ComfyUI already knows.
            const getLoraList = () => {
                const def = LiteGraph.registered_node_definitions["LoraLoader"];
                if (def && def.input && def.input.required && def.input.required.lora_name) {
                    return ["None", ...def.input.required.lora_name[0]];
                }
                return ["None"];
            };

            // ‼️ Hook into node creation to setup properties and widgets
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // Ensure properties exist
                if (!this.properties) this.properties = {};
                if (!this.properties.templates) this.properties.templates = {};
                // ‼️ Property to track how many dynamic LoRAs we have added
                if (!this.properties.loraCount) this.properties.loraCount = 0;

                const loadWidget = this.widgets.find((w) => w.name === "load_template");
                
                // ‼️ Logic to add a new LoRA input/output pair
                this.addLoraInputs = (nameValue = "None", strengthValue = 1.0) => {
                    this.properties.loraCount++;
                    const id = this.properties.loraCount;
                    const loraList = getLoraList();

                    // 1. Add LoRA Name Widget
                    const wName = this.addWidget("combo", `lora_${id}_name`, loraList, () => {}, { 
                        values: loraList 
                    });
                    wName.value = nameValue;

                    // 2. Add LoRA Strength Widget
                    const wStrength = this.addWidget("float", `lora_${id}_strength`, strengthValue, () => {}, {
                        min: -10.0, max: 10.0, step: 0.01, default: 1.0, precision: 2
                    });

                    // 3. Add Outputs (Name and Strength) to connect to other nodes
                    this.addOutput(`lora_${id}_name`, "STRING");
                    this.addOutput(`lora_${id}_strength`, "FLOAT");
                };

                // ‼️ "Add LoRA" Button
                // We add this *before* the Save/Delete buttons so it sits at the top or specific spot
                // But usually buttons are added last. Let's add it now.
                this.addWidget("button", "Add LoRA", null, () => {
                    this.addLoraInputs();
                    this.setSize(this.computeSize());
                });

                // Update dropdown helper
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

                // ‼️ Modified Template Loader
                const originalCallback = loadWidget.callback;
                loadWidget.callback = (value) => {
                    if (originalCallback) originalCallback(value);
                    if (value === "None") return;

                    const template = this.properties.templates[value];
                    if (template) {
                        // ‼️ Check if template has more LoRAs than current node
                        // We count how many 'lora_X_name' keys are in the template
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

                        // Expand node if needed
                        while (this.properties.loraCount < maxLoraId) {
                            this.addLoraInputs();
                        }
                        this.setSize(this.computeSize());

                        // Apply values
                        for (const key in template) {
                            const w = this.widgets.find((w) => w.name === key);
                            if (w) {
                                w.value = template[key];
                            }
                        }
                    }
                };

                // Save Template Button
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
                        // ‼️ Exclude buttons and load widget from saved data
                        const exclude = ["load_template", "Add LoRA", "Save Template", "Delete Template"];
                        
                        this.widgets.forEach(w => {
                            if (w.type !== "button" && !exclude.includes(w.name)) {
                                newTemplate[w.name] = w.value;
                            }
                        });

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

                // Delete Template Button
                this.addWidget("button", "Delete Template", null, () => {
                    const current = loadWidget.value;
                    if (current === "None") return;
                    if (confirm(`Are you sure you want to delete template "${current}"?`)) {
                        delete this.properties.templates[current];
                        updateDropdown();
                        loadWidget.value = "None";
                    }
                });
                
                return r;
            };

            // ‼️ Configure: Restore widgets when loading workflow
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                if (onConfigure) onConfigure.apply(this, arguments);
                
                // If we have saved loraCount in properties, recreate the inputs
                if (this.properties && this.properties.loraCount) {
                    const count = this.properties.loraCount;
                    // Reset internal counter because addLoraInputs increments it
                    this.properties.loraCount = 0; 
                    
                    for (let i = 0; i < count; i++) {
                        // Values will be filled automatically by ComfyUI's deserialization 
                        // matching widget names after we create them
                        this.addLoraInputs();
                    }
                }

                if (this.updateTemplateDropdown) {
                    this.updateTemplateDropdown();
                }
                
                this.setSize(this.computeSize());
            };
        }
    }
});
