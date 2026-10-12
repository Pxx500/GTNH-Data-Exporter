package dev.gtnh.data;

import static org.junit.Assert.*;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

public class WorldgenCaptureTest {
    @Test
    public void weightedDrawsRetainReplacementAndCandidateSupportWithoutFixedYields() {
        JsonObject yield = WorldgenCapture.smallOreYield(Arrays.asList("gem", "gem", "crushed"), 2, "stone", "impure");
        JsonObject rule = yield.getAsJsonObject("output_rule");
        assertTrue("must retain the native weighted primary pool", rule.has("primary"));
        JsonObject primary = rule.getAsJsonObject("primary");
        assertEquals("gt_small_ore_fortune0", rule.get("kind").getAsString());
        assertEquals("per_qualifying_native_base_harvest", rule.get("scope").getAsString());
        assertEquals("primary", rule.getAsJsonArray("evaluation_order").get(0).getAsString());
        assertEquals("host", rule.getAsJsonArray("evaluation_order").get(1).getAsString());
        assertEquals("weighted_draws_with_replacement", primary.get("kind").getAsString());
        assertEquals(2, primary.get("draw_count").getAsInt());
        assertEquals(3, primary.get("total_weight").getAsInt());
        assertEquals(1, primary.get("amount_per_draw").getAsInt());
        JsonArray candidates = primary.getAsJsonArray("candidates");
        assertEquals(2, candidates.size());
        assertEquals("gem", candidates.get(0).getAsJsonObject().get("resource_id").getAsString());
        assertEquals(2, candidates.get(0).getAsJsonObject().get("weight").getAsInt());
        assertEquals(1, candidates.get(1).getAsJsonObject().get("weight").getAsInt());
        assertEquals(4, yield.getAsJsonArray("outputs").size());
        for (com.google.gson.JsonElement value : yield.getAsJsonArray("outputs")) {
            JsonObject output = value.getAsJsonObject();
            assertEquals("mined_item_rule_candidate", output.get("resource_semantics").getAsString());
            assertFalse(output.has("amount"));
            assertFalse(output.has("chance"));
        }
    }

    @Test
    public void emptyPrimaryStillHasExclusiveHostDustAndNoGuaranteedPrimaryYield() {
        JsonObject yield = WorldgenCapture.smallOreYield(Collections.emptyList(), 0, "pure", "impure");
        JsonObject rule = yield.getAsJsonObject("output_rule");
        JsonObject primary = rule.getAsJsonObject("primary");
        assertEquals(1, primary.get("draw_count").getAsInt());
        assertEquals(0, primary.get("total_weight").getAsInt());
        assertEquals(0, primary.getAsJsonArray("candidates").size());
        assertEquals("emit_nothing", primary.get("empty_pool_behavior").getAsString());
        JsonArray outcomes = rule.getAsJsonObject("host").getAsJsonArray("outcomes");
        assertEquals(3, outcomes.size());
        assertEquals(0, outcomes.get(0).getAsJsonObject().getAsJsonArray("outputs").size());
        assertProbability(outcomes.get(0).getAsJsonObject(), 2, 3);
        assertProbability(outcomes.get(1).getAsJsonObject(), 1, 9);
        assertProbability(outcomes.get(2).getAsJsonObject(), 2, 9);
        assertEquals(2, yield.getAsJsonArray("outputs").size());
    }

    @Test
    public void equalHostItemsMergeProbabilityButRetainExclusiveNativeCases() {
        JsonObject yield = WorldgenCapture.smallOreYield(Arrays.asList("dust", "dust"), 1, "dust", "dust");
        JsonArray outcomes = yield.getAsJsonObject("output_rule").getAsJsonObject("host").getAsJsonArray("outcomes");
        assertEquals(2, outcomes.size());
        JsonObject dust = outcomes.get(1).getAsJsonObject();
        assertProbability(dust, 1, 3);
        assertEquals(1, dust.getAsJsonArray("outputs").size());
        assertEquals(1, dust.getAsJsonArray("outputs").get(0).getAsJsonObject().get("amount").getAsInt());
        JsonArray cases = dust.getAsJsonArray("native_cases");
        assertEquals(2, cases.size());
        assertEquals("pure", cases.get(0).getAsJsonObject().get("case").getAsString());
        assertProbability(cases.get(0).getAsJsonObject(), 1, 9);
        assertEquals("impure", cases.get(1).getAsJsonObject().get("case").getAsString());
        assertProbability(cases.get(1).getAsJsonObject(), 2, 9);
        assertEquals(1, yield.getAsJsonArray("outputs").size());
    }

    @Test
    public void missingNativeIdentityCannotBecomeAnEmptyPoolOrNoDustOutcome() {
        assertThrows(IllegalArgumentException.class, () -> WorldgenCapture.smallOreYield(null, 1, "pure", "impure"));
        assertThrows(IllegalArgumentException.class, () -> WorldgenCapture.smallOreYield(Arrays.asList("gem", null), 1, "pure", "impure"));
        assertThrows(IllegalArgumentException.class, () -> WorldgenCapture.smallOreYield(Arrays.asList(" "), 1, "pure", "impure"));
        assertThrows(IllegalArgumentException.class, () -> WorldgenCapture.smallOreYield(Collections.emptyList(), 1, null, "impure"));
        assertThrows(IllegalArgumentException.class, () -> WorldgenCapture.smallOreYield(Collections.emptyList(), 1, "pure", ""));
    }

    private static void assertProbability(JsonObject outcome, int numerator, int denominator) {
        JsonObject probability = outcome.getAsJsonObject("probability");
        assertEquals(numerator, probability.get("numerator").getAsInt());
        assertEquals(denominator, probability.get("denominator").getAsInt());
    }
}
