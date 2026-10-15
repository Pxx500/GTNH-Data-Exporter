package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonObject;
import org.junit.Test;
import java.util.Arrays;
import java.util.List;
import net.minecraft.inventory.IInventory;
import net.minecraft.item.ItemStack;
import vazkii.botania.api.recipe.RecipeRuneAltar;
import vazkii.botania.common.crafting.recipe.HeadRecipe;

public class BotaniaCaptureTest {
    @Test
    public void runicDeclarationsPreserveOccurrencesAndNativeRuntimeRequirements() {
        RecipeRuneAltar recipe = new RecipeRuneAltar(null, 8000, "treeSapling", "treeSapling", "runeWater");
        for (String version : Arrays.asList("1.13.38-GTNH", "1.13.39-GTNH")) {
            BotaniaCapture.RuneDeclaration declaration = BotaniaCapture.runeDeclaration(recipe, version);
            assertTrue(declaration.known);
            assertEquals(Arrays.asList("treeSapling", "treeSapling", "runeWater"), declaration.inputs);
            assertEquals(version, declaration.conditions.get("native_version").getAsString());
            assertEquals(8000, declaration.conditions.get("total_mana").getAsInt());
            assertEquals("mana", declaration.conditions.get("energy_unit").getAsString());
            assertEquals(60, declaration.conditions.get("post_success_cooldown_ticks").getAsInt());
            assertFalse(declaration.conditions.getAsJsonObject("runtime_gates").get("wand_consumed").getAsBoolean());
        }
    }

    @Test
    public void runicUnsupportedVersionsAndSubclassesNeverProbeNativeOverrides() {
        RecipeRuneAltar unsafe = new RecipeRuneAltar(null, 1) {
            @Override public List<Object> getInputs() { throw new AssertionError("input getter called"); }
            @Override public ItemStack getOutput() { throw new AssertionError("output getter called"); }
            @Override public int getManaUsage() { throw new AssertionError("mana getter called"); }
            @Override public boolean matches(IInventory inventory) { throw new AssertionError("matcher called"); }
        };
        for (RecipeRuneAltar recipe : Arrays.asList(unsafe, new HeadRecipe(null, 22500, "nameTag"), null)) {
            BotaniaCapture.RuneDeclaration declaration = BotaniaCapture.runeDeclaration(recipe, "1.13.39-GTNH");
            assertFalse(declaration.known);
            assertTrue(declaration.inputs.isEmpty());
            assertNull(declaration.output);
            assertTrue(declaration.conditions.has("dynamic_output"));
        }
        BotaniaCapture.RuneDeclaration unchecked = BotaniaCapture.runeDeclaration(new RecipeRuneAltar(null, 1), "1.13.40-GTNH");
        assertFalse(unchecked.known);
        assertEquals("unsupported_native_version", unchecked.conditions.get("dynamic_inputs").getAsString());
        assertNull(unchecked.output);
    }

    @Test
    public void bothNativeCatalystPredicatesRemainRequiredDespiteNeiElseIfPresentation() {
        JsonObject conditions = BotaniaCapture.conditions(600, true, true);
        JsonObject catalyst = conditions.getAsJsonObject("catalyst_below");
        assertTrue(catalyst.get("alchemy_required").getAsBoolean());
        assertTrue(catalyst.get("conjuration_required").getAsBoolean());
        assertEquals("one_block_below_pool", catalyst.get("position").getAsString());
    }

    @Test
    public void zeroManaIsRetainedWithItsNativeUnitAndRuntimeGates() {
        JsonObject conditions = BotaniaCapture.conditions(0, false, true);
        assertEquals(0, conditions.get("total_mana").getAsInt());
        assertEquals("mana", conditions.get("energy_unit").getAsString());
        assertFalse(conditions.getAsJsonObject("catalyst_below").get("alchemy_required").getAsBoolean());
        JsonObject gates = conditions.getAsJsonObject("runtime_gates");
        assertEquals("at_least_total_mana", gates.get("available_mana").getAsString());
        assertEquals(101, gates.getAsJsonObject("excluded_entity_age_ticks").get("minimum").getAsInt());
        assertEquals(129, gates.getAsJsonObject("excluded_entity_age_ticks").get("maximum").getAsInt());
        assertEquals("first_matching_recipe_and_catalyst_before_mana_check", conditions.get("selection").getAsString());
    }
}
