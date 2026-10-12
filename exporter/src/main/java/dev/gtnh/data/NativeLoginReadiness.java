package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import cpw.mods.fml.common.network.FMLEmbeddedChannel;
import cpw.mods.fml.common.network.NetworkRegistry;
import cpw.mods.fml.common.network.simpleimpl.SimpleChannelHandlerWrapper;
import cpw.mods.fml.common.network.simpleimpl.SimpleIndexedCodec;
import cpw.mods.fml.relauncher.Side;
import io.netty.channel.ChannelHandler;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import java.util.Map;

/** Observes the native CoreMod login policy being applied before a canonical capture. */
final class NativeLoginReadiness extends ChannelInboundHandlerAdapter {
    private static final String OWNER = "dreamcraft";
    private static final String VERSION = "2.9.88";
    private static final String MESSAGE_TYPE = "com.dreammaster.network.msg.ZZClientOnlySyncMessage";
    private static final String NATIVE_HANDLER_TYPE = MESSAGE_TYPE + "$ZZClientOnlySyncMessageHandler";
    private final SimpleChannelHandlerWrapper<?, ?> nativeHandler;
    private final String pipelineHandlerName;
    private volatile boolean completed;
    private volatile Throwable failure;

    private NativeLoginReadiness(SimpleChannelHandlerWrapper<?, ?> nativeHandler, String pipelineHandlerName) {
        this.nativeHandler = nativeHandler;
        this.pipelineHandlerName = pipelineHandlerName;
    }

    static NativeLoginReadiness install() {
        ModContainer owner = Loader.instance().getIndexedModList().get(OWNER);
        if (owner == null || !VERSION.equals(owner.getVersion()))
            throw new IllegalStateException("Native login readiness requires CoreMod " + VERSION);
        FMLEmbeddedChannel channel = NetworkRegistry.INSTANCE.getChannel(OWNER, Side.CLIENT);
        if (channel == null || channel.attr(NetworkRegistry.CHANNEL_SOURCE).get() != Side.CLIENT
            || !OWNER.equals(channel.attr(NetworkRegistry.FML_CHANNEL).get()))
            throw new IllegalStateException("Native CoreMod client channel is unavailable");
        // CoreMod 2.9.88 registers only this one client message on its channel.
        // ModularUI2 generates wrapper names, so protocol ownership identifies the target.
        String handlerName = null;
        SimpleChannelHandlerWrapper<?, ?> wrapper = null;
        int wrapperCount = 0;
        for (Map.Entry<String, ChannelHandler> entry : channel.pipeline()) {
            if (entry.getValue().getClass() == SimpleChannelHandlerWrapper.class) {
                wrapperCount++;
                handlerName = entry.getKey();
                wrapper = (SimpleChannelHandlerWrapper<?, ?>) entry.getValue();
            }
        }
        ChannelHandlerContext codec = channel.pipeline().context(SimpleIndexedCodec.class);
        if (wrapperCount != 1 || codec == null
            || channel.pipeline().names().indexOf(codec.name()) >= channel.pipeline().names().indexOf(handlerName))
            throw unsupportedRegistration(channel, codec, handlerName, wrapper, wrapperCount);
        NativeLoginReadiness readiness = new NativeLoginReadiness(wrapper, handlerName);
        channel.pipeline().replace(handlerName, handlerName, readiness);
        return readiness;
    }

    private static IllegalStateException unsupportedRegistration(FMLEmbeddedChannel channel,
        ChannelHandlerContext codec, String handlerName, ChannelHandler target, int wrapperCount) {
        JsonArray layout = new JsonArray();
        int count = 0;
        for (Map.Entry<String, ChannelHandler> entry : channel.pipeline()) {
            if (count++ < 32) layout.add(object("name", entry.getKey(),
                "class", entry.getValue().getClass().getName(), "identity", System.identityHashCode(entry.getValue())));
        }
        JsonObject details = object("expected_native_handler", NATIVE_HANDLER_TYPE,
            "selection", "single_exact_fml_wrapper_on_coremod_client_channel", "wrapper_count", wrapperCount,
            "target_name", handlerName, "target_class", target == null ? null : target.getClass().getName(),
            "target_identity", target == null ? null : System.identityHashCode(target),
            "target_position", channel.pipeline().names().indexOf(handlerName),
            "codec_name", codec == null ? null : codec.name(),
            "codec_class", codec == null ? null : codec.handler().getClass().getName(),
            "codec_identity", codec == null ? null : System.identityHashCode(codec.handler()),
            "codec_position", codec == null ? -1 : channel.pipeline().names().indexOf(codec.name()),
            "pipeline", layout, "pipeline_entries", count, "omitted_entries", Math.max(0, count - 32));
        return new IllegalStateException("Unsupported native CoreMod login handler registration: " + details);
    }

    @Override
    public void channelRead(ChannelHandlerContext context, Object message) throws Exception {
        boolean loginPolicy = MESSAGE_TYPE.equals(message.getClass().getName());
        try {
            // The native type matcher verifies loader identity, not just the binary class name.
            if (loginPolicy && !nativeHandler.acceptInboundMessage(message))
                throw new IllegalStateException("Native CoreMod handler rejected the actual login policy message type");
            // Invoke the original instance directly so a failed native call cannot publish completion.
            nativeHandler.channelRead(context, message);
            if (loginPolicy) completed = true;
        } catch (Exception | Error error) {
            if (loginPolicy) failure = error;
            throw error;
        }
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext context, Throwable cause) throws Exception {
        nativeHandler.exceptionCaught(context, cause);
    }

    boolean isReady() {
        if (failure != null) throw new IllegalStateException("Native CoreMod login policy failed", failure);
        return completed;
    }

    JsonObject evidence() {
        return object("owner", OWNER, "version", VERSION, "channel", OWNER,
            "method", "native_client_message_handler_returned",
            "message_type", MESSAGE_TYPE, "native_handler_type", NATIVE_HANDLER_TYPE,
            "pipeline_handler_name", pipelineHandlerName,
            "registration_basis", "CoreMod 2.9.88 single client message wrapper",
            "runtime_layout", "ModularUI2 2.3.92 generates pipeline wrapper names",
            "policy_application", "native_owner_handled_actual_message", "completed", completed,
            "status", failure != null ? "error" : completed ? "complete" : "pending",
            "failure", failure == null ? null : failure.toString());
    }
}
