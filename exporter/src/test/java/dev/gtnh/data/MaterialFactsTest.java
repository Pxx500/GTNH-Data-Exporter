package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertNull;

import com.google.gson.JsonObject;
import java.util.Arrays;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import org.junit.Test;

public class MaterialFactsTest {
    @Test
    public void dispatcherAndPhaseCatalogCollisionCannotSelectOneMaterial() {
        Object dispatcherMaterial = new Object();
        Object catalogMaterial = new Object();
        Map<Object, Set<String>> evidence = new IdentityHashMap<>();
        evidence.put(dispatcherMaterial, Collections.singleton("fluid"));
        evidence.put(catalogMaterial, Collections.singleton("fluid"));
        assertNull(MaterialFacts.uniqueFluidPhase(evidence));
    }

    @Test
    public void oneNativeIdentityStillRequiresOneProvenPhase() {
        Map<Object, Set<String>> evidence = new IdentityHashMap<>();
        assertNull(MaterialFacts.uniqueFluidPhase(evidence));
        Object material = new Object();
        evidence.put(material, Collections.<String>emptySet());
        assertNull(MaterialFacts.uniqueFluidPhase(evidence));
        evidence.put(material, new LinkedHashSet<>(Arrays.asList("fluid", "molten")));
        assertNull(MaterialFacts.uniqueFluidPhase(evidence));
        evidence.put(material, Collections.singleton("gas"));
        assertEquals("gas", MaterialFacts.uniqueFluidPhase(evidence));
    }

    @Test
    public void moltenAndOrdinaryFluidUseDifferentNativeAccountingBases() {
        assertQuantity(MaterialFacts.fluidAccounting("5.09.54.221", "molten", false, true),
            "gt_material_units", "144", "native_top_level_component_parts");
        assertQuantity(MaterialFacts.fluidAccounting("5.09.54.221", "fluid", false, true),
            "formula_units", "1000", "native_formula_unit");
        assertQuantity(MaterialFacts.fluidAccounting("5.09.54.221", "gas", false, true),
            "formula_units", "1000", "native_formula_unit");
    }

    @Test
    public void exactVerifiedRuntimeVersionsRetainNativeQuantityBases() {
        for (String version : Arrays.asList("5.09.54.221", "5.09.54.223", "5.09.54.225", "5.09.54.256")) {
            assertQuantity(MaterialFacts.fluidAccounting(version, "molten", false, true),
                "gt_material_units", "144", "native_top_level_component_parts");
            assertQuantity(MaterialFacts.fluidAccounting(version, "fluid", false, true),
                "formula_units", "1000", "native_formula_unit");
            assertUnresolved(MaterialFacts.fluidAccounting(version, "plasma", false, true));
            assertUnresolved(MaterialFacts.fluidAccounting(version, "fluid", true, true));
            assertUnresolved(MaterialFacts.fluidAccounting(version, "fluid", false, false));
        }
        for (String version : Arrays.asList("5.09.54.255", "5.09.54.256-dev", "5.09.54.257", "6.0")) {
            assertUnresolved(MaterialFacts.fluidAccounting(version, "molten", false, true));
            assertUnresolved(MaterialFacts.fluidAccounting(version, "gas", false, true));
        }
    }

    @Test
    public void taggedUnknownCompositionAndUnsupportedPhasesCannotClaimAccounting() {
        assertUnresolved(MaterialFacts.fluidAccounting("5.09.54.221", "molten", true, true));
        assertUnresolved(MaterialFacts.fluidAccounting("5.09.54.221", "fluid", false, false));
        assertUnresolved(MaterialFacts.fluidAccounting("5.09.54.221", "plasma", false, true));
        assertUnresolved(MaterialFacts.fluidAccounting("5.09.54.221", "slurry", false, true));
        assertUnresolved(MaterialFacts.fluidAccounting("5.09.54.221", "unresolved", false, true));
    }

    private void assertQuantity(JsonObject facts, String basis, String denominator, String normalization) {
        assertEquals("eligible", facts.get("status").getAsString());
        assertEquals(basis, facts.get("basis").getAsString());
        assertEquals("1", facts.getAsJsonObject("quantity").get("numerator").getAsString());
        assertEquals(denominator, facts.getAsJsonObject("quantity").get("denominator").getAsString());
        assertEquals(normalization, facts.get("normalization").getAsString());
    }

    private void assertUnresolved(JsonObject facts) {
        assertEquals("unresolved", facts.get("status").getAsString());
        assertTrue(facts.get("quantity").isJsonNull());
        assertTrue(facts.get("basis").isJsonNull());
        assertTrue(facts.get("reason").getAsString().length() > 0);
    }
}
