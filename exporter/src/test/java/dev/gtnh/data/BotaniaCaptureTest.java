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
import vazkii.botania.api.recipe.RecipePetals;
import vazkii.botania.api.recipe.RecipeRuneAltar;
import vazkii.botania.common.crafting.recipe.HeadRecipe;

public class BotaniaCaptureTest {
    @Test
    public void runicDeclarationsPreserveOccurrencesAndNativeRuntimeRequirements() {
        RecipeRuneAltar recipe = new RecipeRuneAltar(null, 8000, "treeSapling", "treeSapling", "runeWater");
        for (String version : Arrays.asList("1.13.38-GTNH", "1.13.39-GTNH")) {
            BotaniaCapture.CatalogDeclaration declaration = BotaniaCapture.runeDeclaration(recipe, version);
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
            BotaniaCapture.CatalogDeclaration declaration = BotaniaCapture.runeDeclaration(recipe, "1.13.39-GTNH");
            assertFalse(declaration.known);
            assertTrue(declaration.inputs.isEmpty());
            assertNull(declaration.output);
            assertTrue(declaration.conditions.has("dynamic_output"));
        }
        BotaniaCapture.CatalogDeclaration unchecked = BotaniaCapture.runeDeclaration(new RecipeRuneAltar(null, 1), "1.13.40-GTNH");
        assertFalse(unchecked.known);
        assertEquals("unsupported_native_version", unchecked.conditions.get("dynamic_inputs").getAsString());
        assertNull(unchecked.output);
    }

    @Test
    public void petalDeclarationsPreserveOccurrencesWithoutPretendingSeedAndWaterAreIncluded() {
        List<Object> ingredients = Arrays.asList("petalWhite", "petalWhite", "petalWhite", "petalWhite", "runeWater");
        RecipePetals recipe = new RecipePetals(null, ingredients.toArray());
        BotaniaCapture.CatalogDeclaration declaration = BotaniaCapture.petalDeclaration(recipe, "1.13.39-GTNH");
        assertTrue(declaration.known);
        assertEquals(ingredients, declaration.inputs);
        JsonObject conditions = declaration.conditions;
        assertEquals("catalog_ingredient_occurrences_excludes_seed_and_refill", conditions.get("native_inputs_scope").getAsString());
        assertEquals("seed_trigger_and_water_refill_accounting_unmodeled", conditions.get("dynamic_inputs").getAsString());
        assertEquals("all_catalog_ingredients_consumed_including_runes_no_container_return", conditions.get("ingredient_accounting").getAsString());
        JsonObject seed = conditions.getAsJsonObject("seed_trigger");
        assertEquals(1, seed.get("consumed_items").getAsInt());
        assertEquals("Item.getUnlocalizedName(stack)", seed.get("predicate_input").getAsString());
        assertEquals("(?:(?:(?:[A-Z-_.:]|^)seed)|(?:(?:[a-z-_.:]|^)Seed))(?:[sA-Z-_.:]|$)", seed.get("predicate_pattern").getAsString());
        assertEquals("only_after_component_admission_fails", seed.get("precedence").getAsString());
        assertFalse(seed.get("matching_evaluated").getAsBoolean());
        assertFalse(seed.has("resource_id"));
        assertFalse(seed.has("group_id"));
        JsonObject water = conditions.getAsJsonObject("water_state");
        assertEquals("hasWater_true_and_hasLava_false", water.get("required").getAsString());
        assertEquals("setWater_false", water.get("on_success").getAsString());
        assertEquals("unresolved", water.get("refill_accounting").getAsString());
        assertEquals(5, water.getAsJsonArray("refill_paths").size());
        assertFalse(water.has("amount"));
        assertFalse(conditions.has("total_mana"));
        assertFalse(conditions.has("post_success_cooldown_ticks"));
        declaration.inputs.clear();
        assertEquals(ingredients, recipe.getInputs());
    }

    @Test
    public void petalCatalogDoesNotProbeSubclassesOrApplyRunicVersionAuthority() {
        RecipePetals unsafe = new RecipePetals(null) {
            @Override public List<Object> getInputs() { throw new AssertionError("input getter called"); }
            @Override public ItemStack getOutput() { throw new AssertionError("output getter called"); }
            @Override public boolean matches(IInventory inventory) { throw new AssertionError("matcher called"); }
        };
        for (RecipePetals recipe : Arrays.asList(unsafe, new RecipeRuneAltar(null, 1), new HeadRecipe(null, 1), null)) {
            BotaniaCapture.CatalogDeclaration declaration = BotaniaCapture.petalDeclaration(recipe, "1.13.39-GTNH");
            assertFalse(declaration.known);
            assertTrue(declaration.inputs.isEmpty());
            assertNull(declaration.output);
            assertTrue(declaration.conditions.has("dynamic_output"));
        }
        for (String version : Arrays.asList("1.13.38-GTNH", "1.13.40-GTNH", null)) {
            BotaniaCapture.CatalogDeclaration declaration = BotaniaCapture.petalDeclaration(new RecipePetals(null, "petalWhite"), version);
            assertFalse(declaration.known);
            assertEquals("unsupported_native_version", declaration.conditions.get("dynamic_inputs").getAsString());
            assertNull(declaration.output);
        }
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
