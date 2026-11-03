package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import codechicken.nei.ItemList;
import codechicken.nei.NEIClientConfig;
import codechicken.nei.PositionedStack;
import codechicken.nei.recipe.GuiCraftingRecipe;
import codechicken.nei.recipe.GuiUsageRecipe;
import codechicken.nei.recipe.ICraftingHandler;
import codechicken.nei.recipe.Recipe;
import codechicken.nei.recipe.StackInfo;
import codechicken.nei.recipe.TemplateRecipeHandler;
import codechicken.nei.util.NBTJson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import com.google.common.hash.Hashing;
import forestry.api.recipes.IStillRecipe;
import forestry.api.recipes.RecipeManagers;
import forestry.core.recipes.nei.PositionedFluidTank;
import forestry.factory.recipes.StillRecipe;
import forestry.factory.recipes.StillRecipeManager;
import forestry.factory.recipes.nei.NEIHandlerStill;
import gregtech.api.recipe.RecipeMap;
import gregtech.nei.GTNEIDefaultHandler;
import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.IdentityHashMap;
import java.util.Set;
import java.util.LinkedHashSet;
import java.util.Collections;
import java.util.Arrays;
import java.util.function.Supplier;
import java.net.JarURLConnection;
import java.net.URL;
import java.net.URI;
import java.util.Enumeration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPOutputStream;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraftforge.fluids.FluidRegistry;
import net.minecraftforge.fluids.FluidStack;
import net.minecraftforge.fluids.FluidTank;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Client-side NEI presentation evidence, independent of canonical resource serialization. */
final class NeiReferenceCapture implements Closeable {
    private static final Logger LOG = LogManager.getLogger("GTNHDataExporter");
    private static final String[] STREAMS = {"handlers", "signatures", "handler-views"};
    private final Path directory;
    private final boolean stillOnly;
    private final Map<String, BufferedWriter> streams = new LinkedHashMap<>();
    private final Map<String, Long> counts = new LinkedHashMap<>();
    private long failedHandlers;
    private long emptyHandlers;
    private long failedSignatures;
    private long failedViews;
    private long failedStacks;
    private long failedItemFacts;
    private JsonObject presentationContext;
    private int selectedHandlers;
    private int excludedHandlers;
    private JsonObject selectionFailure;
    private long capturedTanks;
    private long unsupportedTanks;
    private long failedTanks;
    private boolean closed;

    private NeiReferenceCapture(Path directory, boolean stillOnly) throws IOException {
        this.directory = directory;
        this.stillOnly = stillOnly;
        Files.createDirectory(directory);
        try {
            for (String name : STREAMS) {
                streams.put(name, new BufferedWriter(new OutputStreamWriter(new GZIPOutputStream(
                    Files.newOutputStream(directory.resolve(name + ".jsonl.gz"), StandardOpenOption.CREATE_NEW)),
                    StandardCharsets.UTF_8)));
                counts.put(name, 0L);
            }
        } catch (IOException failure) {
            try { close(); } catch (IOException cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    static boolean isReady() { return NEIClientConfig.isLoaded() && ItemList.loadFinished; }

    /** Must run on the client thread after native NEI readiness gates. */
    static void capture(Path directory, JsonObject manifest) throws IOException {
        String scope = System.getProperty("gtnh.data.neiReferenceScope", "all");
        if (!"all".equals(scope) && !"forestry_still".equals(scope) && !"inventory".equals(scope)) {
            throw new IllegalArgumentException("Unsupported NEI reference scope: " + scope);
        }
        if (!isReady()) throw new IllegalStateException("NEI reference capture requested before NEI/item readiness");
        if ("inventory".equals(scope)) {
            captureInventory(directory, manifest);
            return;
        }
        try (NeiReferenceCapture reference = new NeiReferenceCapture(directory, "forestry_still".equals(scope))) {
            if (!reference.stillOnly) reference.presentationContext = NeiPresentationContext.capture(directory, manifest);
            List<ICraftingHandler> handlers = new ArrayList<>(GuiCraftingRecipe.craftinghandlers);
            int parallelCount = handlers.size();
            handlers.addAll(new ArrayList<>(GuiCraftingRecipe.serialCraftingHandlers));
            if (reference.stillOnly && !reference.selectStill(handlers)) {
                reference.publish(manifest);
                return;
            }
            for (int index = 0; index < handlers.size(); index++) {
                if (reference.stillOnly && (handlers.get(index) == null
                    || handlers.get(index).getClass() != NEIHandlerStill.class)) continue;
                reference.handler(handlers.get(index), "h" + index,
                    index < parallelCount ? "craftinghandlers" : "serialCraftingHandlers");
            }
            reference.publish(manifest);
        }
    }

    /** Records retained registrations without invoking handler presentation or recipe methods. */
    static void captureInventory(Path directory, JsonObject manifest) throws IOException {
        captureInventory(directory, manifest, () -> Arrays.<List<?>>asList(GuiCraftingRecipe.craftinghandlers,
            GuiCraftingRecipe.serialCraftingHandlers, GuiUsageRecipe.usagehandlers, GuiUsageRecipe.serialUsageHandlers));
    }

    static void captureInventory(Path directory, JsonObject manifest, Supplier<List<List<?>>> rosterSource) throws IOException {
        String[] names = {"craftinghandlers", "serialCraftingHandlers", "usagehandlers", "serialUsageHandlers"};
        List<List<?>> originals = new ArrayList<>(rosterSource.get());
        if (originals.size() != names.length) throw new IllegalArgumentException("Inventory requires all four native rosters");
        List<List<?>> snapshots = new ArrayList<>();
        for (List<?> roster : originals) synchronized (roster) { snapshots.add(new ArrayList<>(roster)); }
        Inventory inventory = new Inventory(manifest);
        try (NeiReferenceCapture reference = new NeiReferenceCapture(directory, false)) {
            int global = 0;
            JsonObject rosters = new JsonObject();
            for (int roster = 0; roster < names.length; roster++) {
                List<?> snapshot = snapshots.get(roster);
                rosters.addProperty(names[roster], snapshot.size());
                for (int index = 0; index < snapshot.size(); index++)
                    reference.append("handlers", inventory.registration(snapshot.get(index), names[roster], index, global++));
            }
            List<List<?>> current = rosterSource.get();
            boolean references = current.size() == originals.size();
            boolean stable = true;
            for (int roster = 0; roster < names.length; roster++) {
                references &= roster < current.size() && originals.get(roster) == current.get(roster);
                stable &= sameRoster(originals.get(roster), snapshots.get(roster));
            }
            rosters.addProperty("stable", stable);
            rosters.addProperty("references_unchanged", references);
            reference.close();
            JsonObject summary = object("schema_version", 1, "profile", "handler_inventory",
                "canonical_snapshot_id", manifest.get("snapshot_id"), "canonical_pack", manifest.get("pack"),
                "canonical_pack_sha256", Hashing.sha256().hashString(SnapshotWriter.JSON.toJson(manifest.get("pack")), StandardCharsets.UTF_8).toString(),
                "canonical_files", manifest.get("files"), "created_at", Instant.now().toString(),
                "scope", "current retained crafting and usage registration entries, including serial rosters",
                "counts", object("handlers", global, "signatures", 0, "handler_views", 0),
                "rosters", rosters,
                "authority", inventory.authority, "source_census", inventory.sourceCensus,
                "class_counts", inventory.classCounts, "native_files", inventory.nativeFiles(),
                "failed_handlers", inventory.failedRows, "files", reference.fileDeclarations(),
                "signature_projection", "not_applicable", "view_projection", "not_applicable",
                "item_presentation_context", object("status", "not_applicable", "reason", "inventory_only"),
                "complete", references && stable && inventory.failedRows == 0
                    && inventory.authority.get("nei_artifact_verified").getAsBoolean());
            reference.writeSummary(summary);
        }
    }

    private static boolean sameRoster(List<?> actual, List<?> snapshot) {
        synchronized (actual) {
            if (actual.size() != snapshot.size()) return false;
            for (int index = 0; index < actual.size(); index++) if (actual.get(index) != snapshot.get(index)) return false;
            return true;
        }
    }

    /** Resolves one actual class-resource origin without relying on FML protection domains. */
    static JsonObject classResourceOrigin(ClassLoader loader, String resourcePath) {
        JsonObject result = object("status", "unavailable", "basis", "unique_class_resource", "file", null,
            "sha256", null, "owner_candidates", new JsonArray(), "origins", new JsonArray());
        if (loader == null) {
            result.addProperty("reason", "bootstrap_class_loader");
            return result;
        }
        try {
            Set<String> origins = new LinkedHashSet<>();
            Enumeration<URL> resources = loader.getResources(resourcePath);
            while (resources.hasMoreElements()) {
                URL resource = resources.nextElement();
                URI origin;
                if ("jar".equals(resource.getProtocol())) {
                    JarURLConnection connection = (JarURLConnection) resource.openConnection();
                    if (!matchesJarClassResource(connection, resourcePath))
                        throw new IOException("Class resource entry does not match the requested binary name");
                    origin = connection.getJarFileURL().toURI().normalize();
                    if ("file".equals(origin.getScheme())) origin = Paths.get(origin).toRealPath().toUri();
                } else if ("file".equals(resource.getProtocol())) {
                    Path classFile = Paths.get(resource.toURI()).toRealPath();
                    if (!classFile.endsWith(Paths.get(resourcePath)))
                        throw new IOException("Class resource path does not match the requested binary name");
                    Path root = classFile;
                    for (int part = 0; part < Paths.get(resourcePath).getNameCount(); part++) root = root.getParent();
                    origin = root.toRealPath().toUri();
                } else origin = resource.toURI().normalize();
                origins.add(origin.toString());
            }
            result.add("origins", SnapshotWriter.JSON.toJsonTree(origins));
            if (origins.size() != 1) {
                result.addProperty("reason", origins.isEmpty() ? "class_resource_missing" : "ambiguous_class_origins");
                return result;
            }
            URI origin = URI.create(origins.iterator().next());
            if (!"file".equals(origin.getScheme())) {
                result.addProperty("reason", "unsupported_resource_origin");
                return result;
            }
            Path path = Paths.get(origin);
            result.addProperty("file", path.getFileName() == null ? null : path.getFileName().toString());
            if (Files.isRegularFile(path)) result.addProperty("status", "jar");
            else if (Files.isDirectory(path)) result.addProperty("status", "directory");
            else result.addProperty("reason", "resource_origin_unavailable");
        } catch (Exception | LinkageError error) {
            result.addProperty("status", "failed");
            result.add("failure", failure("class_resource_origin", error));
        }
        return result;
    }

    static boolean matchesJarClassResource(JarURLConnection connection, String resourcePath) throws IOException {
        String entry = connection.getEntryName();
        if (resourcePath.equals(entry)) return true;
        Matcher versioned = Pattern.compile("META-INF/versions/([1-9][0-9]*)/" + Pattern.quote(resourcePath)).matcher(entry);
        if (!versioned.matches()) return false;
        try {
            if (Integer.parseInt(versioned.group(1)) < 9) return false;
        } catch (NumberFormatException invalidVersion) {
            return false;
        }
        java.util.jar.Manifest manifest = connection.getManifest();
        return manifest != null && Boolean.parseBoolean(manifest.getMainAttributes().getValue("Multi-Release"));
    }

    /** Reflection facts and verified native field bindings, separate from handler execution. */
    private static final class Inventory {
        private final JsonObject manifest;
        private final Map<String, JsonObject> artifacts = new LinkedHashMap<>();
        private final IdentityHashMap<Object, String> objects = new IdentityHashMap<>();
        private final IdentityHashMap<Object, String> firstRegistrations = new IdentityHashMap<>();
        private final JsonObject authority;
        private final JsonObject classCounts = new JsonObject();
        private final JsonObject sourceCensus = object("mapped", 0, "unresolved", 0, "unsupported_profile", 0, "failed", 0);
        private int failedRows;

        Inventory(JsonObject manifest) {
            this.manifest = manifest;
            JsonObject nei = component("NotEnoughItems");
            JsonObject gt = component("gregtech");
            JsonObject neiSource = source(GuiCraftingRecipe.class);
            JsonObject gtSource = source(GTNEIDefaultHandler.class);
            boolean neiVerified = verified(nei, neiSource);
            boolean gtVerified = verified(gt, gtSource);
            JsonArray failures = new JsonArray();
            if (neiSource.has("failure")) failures.add(neiSource.get("failure"));
            if (gtSource.has("failure")) failures.add(gtSource.get("failure"));
            authority = object("status", neiVerified ? "verified" : "unsupported", "nei", nei, "gt", gt,
                "nei_artifact_verified", neiVerified, "gt_artifact_verified", gtVerified, "failures", failures,
                "class_origin_basis", "unique_class_resource");
        }

        private JsonObject component(String id) {
            for (JsonElement value : manifest.getAsJsonObject("pack").getAsJsonArray("mods")) {
                JsonObject mod = value.getAsJsonObject();
                if (id.equals(mod.get("id").getAsString())) return mod;
            }
            return null;
        }

        private static boolean verified(JsonObject mod, JsonObject source) {
            return mod != null && !mod.get("sha256").isJsonNull() && !source.get("sha256").isJsonNull()
                && mod.get("sha256").getAsString().equals(source.get("sha256").getAsString());
        }

        private JsonObject source(Class<?> type) {
            JsonObject result = classResourceOrigin(type.getClassLoader(), type.getName().replace('.', '/') + ".class");
            if (!"jar".equals(result.get("status").getAsString()) && !"directory".equals(result.get("status").getAsString()))
                return result;
            String location = result.getAsJsonArray("origins").get(0).getAsString();
            JsonObject cached = artifacts.get(location);
            if (cached != null) return cached;
            try {
                if ("jar".equals(result.get("status").getAsString())) {
                    String digest = SnapshotWriter.sha256(Paths.get(URI.create(location)));
                    result.addProperty("sha256", digest);
                    for (JsonElement value : manifest.getAsJsonObject("pack").getAsJsonArray("mods")) {
                        JsonObject mod = value.getAsJsonObject();
                        if (!mod.get("sha256").isJsonNull() && digest.equals(mod.get("sha256").getAsString()))
                            result.getAsJsonArray("owner_candidates").add(mod);
                    }
                }
            } catch (Exception | LinkageError error) {
                result.addProperty("status", "failed");
                result.add("failure", failure("class_source", error));
            }
            artifacts.put(location, result);
            return result;
        }

        JsonObject registration(Object handler, String roster, int index, int global) {
            String key = "h" + global;
            JsonArray failures = new JsonArray();
            JsonArray hierarchy = new JsonArray();
            Set<String> interfaces = new LinkedHashSet<>();
            JsonObject binding = object("status", "unresolved", "profile", null, "api", null,
                "source_ids", new JsonArray(), "map_name", null, "map_registry_keys", new JsonArray(), "map_class", null);
            JsonObject row = object("registration_key", key, "registration", roster, "registration_index", index,
                "global_index", global, "object_key", null, "same_instance_as", null,
                "native_class", null, "hierarchy", hierarchy, "interfaces", interfaces, "native_source", binding, "failures", failures);
            if (handler == null) {
                binding.addProperty("status", "failed");
                failures.add(object("phase", "registration", "class", "null", "message", "Null retained handler"));
            } else {
                if (!objects.containsKey(handler)) {
                    objects.put(handler, "o" + objects.size());
                    firstRegistrations.put(handler, key);
                } else row.addProperty("same_instance_as", firstRegistrations.get(handler));
                row.addProperty("object_key", objects.get(handler));
                Class<?> type = handler.getClass();
                row.addProperty("native_class", type.getName());
                increment(classCounts, type.getName());
                try {
                    for (Class<?> owner = type; owner != null; owner = owner.getSuperclass()) {
                        JsonObject source = source(owner);
                        hierarchy.add(object("class", owner.getName(), "source", source));
                        if (source.has("failure")) failures.add(source.get("failure"));
                        interfaces(owner, interfaces);
                    }
                    row.add("interfaces", SnapshotWriter.JSON.toJsonTree(interfaces));
                    bind(handler, binding, failures);
                } catch (Exception | LinkageError error) {
                    failures.add(failure("class_hierarchy", error));
                }
            }
            if (failures.size() != 0) failedRows++;
            increment(sourceCensus, binding.get("status").getAsString());
            return row;
        }

        private static void interfaces(Class<?> type, Set<String> names) {
            for (Class<?> contract : type.getInterfaces()) {
                if (names.add(contract.getName())) interfaces(contract, names);
            }
        }

        private void bind(Object handler, JsonObject binding, JsonArray failures) {
            if (!(handler instanceof GTNEIDefaultHandler)) return;
            binding.addProperty("profile", "gt_nei_recipe_map_field_v1");
            binding.addProperty("api", "gregtech.nei.GTNEIDefaultHandler.recipeMap");
            if (!authority.get("gt_artifact_verified").getAsBoolean()) {
                binding.addProperty("status", "unsupported_profile");
                return;
            }
            try {
                java.lang.reflect.Field field = GTNEIDefaultHandler.class.getDeclaredField("recipeMap");
                field.setAccessible(true);
                RecipeMap<?> map = (RecipeMap<?>) field.get(handler);
                if (map == null) return;
                binding.addProperty("map_name", map.unlocalizedName);
                binding.addProperty("map_class", map.getClass().getName());
                List<String> keys = new ArrayList<>();
                for (Map.Entry<String, RecipeMap<?>> entry : RecipeMap.ALL_RECIPE_MAPS.entrySet())
                    if (entry.getValue() == map) keys.add(entry.getKey());
                Collections.sort(keys);
                for (String registryKey : keys) {
                    binding.getAsJsonArray("map_registry_keys").add(new JsonPrimitive(registryKey));
                    binding.getAsJsonArray("source_ids").add(new JsonPrimitive("gregtech:" + registryKey));
                }
                if (!keys.isEmpty()) binding.addProperty("status", "mapped");
            } catch (Exception | LinkageError error) {
                binding.addProperty("status", "failed");
                failures.add(failure("native_source", error));
            }
        }

        private static void increment(JsonObject counts, String key) {
            counts.addProperty(key, counts.has(key) ? counts.get(key).getAsInt() + 1 : 1);
        }

        JsonArray nativeFiles() {
            JsonArray files = new JsonArray();
            for (JsonObject artifact : artifacts.values()) files.add(artifact);
            return files;
        }
    }

    private boolean selectStill(List<ICraftingHandler> handlers) {
        for (ICraftingHandler handler : handlers) {
            if (handler != null && handler.getClass() == NEIHandlerStill.class) selectedHandlers++;
            else excludedHandlers++;
        }
        try {
            if (selectedHandlers != 1) {
                selectionFailure = object("reason", selectedHandlers == 0 ? "missing_still_handler" : "duplicate_still_handlers");
            } else if (RecipeManagers.stillManager == null || RecipeManagers.stillManager.getClass() != StillRecipeManager.class) {
                selectionFailure = object("reason", "unsupported_still_manager");
            } else {
                for (IStillRecipe recipe : RecipeManagers.stillManager.recipes()) {
                    if (recipe == null || recipe.getClass() != StillRecipe.class) {
                        selectionFailure = object("reason", "unsupported_native_recipe_class",
                            "native_class", recipe == null ? null : recipe.getClass().getName());
                        break;
                    }
                }
            }
        } catch (RuntimeException | LinkageError error) {
            selectionFailure = object("reason", "still_preflight_failed", "failure", failure("still_preflight", error));
        }
        return selectionFailure == null;
    }

    private void handler(ICraftingHandler original, String key, String registration) throws IOException {
        LOG.info("NEI reference enumerates {} from {} ({})", key, registration, original.getClass().getName());
        JsonObject record = object("handler_key", key, "native_class", original.getClass().getName(),
            "handler_id", null, "handler_name", null, "gt_recipe_map_id", null,
            "registration", registration, "enumeration_status", "failed", "recipe_count", null, "failure", null);
        ICraftingHandler handler;
        int size;
        try {
            record.addProperty("handler_id", original.getHandlerId());
            record.addProperty("handler_name", original.getRecipeName());
            if (stillOnly) {
                String recipeId = ((NEIHandlerStill) original).getRecipeID();
                record.addProperty("native_recipe_id", recipeId);
                if (!"forestry.still".equals(recipeId)) throw new IllegalStateException("Unsupported native Still recipe ID");
            }
            handler = original instanceof TemplateRecipeHandler
                ? ((TemplateRecipeHandler) original).getAllRecipeHandler() : original.getRecipeHandler("all");
            if (handler == null) throw new IllegalStateException("Native all-recipes query returned null");
            record.addProperty("queried_native_class", handler.getClass().getName());
            if (stillOnly && handler.getClass() != NEIHandlerStill.class) {
                throw new IllegalStateException("Unsupported queried Still handler class");
            }
            if (handler.getClass() == GTNEIDefaultHandler.class) {
                record.addProperty("gt_recipe_map_id", "gregtech:" + ((GTNEIDefaultHandler) handler).getRecipeMap().unlocalizedName);
            }
            record.add("getter_declaring_classes", object(
                "ingredients", handler.getClass().getMethod("getIngredientStacks", int.class).getDeclaringClass().getName(),
                "result", handler.getClass().getMethod("getResultStack", int.class).getDeclaringClass().getName(),
                "other_stacks", handler.getClass().getMethod("getOtherStacks", int.class).getDeclaringClass().getName()));
            size = handler.numRecipes();
            if (size < 0) throw new IllegalStateException("Native handler returned negative recipe count");
            record.addProperty("recipe_count", size);
            record.addProperty("enumeration_status", size == 0 ? "empty" : "ok");
            if (size == 0) emptyHandlers++;
        } catch (Exception | LinkageError failure) {
            failedHandlers++;
            record.add("failure", failure("handler_enumeration", failure));
            append("handlers", record);
            return;
        }
        append("handlers", record);
        for (int index = 0; index < size; index++) {
            if (!stillOnly) signature(handler, key, index);
            view(handler, key, index);
        }
    }

    private void signature(ICraftingHandler handler, String key, int index) throws IOException {
        JsonObject record = object("handler_key", key, "recipe_index", index,
            "projection", "native_recipe_id_api", "signature", null, "failure", null);
        try { record.add("signature", Recipe.of(handler, index).getRecipeId().toJsonObject()); }
        catch (RuntimeException | LinkageError error) {
            failedSignatures++;
            record.add("failure", failure("native_recipe_id_api", error));
        }
        append("signatures", record);
    }

    private void view(ICraftingHandler handler, String key, int index) throws IOException {
        JsonObject record = object("handler_key", key, "recipe_index", index,
            "ingredients", null, "result", null, "other_stacks", null, "displayed_fields", null, "failure", null);
        JsonArray failures = new JsonArray();
        boolean mapped = handler.getClass() == GTNEIDefaultHandler.class;
        try { record.add("ingredients", positionedList(handler.getIngredientStacks(index), mapped)); }
        catch (RuntimeException | LinkageError error) { failures.add(failure("ingredients", error)); }
        try { record.add("result", positioned(handler.getResultStack(index), mapped)); }
        catch (RuntimeException | LinkageError error) { failures.add(failure("result", error)); }
        try { record.add("other_stacks", positionedList(handler.getOtherStacks(index), mapped)); }
        catch (RuntimeException | LinkageError error) { failures.add(failure("other_stacks", error)); }
        try {
            JsonObject displayed = object("recipe_height", handler.getRecipeHeight(index),
                "recipe_tab_name", handler.getRecipeTabName(), "overlay_identifier", handler.getOverlayIdentifier());
            if (mapped) {
                RecipeMap<?> map = ((GTNEIDefaultHandler) handler).getRecipeMap();
                displayed.addProperty("frontend_class", map.getFrontend().getClass().getName());
                displayed.addProperty("render_real_stack_sizes", map.getFrontend().getNEIProperties().renderRealStackSizes);
                displayed.addProperty("unificate_output", map.getFrontend().getNEIProperties().unificateOutput);
            }
            record.add("displayed_fields", displayed);
        } catch (RuntimeException | LinkageError error) { failures.add(failure("displayed_fields", error)); }
        if (stillOnly) {
            JsonObject tanks = stillTanks((NEIHandlerStill) handler, index);
            if ("captured".equals(tanks.get("status").getAsString()) && failures.size() == 0
                && (record.getAsJsonArray("ingredients").size() != 0 || !record.get("result").isJsonNull()
                    || record.getAsJsonArray("other_stacks").size() != 0)) {
                tanks.addProperty("status", "unsupported");
                tanks.addProperty("reason", "generic_item_view_not_empty");
            }
            String status = tanks.get("status").getAsString();
            if ("captured".equals(status)) capturedTanks++;
            else if ("unsupported".equals(status)) unsupportedTanks++;
            else {
                failedTanks++;
                failures.add(tanks.get("failure"));
            }
            record.add("forestry_still_tanks", tanks);
        }
        if (failures.size() != 0) {
            failedViews++;
            record.add("failure", failures.get(0));
        }
        record.add("failures", failures);
        append("handler-views", record);
    }

    private JsonObject stillTanks(NEIHandlerStill handler, int index) {
        JsonArray observations = new JsonArray();
        JsonObject result = object("status", "unsupported", "quantity_scope", "unscaled_per_unit_templates",
            "cached_recipe_class", null, "source_api", "forestry.factory.recipes.nei.NEIHandlerStill$CachedStillRecipe.getFluidTanks",
            "getter_declaring_class", null, "tanks", observations, "reason", null, "failure", null);
        try {
            TemplateRecipeHandler.CachedRecipe cached = handler.arecipes.get(index);
            result.addProperty("cached_recipe_class", cached == null ? null : cached.getClass().getName());
            if (cached == null || cached.getClass() != NEIHandlerStill.CachedStillRecipe.class) {
                result.addProperty("reason", "unsupported_cached_recipe_class");
                return result;
            }
            result.addProperty("getter_declaring_class", cached.getClass().getMethod("getFluidTanks").getDeclaringClass().getName());
            List<PositionedFluidTank> tanks = ((NEIHandlerStill.CachedStillRecipe) cached).getFluidTanks();
            if (tanks == null) {
                result.addProperty("reason", "native_tank_list_is_null");
                return result;
            }
            boolean supported = tanks.size() == 2;
            for (int ordinal = 0; ordinal < tanks.size(); ordinal++) {
                PositionedFluidTank tank = tanks.get(ordinal);
                JsonArray alternatives = new JsonArray();
                JsonObject observation = object("ordinal", ordinal, "native_class", tank == null ? null : tank.getClass().getName(),
                    "position", null, "show_amount", null, "per_tick", null, "alternatives", alternatives);
                observations.add(observation);
                if (tank == null) {
                    supported = false;
                    continue;
                }
                observation.addProperty("show_amount", tank.showAmount);
                observation.addProperty("per_tick", tank.perTick);
                if (tank.position != null) observation.add("position", object("x", tank.position.x, "y", tank.position.y,
                    "width", tank.position.width, "height", tank.position.height));
                supported &= tank.getClass() == PositionedFluidTank.class && tank.position != null
                    && tank.position.x == (ordinal == 0 ? 30 : 120) && tank.position.y == 4
                    && tank.position.width == 16 && tank.position.height == 58 && tank.showAmount && !tank.perTick;
                if (tank.tanks == null) {
                    supported = false;
                    continue;
                }
                supported &= tank.tanks.length == 1;
                for (int alternative = 0; alternative < tank.tanks.length; alternative++) {
                    FluidTank nativeTank = tank.tanks[alternative];
                    JsonObject value = object("ordinal", alternative,
                        "native_class", nativeTank == null ? null : nativeTank.getClass().getName(), "capacity", null, "fluid", null);
                    alternatives.add(value);
                    if (nativeTank == null || nativeTank.getClass() != FluidTank.class) {
                        supported = false;
                        continue;
                    }
                    value.addProperty("capacity", nativeTank.getCapacity());
                    FluidStack fluid = nativeTank.getFluid();
                    if (fluid == null) {
                        supported = false;
                        continue;
                    }
                    String registry = fluid.getFluid() == null ? null : FluidRegistry.getFluidName(fluid.getFluid());
                    value.add("fluid", object("registry_name", registry, "amount", fluid.amount, "nbt", TypedNbt.encode(fluid.tag)));
                    supported &= nativeTank.getCapacity() == 10000 && registry != null && fluid.amount > 0;
                }
            }
            result.addProperty("status", supported ? "captured" : "unsupported");
            if (!supported) result.addProperty("reason", "unsupported_native_tank_shape");
        } catch (ReflectiveOperationException | RuntimeException | LinkageError error) {
            result.addProperty("status", "failed");
            result.add("failure", failure("forestry_still_tanks", error));
        }
        return result;
    }

    private JsonArray positionedList(List<PositionedStack> stacks, boolean mapped) {
        if (stacks == null) throw new IllegalStateException("Native positioned-stack list is null");
        JsonArray result = new JsonArray();
        for (PositionedStack stack : stacks) result.add(positioned(stack, mapped));
        return result;
    }

    private JsonElement positioned(PositionedStack stack, boolean mapped) {
        if (stack == null) return JsonNull.INSTANCE;
        JsonObject result = object("x", stack.relx, "y", stack.rely, "native_class", stack.getClass().getName(),
            "chance", stack.getChance(), "chance_semantics", "native_presentation_default_may_be_full",
            "real_stack_size", null, "alternatives", null);
        if (mapped && stack instanceof GTNEIDefaultHandler.FixedPositionedStack) {
            result.addProperty("real_stack_size", ((GTNEIDefaultHandler.FixedPositionedStack) stack).realStackSize);
        }
        if (stack.items == null) throw new IllegalStateException("Native positioned-stack alternatives are null");
        JsonArray alternatives = new JsonArray();
        for (ItemStack item : stack.items) {
            JsonObject alternative = object("native_stack", null, "failure", null, "item_facts", null,
                "item_facts_failure", null, "serializer_class", null, "count_semantics", "unknown");
            if (item != null) {
                ItemStack detached;
                try {
                    detached = item.copy();
                } catch (RuntimeException | LinkageError error) {
                    failedItemFacts++;
                    failedStacks++;
                    alternative.add("item_facts_failure", failure("item_facts_copy", error));
                    alternative.add("failure", failure("native_stack_copy", error));
                    alternatives.add(alternative);
                    continue;
                }
                try {
                    alternative.add("item_facts", NeiPresentationContext.itemFacts(detached));
                } catch (RuntimeException | LinkageError error) {
                    failedItemFacts++;
                    alternative.add("item_facts_failure", failure("item_facts", error));
                }
                try {
                    Map.Entry<codechicken.nei.api.IStackStringifyHandler, NBTTagCompound> selected =
                        NeiPresentationContext.dispatchItem(detached, true, StackInfo.stackStringifyHandlers);
                    if (selected == null) throw new IllegalStateException("NEI StackInfo serializer returned null");
                    NBTTagCompound nativeNbt = selected.getValue();
                    String serializer = selected.getKey().getClass().getName();
                    alternative.addProperty("serializer_class", serializer);
                    if (!alternative.get("item_facts").isJsonNull()) alternative.addProperty("count_semantics",
                        NeiPresentationContext.itemCountSemantics(alternative.getAsJsonObject("item_facts"), nativeNbt, serializer));
                    alternative.add("native_stack", NBTJson.toJsonObject(nativeNbt));
                } catch (RuntimeException | LinkageError error) {
                    failedStacks++;
                    alternative.add("failure", failure("native_stack", error));
                }
            }
            alternatives.add(alternative);
        }
        result.add("alternatives", alternatives);
        return result;
    }

    private static JsonObject failure(String phase, Throwable error) {
        LOG.warn("NEI reference {} failed: {}", phase, error.toString());
        return object("phase", phase, "class", error.getClass().getName(), "message", error.getMessage());
    }

    private void append(String stream, JsonObject record) throws IOException {
        BufferedWriter target = streams.get(stream);
        target.write(SnapshotWriter.JSON.toJson(record));
        target.newLine();
        counts.put(stream, counts.get(stream) + 1L);
    }

    private JsonObject fileDeclarations() throws IOException {
        JsonObject files = new JsonObject();
        for (String name : STREAMS) {
            String filename = name + ".jsonl.gz";
            files.add(filename, object("records", counts.get(name), "sha256", SnapshotWriter.sha256(directory.resolve(filename))));
        }
        return files;
    }

    private void publish(JsonObject manifest) throws IOException {
        close();
        JsonObject files = fileDeclarations();
        if (!stillOnly) files.add("presentation-context.json", presentationContext);
        JsonObject summary = object("schema_version", 2, "canonical_snapshot_id", manifest.get("snapshot_id"),
            "canonical_pack", manifest.get("pack"), "created_at", Instant.now().toString(),
            "counts", object("handlers", counts.get("handlers"), "signatures", counts.get("signatures"),
                "handler_views", counts.get("handler-views")),
            "complete", failedHandlers + failedSignatures + failedViews + failedStacks + failedItemFacts == 0,
            "scope", "registered crafting and serial crafting all-recipes queries, not all pack recipes",
            "signature_projection", "native_recipe_id_api", "view_projection", "raw_handler_view",
            "recipeid_blacklist_applied", false, "skipped_handlers", 0, "empty_handlers", emptyHandlers,
            "readiness", object("nei_loaded", true, "item_list_load_finished", true,
                "canonical_capture_after_nei_ready", true),
            "settings", object("config_digest_source", "canonical_pack.config_script_digests",
                "native_handler_filters", "uninterpreted", "recipeid_blacklist_applied", false),
            "failed_handlers", failedHandlers, "failed_signatures", failedSignatures, "failed_views", failedViews,
            "failed_stacks", failedStacks, "failed_item_facts", failedItemFacts, "chance_semantics", "native_presentation_default_may_be_full",
            "nbt_semantics", "verbatim NEI NBTJson projection, not typed canonical NBT", "files", files);
        if (stillOnly) {
            summary.addProperty("schema_version", 3);
            summary.addProperty("profile", "forestry_still");
            summary.add("canonical_files", manifest.getAsJsonObject("files"));
            summary.addProperty("signature_projection", "not_applicable_fluid_tank_profile");
            summary.addProperty("view_projection", "forestry_still_fluid_tanks_v1");
            summary.addProperty("scope", "exact Forestry Still handler unscaled fluid tank templates only");
            summary.addProperty("skipped_handlers", excludedHandlers);
            summary.addProperty("nbt_semantics", "typed native FluidStack tags, not NEI item serialization");
            summary.add("selection", object("selected_handlers", selectedHandlers, "excluded_handlers", excludedHandlers,
                "failure", selectionFailure));
            summary.add("tank_observations", object("captured", capturedTanks, "unsupported", unsupportedTanks, "failed", failedTanks));
            summary.add("item_presentation_context", object("status", "not_applicable", "reason", "fluid_only_profile"));
            summary.addProperty("complete", summary.get("complete").getAsBoolean() && selectionFailure == null
                && selectedHandlers == 1 && capturedTanks > 0 && unsupportedTanks == 0 && failedTanks == 0
                && capturedTanks == counts.get("handler-views"));
        } else summary.add("handler_item_facts", object("version", 1, "stage", "before_native_serialization",
            "identity", "registry_metadata_typed_nbt", "quantity", "positioned_item_stack_size",
            "native_input", "detached_positioned_copy",
            "native_api", "StackInfo.stackStringifyHandlers.reverse.convertItemStackToNBT(stack,true)->NBTJson.toJsonObject",
            "count_classification", "selected_default_at_observed_quantity"));
        JsonElement nei = JsonNull.INSTANCE;
        for (JsonElement mod : manifest.getAsJsonObject("pack").getAsJsonArray("mods")) {
            if ("NotEnoughItems".equalsIgnoreCase(mod.getAsJsonObject().get("id").getAsString())) nei = mod;
        }
        summary.add("native_nei", nei);
        writeSummary(summary);
    }

    private void writeSummary(JsonObject summary) throws IOException {
        Path temporary = directory.resolve("summary.json.tmp");
        Files.write(temporary, SnapshotWriter.JSON.toJson(summary).getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        Files.move(temporary, directory.resolve("summary.json"), StandardCopyOption.ATOMIC_MOVE);
    }

    @Override
    public void close() throws IOException {
        if (closed) return;
        closed = true;
        IOException failure = null;
        for (BufferedWriter stream : streams.values()) {
            try { stream.close(); }
            catch (IOException error) {
                if (failure == null) failure = error;
                else failure.addSuppressed(error);
            }
        }
        if (failure != null) throw failure;
    }
}
