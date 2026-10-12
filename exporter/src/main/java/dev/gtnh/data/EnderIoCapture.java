package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import crazypants.enderio.ModObject;
import crazypants.enderio.machine.IMachineRecipe;
import crazypants.enderio.machine.MachineRecipeRegistry;
import crazypants.enderio.machine.alloy.AlloyRecipeManager;
import crazypants.enderio.machine.alloy.VanillaSmeltingRecipe;
import crazypants.enderio.machine.crusher.CrusherMachineRecipe;
import crazypants.enderio.machine.crusher.CrusherRecipeManager;
import crazypants.enderio.machine.recipe.BasicManyToOneRecipe;
import crazypants.enderio.machine.recipe.IRecipe;
import crazypants.enderio.machine.recipe.ManyToOneMachineRecipe;
import crazypants.enderio.machine.recipe.OreDictionaryRecipeInput;
import crazypants.enderio.machine.recipe.Recipe;
import crazypants.enderio.machine.recipe.RecipeInput;
import crazypants.enderio.machine.recipe.RecipeOutput;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.item.ItemStack;

/** Configured native Sag Mill no-ball and ordinary Alloy Smelter recipe catalog. */
final class EnderIoCapture {
    private final NativeCapture capture;

    EnderIoCapture(NativeCapture capture) { this.capture = capture; }

    void capture() throws IOException {
        recipes("enderio:sag_mill", "Sag Mill", ModObject.blockSagMill.unlocalisedName,
            new ArrayList<>(CrusherRecipeManager.getInstance().getRecipes()), true);
        recipes("enderio:alloy_smelter", "Alloy Smelter", ModObject.blockAlloySmelter.unlocalisedName,
            new ArrayList<>(AlloyRecipeManager.getInstance().getRecipes()), false);
        capture.coverage("enderio.grinding_ball_variants", "unsupported", 0,
            "Only the no-grinding-ball Sag baseline is captured. Ball modifiers, wear and output repetition are not expanded");
        capture.coverage("enderio.alloy_vanilla_smelting", "unsupported", 0,
            "The display helper omits configured exclusions. Furnace mode and vanilla wrapper execution are not interpreted");
    }

    private void recipes(String family, String label, String machine, List<? extends IRecipe> recipes, boolean sag)
        throws IOException {
        JsonObject registry = registry(machine, sag);
        long supported = 0;
        for (int index = 0; index < recipes.size(); index++) {
            IRecipe recipe = recipes.get(index);
            JsonArray inputs = new JsonArray();
            JsonArray outputs = new JsonArray();
            JsonObject conditions = object("native_class", recipe.getClass().getName(), "machine", machine,
                "total_rf", null, "energy_unit", "RF", "selection", "native_first_matching_manager_record",
                "matching_order", "native_requirement_order", "extra_inputs", "unmatched_inputs_rejected",
                "machine_mode", sag ? "sag_mill" : "ALL_or_ALLOY", "machine_input_slots", sag ? 1 : 3,
                "grinding_ball", sag ? "absent" : "not_applicable", "modifier_variants", "unsupported",
                "registry_binding", "native_class_uid_contract",
                "output_roll", object("shared", true, "rng", "java.util.Random.nextFloat",
                    "range", "[0,1)", "task_clamp", "[0,1]", "comparison", "threshold >= roll",
                    "probability_model", "native_uniform_24_bit_float_lattice"));
            boolean known = sag ? recipe.getClass() == Recipe.class : recipe.getClass() == BasicManyToOneRecipe.class;
            Boolean executable = null;
            if (known) {
                conditions.addProperty("total_rf", recipe.getEnergyRequired());
                conditions.addProperty("native_bonus_type", recipe.getBonusType().name());
                for (RecipeInput input : recipe.getInputs()) inputs.add(input(input, conditions));
                for (RecipeOutput output : recipe.getOutputs()) output(output, outputs, conditions);
                if (!registry.get("known_wrappers_only").getAsBoolean())
                    conditions.addProperty("dynamic_output", "unresolved");
                executable = recipe.isValid() ? Boolean.TRUE : Boolean.FALSE;
                if (Boolean.TRUE.equals(executable) && (conditions.has("dynamic_inputs") || conditions.has("dynamic_output")))
                    executable = null;
                else supported++;
            } else {
                conditions.addProperty("dynamic_inputs", "unresolved");
                conditions.addProperty("dynamic_output", "unresolved");
            }
            capture.emitProcess(family, label, inputs, outputs, null, null, null, executable, conditions,
                object("owner", sag ? "CrusherRecipeManager.getRecipes" : "AlloyRecipeManager.getRecipes",
                    "index", index, "native_class", recipe.getClass().getName(), "native_version", "2.10.49"));
        }
        capture.coverage(family, "partial", recipes.size(),
            "Configured manager records in native order. Supported baseline predicates: " + supported
                + ". Machine modes, first-match selection and inventory layout remain explicit conditions", registry);
    }

    private JsonObject input(RecipeInput input, JsonObject conditions) throws IOException {
        boolean ordinary = input != null && input.getClass() == RecipeInput.class;
        boolean ore = input != null && input.getClass() == OreDictionaryRecipeInput.class;
        ItemStack original = input == null ? null : input.getInput();
        ItemStack[] alternatives = original == null ? new ItemStack[0] : new ItemStack[]{original};
        if (ore) {
            ItemStack[] declared = input.getEquivelentInputs();
            alternatives = declared == null ? new ItemStack[0] : declared;
        }
        JsonObject slot = capture.itemSlot(alternatives, -1, false, false);
        boolean known = (ordinary || ore) && !input.isFluid() && original != null && original.stackSize > 0
            && alternatives.length != 0;
        Boolean metadataIgnored = null;
        if (known && ordinary) {
            ItemStack probe = original.copy();
            probe.setItemDamage(original.getItemDamage() == 0 ? 1 : 0);
            if (probe.getItem() == original.getItem() && probe.getItemDamage() != original.getItemDamage()
                && input.isInput(original.copy())) metadataIgnored = input.isInput(probe);
            else known = false;
        }
        for (JsonElement value : slot.getAsJsonArray("choices")) {
            JsonObject choice = value.getAsJsonObject();
            if (choice.get("resource_id").isJsonNull()) known = false;
            if (known && ordinary) choice.add("match", object("mode", metadataIgnored ? "wildcard" : "exact",
                "nbt_sensitive", false));
        }
        slot.addProperty("native_class", input == null ? null : input.getClass().getName());
        if (input != null) {
            slot.addProperty("native_slot", input.getSlotNumber());
            slot.addProperty("native_multiplier", input.getMulitplier());
        }
        if (!known) {
            conditions.addProperty("dynamic_inputs", "unresolved");
            slot.addProperty("role", "consume");
            for (JsonElement value : slot.getAsJsonArray("choices")) {
                JsonObject choice = value.getAsJsonObject();
                choice.add("declared_match", choice.get("match"));
                choice.add("match", object("mode", "native_unknown"));
                if (original != null && original.stackSize <= 0) choice.addProperty("amount", original.stackSize);
            }
            if (input != null && input.isFluid()) slot.add("native_fluid", object("resource_id",
                capture.fluid(input.getFluidInput()), "amount", input.getFluidInput().amount));
        }
        return slot;
    }

    private void output(RecipeOutput output, JsonArray outputs, JsonObject conditions) throws IOException {
        if (output == null || output.getClass() != RecipeOutput.class) {
            conditions.addProperty("dynamic_output", "unresolved");
            JsonArray unknown = conditions.has("uninterpreted_outputs")
                ? conditions.getAsJsonArray("uninterpreted_outputs") : new JsonArray();
            unknown.add(object("native_class", output == null ? null : output.getClass().getName()));
            conditions.add("uninterpreted_outputs", unknown);
            return;
        }
        float threshold = output.getChance();
        JsonObject probability = NativeCapture.floatRollChance(threshold, true);
        if (probability == null) conditions.addProperty("dynamic_output", "unresolved");
        JsonObject record = object("resource_id", output.isFluid() ? capture.fluid(output.getFluidOutput())
            : capture.item(output.getOutput()), "amount", output.isFluid() ? output.getFluidOutput().amount
            : output.getOutput().stackSize, "chance", probability, "native_chance_threshold",
            Float.isNaN(threshold) || Float.isInfinite(threshold) ? Float.toString(threshold) : threshold,
            "native_experience", output.getExperiance());
        outputs.add(record);
    }

    private JsonObject registry(String machine, boolean sag) {
        JsonArray wrappers = new JsonArray();
        boolean found = false;
        boolean known = true;
        int index = 0;
        for (Map.Entry<String, IMachineRecipe> entry : new LinkedHashMap<>(
            MachineRecipeRegistry.instance.getRecipesForMachine(machine)).entrySet()) {
            IMachineRecipe wrapper = entry.getValue();
            boolean nativeOwner = sag ? wrapper.getClass() == CrusherMachineRecipe.class
                && "CrusherRecipe".equals(wrapper.getUid()) : wrapper.getClass() == ManyToOneMachineRecipe.class
                && "AlloySmelterRecipe".equals(wrapper.getUid());
            boolean vanilla = !sag && wrapper.getClass() == VanillaSmeltingRecipe.class;
            found |= nativeOwner;
            known &= nativeOwner || vanilla;
            wrappers.add(object("index", index++, "registry_key", entry.getKey(), "uid", wrapper.getUid(),
                "native_class", wrapper.getClass().getName(), "machine", wrapper.getMachineName(),
                "status", nativeOwner ? "native_owner_wrapper" : vanilla ? "unsupported_vanilla_wrapper" : "uninterpreted"));
        }
        return object("registry_wrappers", wrappers, "known_wrappers_only", found && known,
            "binding", "native_class_uid_contract", "manager_reference", "not_exposed_by_public_wrapper_api");
    }
}
