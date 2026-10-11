package dev.gtnh.data;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.LoaderState;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.event.FMLLoadCompleteEvent;
import cpw.mods.fml.common.event.FMLServerStartedEvent;
import cpw.mods.fml.common.event.FMLServerStoppedEvent;
import cpw.mods.fml.common.eventhandler.EventPriority;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import gregtech.api.enums.GTValues;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.client.Minecraft;
import net.minecraft.world.WorldSettings;
import net.minecraft.world.WorldType;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Opt-in capture from a freshly bootstrapped integrated world, then process termination. */
@Mod(modid = "gtnhdataexporter", name = "GTNH Data Exporter", version = Tags.VERSION,
    dependencies = "required-after:gregtech", acceptableRemoteVersions = "*")
public final class DataExporterMod {
    private static final Logger LOG = LogManager.getLogger("GTNHDataExporter");
    private volatile boolean loadComplete;
    private volatile boolean serverStarted;
    private volatile boolean worldRequested;
    private volatile boolean captureStarted;
    private String worldName;
    private final CountDownLatch bootstrapSettled = new CountDownLatch(1);
    private final AtomicBoolean failureReported = new AtomicBoolean();

    @Mod.EventHandler
    public void initialize(FMLInitializationEvent event) {
        if (Boolean.getBoolean("gtnh.data.autorun") && event.getSide().isClient()) {
            FMLCommonHandler.instance().bus().register(this);
        }
    }

    @Mod.EventHandler
    public void loadComplete(FMLLoadCompleteEvent event) { loadComplete = true; }

    @Mod.EventHandler
    public void serverStarted(FMLServerStartedEvent event) { serverStarted = true; }

    @Mod.EventHandler
    public void serverStopped(FMLServerStoppedEvent event) {
        if (worldRequested && !captureStarted) fail(new IllegalStateException(
            "Integrated server stopped before capture readiness. Inspect the native server-start error"));
    }

    @SubscribeEvent
    public void clientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || worldRequested || !loadComplete
            || !Loader.instance().hasReachedState(LoaderState.AVAILABLE)) return;
        worldRequested = true;
        Minecraft client = Minecraft.getMinecraft();
        if (client.theWorld != null || client.isIntegratedServerRunning()) {
            fail(new IllegalStateException("Autorun requires a fresh isolated client, not an existing world"));
            return;
        }
        worldName = "gtnh-data-capture-" + UUID.randomUUID();
        LOG.info("GTNH data capture bootstraps isolated world {} after FML load-complete", worldName);
        try {
            startBootstrapDeadline();
            // GT world generators use XSTR, whose zero seed produces an all-zero stream.
            WorldSettings settings = new WorldSettings(1L, WorldSettings.GameType.CREATIVE, false, false, WorldType.FLAT);
            settings.enableCommands();
            client.launchIntegratedServer(worldName, worldName, settings);
        } catch (Throwable failure) { fail(failure); }
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public void serverTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || captureStarted || !serverStarted || !loadComplete
            || !GTValues.worldTickHappened) return;
        Minecraft client = Minecraft.getMinecraft();
        if (client.theWorld == null || client.thePlayer == null || !client.isIntegratedServerRunning()) return;
        captureStarted = true;
        bootstrapSettled.countDown();
        try {
            String output = System.getProperty("gtnh.data.outputDir");
            if (output == null || output.trim().isEmpty()) throw new IllegalArgumentException("gtnh.data.outputDir is required");
            Path directory = Paths.get(output).toAbsolutePath();
            if (directory.getParent() != null) java.nio.file.Files.createDirectories(directory.getParent());
            LOG.info("GT first-world callbacks finished and client attached. Capturing native data at {}", directory);
            try (SnapshotWriter writer = new SnapshotWriter(directory)) {
                NativeCapture capture = new NativeCapture(writer);
                capture.capture();
                writer.publish(capture.manifest(client.mcDataDir.toPath(), worldName,
                    client.getIntegratedServer().worldServerForDimension(0).getSeed()));
            }
            LOG.info("GTNH data snapshot published at {}", directory.resolve("manifest.json"));
            FMLCommonHandler.instance().exitJava(0, false);
        } catch (Throwable failure) { fail(failure); }
    }

    private void fail(Throwable failure) {
        bootstrapSettled.countDown();
        if (!failureReported.compareAndSet(false, true)) return;
        LOG.error("GTNH data capture failed. No valid snapshot has been published", failure);
        FMLCommonHandler.instance().exitJava(2, false);
    }

    private void startBootstrapDeadline() {
        final long seconds = Long.parseLong(System.getProperty("gtnh.data.bootstrapTimeoutSeconds", "180"));
        if (seconds <= 0) throw new IllegalArgumentException("gtnh.data.bootstrapTimeoutSeconds must be positive");
        Thread watchdog = new Thread(() -> {
            try {
                if (!bootstrapSettled.await(seconds, TimeUnit.SECONDS)) fail(new IllegalStateException(
                    "Integrated-world bootstrap exceeded " + seconds + " seconds. loadComplete=" + loadComplete
                        + ", serverStarted=" + serverStarted + ", gtFirstWorldTick=" + GTValues.worldTickHappened));
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
            }
        }, "gtnh-data-bootstrap-deadline");
        watchdog.setDaemon(true);
        watchdog.start();
    }
}
