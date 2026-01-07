import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.PromptTemplateManager",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PromptTemplateManager") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);

                const node = this;

                if (!node.properties) node.properties = {};
                // 'saved_templates' will hold our library of templates
                if (!node.properties.saved_templates) node.properties.saved_templates = {};

                const getWidget = (name) => node.widgets.find((w) => w.name === name);

                node.refreshTemplateDropdown = () => {
                    const templates = node.properties.saved_templates;
                    const templateWidget = getWidget("load_template");
                    
                    if (templateWidget) {
                        const current = templateWidget.value;
                        // Sort keys alphabetically
                        const options = ["None", ...Object.keys(templates).sort()];
                        templateWidget.options.values = options;
                        
                        // If current selection is no longer valid, reset to None
                        if (!options.includes(current)) {
                            templateWidget.value = "None";
                        }
                    }
                };

                this.addWidget("button", "Save Template (to Node)", null, () => {
                    const nameWidget = getWidget("new_template_name");
                    const templateName = nameWidget ? nameWidget.value : "";

                    if (!templateName || templateName.trim() === "") {
                        alert("Please enter a template name.");
                        return;
                    }

                    // Gather values
                    const prompt = getWidget("prompt").value;
                    const loraData = [];
                    for (let i = 1; i <= 4; i++) {
                        loraData.push({
                            name: getWidget(`lora_${i}_name`).value,
                            strength: getWidget(`lora_${i}_strength`).value
                        });
                    }

                    node.properties.saved_templates[templateName] = {
                        prompt: prompt,
                        lora_data: loraData
                    };

                    node.refreshTemplateDropdown();
                    alert(`Template '${templateName}' saved to this node! It will persist with the workflow.`);
                });

                const templateWidget = getWidget("load_template");
                if (templateWidget) {
                    const originalCallback = templateWidget.callback;
                    templateWidget.callback = (value) => {
                        if (originalCallback) originalCallback(value);
                        
                        if (value && value !== "None") {
                            // Load from properties
                            const data = node.properties.saved_templates[value];

                            if (data) {
                                // Update Prompt
                                const promptWidget = getWidget("prompt");
                                if (promptWidget && data.prompt) {
                                    promptWidget.value = data.prompt;
                                }

                                // Update LoRAs
                                const loras = data.lora_data || [];
                                for (let i = 0; i < 4; i++) {
                                    const lName = getWidget(`lora_${i+1}_name`);
                                    const lStr = getWidget(`lora_${i+1}_strength`);
                                    
                                    if (i < loras.length) {
                                        if (lName) lName.value = loras[i].name || "None";
                                        if (lStr) lStr.value = loras[i].strength || 1.0;
                                    } else {
                                        if (lName) lName.value = "None";
                                        if (lStr) lStr.value = 1.0;
                                    }
                                }
                                app.graph.setDirtyCanvas(true, true);
                            }
                        }
                    };
                }
            };

            // Handle Workflow Loading
            // This ensures that when you open a saved workflow, the dropdown is repopulated
            // from the loaded properties.
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function() {
                if (onConfigure) onConfigure.apply(this, arguments);
                if (this.refreshTemplateDropdown) {
                    this.refreshTemplateDropdown();
                }
            };
        }
    }
});
