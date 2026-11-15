// FSR1 presentation resources. Shader attribution/license: third_party/fsr1.
// Neither intermediate image is part of emulated GS memory or saved state.
struct FsrPresentation {
    WGPURenderPipeline easu = nullptr, rcas = nullptr;
    WGPUBindGroupLayout rcas_layout = nullptr;
    WGPUTexture image = nullptr;
    WGPUTextureView view = nullptr;
    WGPUBindGroup group = nullptr;
    std::uint32_t width = 0, height = 0;
    bool active = false, upscale = false;
} g_fsr;

void init_fsr(WGPUBindGroupLayout easu_layout) {
    if (os::env("PS2_UPSCALER") != "fsr1") return;
    WGPUShaderSourceWGSL source = WGPU_SHADER_SOURCE_WGSL_INIT;
    source.code = view(kFsrShader);
    WGPUShaderModuleDescriptor md = WGPU_SHADER_MODULE_DESCRIPTOR_INIT;
    md.nextInChain = &source.chain;
    WGPUShaderModule module = wgpuDeviceCreateShaderModule(g_device, &md);
    WGPUBindGroupLayoutEntry entries[2] = {WGPU_BIND_GROUP_LAYOUT_ENTRY_INIT, WGPU_BIND_GROUP_LAYOUT_ENTRY_INIT};
    entries[0].binding = 1;
    entries[0].visibility = WGPUShaderStage_Fragment;
    entries[0].buffer.type = WGPUBufferBindingType_Uniform;
    entries[1].binding = 2;
    entries[1].visibility = WGPUShaderStage_Fragment;
    entries[1].texture.sampleType = WGPUTextureSampleType_UnfilterableFloat;
    entries[1].texture.viewDimension = WGPUTextureViewDimension_2D;
    WGPUBindGroupLayoutDescriptor ld = WGPU_BIND_GROUP_LAYOUT_DESCRIPTOR_INIT;
    ld.entryCount = 2; ld.entries = entries;
    g_fsr.rcas_layout = wgpuDeviceCreateBindGroupLayout(g_device, &ld);
    const auto pipeline = [&](WGPUBindGroupLayout layout, const char *entry, WGPUTextureFormat format) {
        WGPUPipelineLayoutDescriptor pld = WGPU_PIPELINE_LAYOUT_DESCRIPTOR_INIT;
        pld.bindGroupLayoutCount = 1; pld.bindGroupLayouts = &layout;
        WGPUPipelineLayout pl = wgpuDeviceCreatePipelineLayout(g_device, &pld);
        WGPUColorTargetState color = WGPU_COLOR_TARGET_STATE_INIT; color.format = format;
        WGPUFragmentState fragment = WGPU_FRAGMENT_STATE_INIT;
        fragment.module = module; fragment.entryPoint = view(entry); fragment.targetCount = 1; fragment.targets = &color;
        WGPURenderPipelineDescriptor rd = WGPU_RENDER_PIPELINE_DESCRIPTOR_INIT;
        rd.layout = pl; rd.vertex.module = module; rd.vertex.entryPoint = view("vs"); rd.fragment = &fragment;
        WGPURenderPipeline result = wgpuDeviceCreateRenderPipeline(g_device, &rd);
        wgpuPipelineLayoutRelease(pl);
        return result;
    };
    g_fsr.easu = pipeline(easu_layout, "fs_easu", WGPUTextureFormat_RGBA16Float);
    g_fsr.rcas = pipeline(g_fsr.rcas_layout, "fs_rcas", g_surface_format);
    wgpuShaderModuleRelease(module);
    g_fsr.active = g_fsr.easu && g_fsr.rcas;
    std::fprintf(stderr, "[video] FSR1 EASU + RCAS %s (spatial upscaling; no frame generation)\n", g_fsr.active ? "enabled" : "unavailable");
}

bool fsr_target(std::uint32_t width, std::uint32_t height) {
    if (!g_fsr.active || !g_fsr.upscale || !width || !height) return false;
    if (width == g_fsr.width && height == g_fsr.height) return g_fsr.group != nullptr;
    if (g_fsr.group) wgpuBindGroupRelease(g_fsr.group);
    if (g_fsr.view) wgpuTextureViewRelease(g_fsr.view);
    if (g_fsr.image) wgpuTextureRelease(g_fsr.image);
    WGPUTextureDescriptor td = WGPU_TEXTURE_DESCRIPTOR_INIT;
    td.size = WGPUExtent3D{width, height, 1}; td.format = WGPUTextureFormat_RGBA16Float;
    td.usage = WGPUTextureUsage_RenderAttachment | WGPUTextureUsage_TextureBinding;
    td.dimension = WGPUTextureDimension_2D;
    g_fsr.image = wgpuDeviceCreateTexture(g_device, &td);
    g_fsr.view = wgpuTextureCreateView(g_fsr.image, nullptr);
    WGPUBindGroupEntry entries[2] = {WGPU_BIND_GROUP_ENTRY_INIT, WGPU_BIND_GROUP_ENTRY_INIT};
    entries[0].binding = 1; entries[0].buffer = g_blit_params; entries[0].size = 32;
    entries[1].binding = 2; entries[1].textureView = g_fsr.view;
    WGPUBindGroupDescriptor bd = WGPU_BIND_GROUP_DESCRIPTOR_INIT;
    bd.layout = g_fsr.rcas_layout; bd.entryCount = 2; bd.entries = entries;
    g_fsr.group = wgpuDeviceCreateBindGroup(g_device, &bd);
    g_fsr.width = width; g_fsr.height = height;
    std::fprintf(stderr, "[video] FSR1 presentation target %ux%u\n", width, height);
    return g_fsr.group != nullptr;
}

void encode_easu(WGPUCommandEncoder encoder) {
    WGPURenderPassColorAttachment color = WGPU_RENDER_PASS_COLOR_ATTACHMENT_INIT;
    color.view = g_fsr.view; color.loadOp = WGPULoadOp_Clear; color.storeOp = WGPUStoreOp_Store;
    WGPURenderPassDescriptor rd = WGPU_RENDER_PASS_DESCRIPTOR_INIT;
    rd.colorAttachmentCount = 1; rd.colorAttachments = &color;
    WGPURenderPassEncoder pass = wgpuCommandEncoderBeginRenderPass(encoder, &rd);
    wgpuRenderPassEncoderSetPipeline(pass, g_fsr.easu);
    wgpuRenderPassEncoderSetBindGroup(pass, 0, g_blit_group, 0, nullptr);
    wgpuRenderPassEncoderDraw(pass, 3, 1, 0, 0);
    wgpuRenderPassEncoderEnd(pass); wgpuRenderPassEncoderRelease(pass);
}

// Explicit diagnostic capture of the presented image, including postprocessing.
// PS2_PRESENT_CAPTURE=frame:/path/image.ppm. It never changes emulated memory.
struct PresentCapture {
    std::uint64_t frame = 0;
    std::string path;
    WGPUBuffer buffer = nullptr;
    std::uint32_t stride = 0, width = 0, height = 0;
    bool supported = false, encoded = false, done = false;
} g_present_capture = [] {
    PresentCapture c;
    const std::string value = os::env("PS2_PRESENT_CAPTURE");
    if (!value.empty()) {
        char *end = nullptr;
        c.frame = std::strtoull(value.c_str(), &end, 10);
        if (end && *end == ':' && end != value.c_str() && end[1]) c.path = end + 1;
        else std::fprintf(stderr, "[video] invalid PS2_PRESENT_CAPTURE; expected frame:path.ppm\n");
    }
    return c;
}();

void encode_present_capture(WGPUCommandEncoder encoder) {
    auto &c = g_present_capture;
    const std::uint64_t frame = queue::active() ? gs::present_frame() : frames_run();
    if (!c.supported || c.done || c.encoded || frame != c.frame || !post::g_present_texture) return;
    c.width = g_surface_width; c.height = g_surface_height; c.stride = (c.width * 4u + 255u) & ~255u;
    c.buffer = make_buffer(static_cast<std::uint64_t>(c.stride) * c.height, WGPUBufferUsage_MapRead | WGPUBufferUsage_CopyDst);
    WGPUTexelCopyTextureInfo source = WGPU_TEXEL_COPY_TEXTURE_INFO_INIT;
    source.texture = post::g_present_texture;
    WGPUTexelCopyBufferInfo target = WGPU_TEXEL_COPY_BUFFER_INFO_INIT;
    target.buffer = c.buffer; target.layout.bytesPerRow = c.stride; target.layout.rowsPerImage = c.height;
    const WGPUExtent3D size{c.width, c.height, 1};
    wgpuCommandEncoderCopyTextureToBuffer(encoder, &source, &target, &size);
    c.encoded = true;
}

void collect_present_capture() {
    auto &c = g_present_capture;
    if (!c.encoded || c.done) return;
    struct Mapped { bool done = false, ok = false; } status;
    WGPUBufferMapCallbackInfo callback = WGPU_BUFFER_MAP_CALLBACK_INFO_INIT;
    callback.mode = WGPUCallbackMode_AllowProcessEvents;
    callback.userdata1 = &status;
    callback.callback = [](WGPUMapAsyncStatus result, WGPUStringView, void *pointer, void *) {
        auto &s = *static_cast<Mapped *>(pointer); s.ok = result == WGPUMapAsyncStatus_Success; s.done = true;
    };
    const std::uint64_t bytes = static_cast<std::uint64_t>(c.stride) * c.height;
    wgpuBufferMapAsync(c.buffer, WGPUMapMode_Read, 0, bytes, callback);
    while (!status.done) pump();
    if (status.ok) {
        const auto *data = static_cast<const std::uint8_t *>(wgpuBufferGetConstMappedRange(c.buffer, 0, bytes));
        if (data) if (std::FILE *file = os::open(c.path, "wb")) {
            std::fprintf(file, "P6\n%u %u\n255\n", c.width, c.height);
            const bool bgra = g_surface_format == WGPUTextureFormat_BGRA8Unorm || g_surface_format == WGPUTextureFormat_BGRA8UnormSrgb;
            for (std::uint32_t y = 0; y < c.height; ++y) for (std::uint32_t x = 0; x < c.width; ++x) {
                const auto *p = data + static_cast<std::size_t>(y) * c.stride + x * 4u;
                const std::uint8_t rgb[3] = {p[bgra ? 2 : 0], p[1], p[bgra ? 0 : 2]};
                std::fwrite(rgb, 1, 3, file);
            }
            std::fclose(file);
            std::fprintf(stderr, "[video] captured presented frame %llu at %ux%u to %s\n", static_cast<unsigned long long>(c.frame), c.width, c.height, c.path.c_str());
        }
        wgpuBufferUnmap(c.buffer);
    } else std::fprintf(stderr, "[video] presented capture mapping failed\n");
    wgpuBufferRelease(c.buffer); c.buffer = nullptr; c.done = true;
}
