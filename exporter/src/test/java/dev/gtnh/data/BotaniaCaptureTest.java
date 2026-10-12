package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonObject;
import org.junit.Test;

public class BotaniaCaptureTest {
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
