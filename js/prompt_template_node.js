import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ‼️ Extension to handle PromptTemplateManager interactivity
app.registerExtension({
    name: "Comfy.PromptTemplateManager",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PromptTemplateManager") {
            
            // ‼️ Hook into node creation
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);

                const node = this;

                // Helper to find widgets by name
                const getWidget = (name) => node.widgets.find((w) => w.name === name);

                // ‼️ 1. Create a "Save Template" button
                // We add a button widget that triggers the API call
                this.addWidget("button", "Save Template", null, async () => {
                    const nameWidget = getWidget("new_template_name");
                    const templateName = nameWidget ? nameWidget.value : "";

                    if (!templateName || templateName.trim() === "") {
                        alert("Please enter a template name in 'new_template_name'.");
                        return;
                    }

                    // Gather current values
                    const prompt = getWidget("prompt").value;
                    const loraData = [];
                    for (let i = 1; i <= 4; i++) {
                        loraData.push({
                            name: getWidget(`lora_${i}_name`).value,
                            strength: getWidget(`lora_${i}_strength`).value
                        });
                    }

                    // Send to API
                    try {
                        const response = await api.fetchApi("/pmanager/save_template", {
                            method: "POST",
                            body: JSON.stringify({
                                name: templateName,
                                content: { prompt: prompt, lora_data: loraData }
                            })
                        });

                        if (response.ok) {
                            alert(`Template '${templateName}' saved!`);
                            // Refresh the dropdown
                            await refreshTemplateDropdown();
                        } else {
                            alert("Failed to save template.");
                        }
                    } catch (error) {
                        console.error(error);
                        alert("Error communicating with server.");
                    }
                });

                // ‼️ 2. Function to refresh the dropdown list from server
                const refreshTemplateDropdown = async () => {
                    try {
                        const response = await api.fetchApi("/pmanager/get_templates");
                        const templates = await response.json();
                        const templateWidget = getWidget("load_template");
                        
                        if (templateWidget) {
                            // Keep selection if it still exists, else None
                            const current = templateWidget.value;
                            const options = ["None", ...Object.keys(templates).sort()];
                            templateWidget.options.values = options;
                            
                            if (options.includes(current)) {
                                templateWidget.value = current;
                            } else {
                                templateWidget.value = "None";
                            }
                        }
                        return templates;
                    } catch (error) {
                        console.error("Failed to fetch templates", error);
                    }
                };

                // ‼️ 3. Listen for changes on "load_template"
                const templateWidget = getWidget("load_template");
                if (templateWidget) {
                    // We hook into the callback
                    const originalCallback = templateWidget.callback;
                    templateWidget.callback = async (value) => {
                        if (originalCallback) originalCallback(value);
                        
                        if (value && value !== "None") {
                            // Fetch latest data (or use cached if we stored it)
                            const response = await api.fetchApi("/pmanager/get_templates");
                            const templates = await response.json();
                            const data = templates[value];

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
                                        // Reset unused slots
                                        if (lName) lName.value = "None";
                                        if (lStr) lStr.value = 1.0;
                                    }
                                }
                                // Force redraw to show new values
                                app.graph.setDirtyCanvas(true, true);
                            }
                        }
                    };
                }
            };
        }
    }
});
