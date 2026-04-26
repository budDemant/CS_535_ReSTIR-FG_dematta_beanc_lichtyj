# Linux issues to investigate

Tracking list for ReSTIR FG perf/stability issues on Linux (Vulkan backend).
Short notes only. Add findings inline as they're confirmed.

## Open

- [ ] **Resizing the window rubber-bands and aborts (SIGABRT, exit 134).**
  Reproduces even before a scene is loaded. Observed: window snaps between
  sizes a few times, then crashes. Two contributing bugs:
  1. `Source/Falcor/Core/Window.cpp:43` — `windowSizeCallback` (called by GLFW
     on user drag) invokes the programmatic `Window::resize`, which at
     `Window.cpp:498` calls `glfwSetWindowSize`. On X11/Xwayland that issues
     `XResizeWindow`, WM replies with an adjusted configure, GLFW fires the
     size callback again → feedback loop. Each iteration also runs
     `handleWindowSizeChange` → `Swapchain::resize` → `flushAndSync`.
     Likely fix: split user-event path from programmatic API — callback
     should only update stored size + call `handleWindowSizeChange`, not go
     back through `glfwSetWindowSize`.
  2. `Source/Falcor/Core/API/Swapchain.cpp:78` — `resize()` never updates
     `mDesc.width` / `mDesc.height`, so after resize `prepareImages` wraps
     the new GFX images with stale dimensions. Subsequent blits/presents
     operate on mismatched sizes. Likely fix: assign
     `mDesc.width = width; mDesc.height = height;` before `prepareImages`.

  Validation capture attempt (`VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation`)
  produced no extra output — layer probably not installed, or messages going
  to stderr were discarded before the abort. Try
  `vulkaninfo --summary | rg -i 'VK_LAYER_KHRONOS_validation'` first, and use
  `VK_LOADER_LAYERS_ENABLE=VK_LAYER_KHRONOS_validation` on newer loaders.

- [ ] **Profiler (`P` key) crashes the app.** Vulkan timestamp path in
  `Source/Falcor/Core/API/GpuTimer.cpp` uses `resourceCommandEncoder->writeTimestamp`
  + per-event `GpuTimer` alloc. Suspected: query-heap exhaustion
  (`Device.cpp:618`, 1024*1024 entries) or slang-gfx encoder mismatch on
  `resolveQuery`. Need crash log / stack trace to confirm.
- [ ] **~2 fps on RTX 4070 Ti vs ~25 fps on 2070 (Windows).** GPU at 100% util
  but only 65 W / 285 W — SM-starvation signature. Capture per-pass timings
  (external tool, since profiler crashes) to find the dominant pass.
  External-profiling path wired in: NVTX push/pop was added to
  `Profiler::startEvent`/`endEvent` (gated on `FALCOR_HAS_CUDA`), so every
  `FALCOR_PROFILE("...")` scope now shows as a labelled range in Nsight
  Systems / Nsight Graphics without depending on `GpuTimer`. Capture with:

  ```
  nsys profile --trace=vulkan,nvtx --sample=cpu --output=profile_restir \
      build/linux-gcc/bin/Release/Mogwai --script=<script.py>
  ```

  Then open `profile_restir.nsys-rep` in `nsys-ui` and rank passes by GPU
  duration on the Vulkan queue timeline. Nsight Graphics (for warp-stall
  detail) is not installed — separate download from NVIDIA if needed.
- [ ] **Vulkan backend has no NVAPI / SER / OMM.** Gated to D3D12 in
  `SampleApp.cpp:104`. Major factor in the perf gap; no easy fix, but worth
  quantifying (compare with SER disabled on Windows if possible).
- [ ] **DLSSPass compiled out on Linux.** `RenderPasses/DLSSPass/CMakeLists.txt:1`
  requires `FALCOR_HAS_D3D12`. Confirm whether the launched script actually
  depends on DLSS; if so, either port or use a non-DLSS script variant.
- [ ] **Procedural hit group has `intersectionShader = VK_SHADER_UNUSED_KHR`.**
  Vulkan VL spams `VUID-VkRayTracingShaderGroupCreateInfoKHR-type-03476` on
  `pGroups[2]` during each `vkCreateRayTracingPipelinesKHR` around
  `LightCollection::build`. Root cause: `ReSTIR_FG.cpp:2065` and `:2067`
  (`initRTCollectionProgram`) both call `desc.addHitGroup(..., "intersection",
  globalTypeConformances)` without a distinguishing `entryPointNameSuffix`.
  Program dedupe in `Program.cpp:212` then logs `Duplicate program entry points
  'intersection' of type 'intersection'.` and drops the second one, so the
  ray-type-1 hit group ends up with no intersection shader index. Non-fatal
  (process exits normally) but violates the spec. Fix: pass unique suffixes
  (e.g. `"RayType0"` / `"RayType1"`), matching the pattern used in
  `PathTracer.cpp:702`.
- [ ] **Shader model 6_6 requested but unsupported on Vulkan build.**
  `CustomAccelerationStructure.cpp:383` sets SM 6_6 unconditionally for
  `clearAABBBuffers`. Fallback appears silent; check whether the fallback
  shader is actually correct, or guard with `isShaderModelSupported` like
  `LightCollection.cpp:125`.
- [ ] **Wayland/KDE compositor overhead.** `nvidia-smi` shows kwin_wayland +
  Xwayland + many GPU clients. Test under Xorg session and/or with other GPU
  apps closed; record delta.

## Known / low-priority

- `GpuTimer::resolve` resolves per-timer instead of batching (comment at
  `GpuTimer.cpp:125`). Perf-only, not the crash.
- Many AssimpImporter warnings on Kitchen scene (missing UVs, zero-length
  normals). Cosmetic, unrelated to perf.

## Resolved

- _(none yet)_
