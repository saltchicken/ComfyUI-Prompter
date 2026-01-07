import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.PromptTemplateManager",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PromptTemplateManager") {
            
            // ‼️ Hook into node creation to setup properties and widgets
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // Ensure properties exist to store templates
                if (!this.properties) this.properties = {};
                if (!this.properties.templates) this.properties.templates = {};

                // Find the load_template widget
                const loadWidget = this.widgets.find((w) => w.name === "load_template");
                
                // Helper to update dropdown options based on stored templates
                // ‼️ Defined as a const for local use, but also attached to 'this' 
                // so it can be called by onConfigure later
                const updateDropdown = () => {
                    // ‼️ Safety check
                    if (!this.properties || !this.properties.templates) return;

                    const templates = Object.keys(this.properties.templates);
                    loadWidget.options.values = ["None", ...templates];
                    
                    // If current value is invalid, reset to None
                    if (!loadWidget.options.values.includes(loadWidget.value)) {
                        loadWidget.value = "None";
                    }
                };
                
                // ‼️ Expose the updater to the instance
                this.updateTemplateDropdown = updateDropdown;

                // Initial dropdown update
                updateDropdown();

                // ‼️ Listener for when a template is selected from the dropdown
                const originalCallback = loadWidget.callback;
                loadWidget.callback = (value) => {
                    if (originalCallback) originalCallback(value);
                    
                    if (value === "None") return;

                    const template = this.properties.templates[value];
                    if (template) {
                        // Apply template values to other widgets
                        for (const key in template) {
                            const w = this.widgets.find((w) => w.name === key);
                            if (w) {
                                w.value = template[key];
                            }
                        }
                    }
                };

                // ‼️ "Save Template" Button
                this.addWidget("button", "Save Template", null, () => {
                    const currentSelection = loadWidget.value;
                    const isExistingLoaded = currentSelection !== "None";

                    // Show custom Dialog
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

                    // Name Input
                    const nameInput = document.createElement("input");
                    nameInput.type = "text";
                    nameInput.placeholder = "Template Name";
                    nameInput.style.padding = "5px";
                    nameInput.style.backgroundColor = "#333";
                    nameInput.style.color = "white";
                    nameInput.style.border = "1px solid #555";
                    
                    // If overwrite isn't possible, we can pre-fill with a generic name or empty
                    if (isExistingLoaded) {
                        nameInput.value = currentSelection; 
                    }
                    dialog.appendChild(nameInput);

                    // Overwrite Checkbox Container
                    const overwriteContainer = document.createElement("div");
                    overwriteContainer.style.display = "flex";
                    overwriteContainer.style.alignItems = "center";
                    overwriteContainer.style.gap = "8px";

                    const overwriteCheckbox = document.createElement("input");
                    overwriteCheckbox.type = "checkbox";
                    overwriteCheckbox.id = "overwrite-cb";
                    
                    const overwriteLabel = document.createElement("label");
                    overwriteLabel.htmlFor = "overwrite-cb";
                    overwriteLabel.textContent = isExistingLoaded 
                        ? `Overwrite current ("${currentSelection}")` 
                        : "Overwrite current (No template loaded)";
                    
                    // Logic to disable/enable overwrite option
                    if (!isExistingLoaded) {
                        overwriteCheckbox.disabled = true;
                        overwriteLabel.style.color = "#777";
                    } else {
                        // Default to unchecked to prevent accidents
                        overwriteCheckbox.checked = false;
                    }

                    overwriteContainer.appendChild(overwriteCheckbox);
                    overwriteContainer.appendChild(overwriteLabel);
                    dialog.appendChild(overwriteContainer);

                    // Name input disable logic
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

                    // Buttons
                    const btnContainer = document.createElement("div");
                    btnContainer.style.display = "flex";
                    btnContainer.style.justifyContent = "flex-end";
                    btnContainer.style.gap = "10px";
                    btnContainer.style.marginTop = "10px";

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

                        // Collect values
                        const newTemplate = {};
                        const exclude = ["load_template"]; // Don't save the loader itself
                        
                        this.widgets.forEach(w => {
                            if (w.type !== "button" && !exclude.includes(w.name)) {
                                newTemplate[w.name] = w.value;
                            }
                        });

                        // Save
                        this.properties.templates[finalName] = newTemplate;
                        updateDropdown();
                        loadWidget.value = finalName; // Select the new template
                        
                        document.body.removeChild(dialog);
                        app.graph.setDirtyCanvas(true, true); // Refresh
                    };

                    btnContainer.appendChild(cancelBtn);
                    btnContainer.appendChild(saveBtn);
                    dialog.appendChild(btnContainer);

                    document.body.appendChild(dialog);
                });

                // ‼️ "Delete Template" Button
                this.addWidget("button", "Delete Template", null, () => {
                    const current = loadWidget.value;
                    if (current === "None") return;

                    if (confirm(`Are you sure you want to delete template "${current}"?`)) {
                        delete this.properties.templates[current];
                        updateDropdown();
                        loadWidget.value = "None"; // Reset selection
                    }
                });
                
                return r;
            };

            // ‼️ Hook into onConfigure to refresh widgets when workflow is loaded/refreshed
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                if (onConfigure) onConfigure.apply(this, arguments);
                
                // When the graph is reloaded, properties are restored from the save file.
                // We need to trigger the dropdown update to show the restored templates.
                if (this.updateTemplateDropdown) {
                    this.updateTemplateDropdown();
                }
            };
        }
    }
});
