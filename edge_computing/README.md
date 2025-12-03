# Edge computing software

This directory contains a minimal, publicly shareable subset of the edge computing software used in:

> Nitta et al., *Clinical-grade autonomous cytopathology via whole-slide edge tomography*.

It is part of the **`cyboscan-paper`** repository.  
For a high-level system overview, release notes, and license information, please refer to the **repository root `README.md`** and `LICENSE`.

This directory provides a simplified extraction of the core image-processing pipeline used in a system with custom camera and imaging hardware. The purpose of this software is to present and document the essential image-processing workflow implemented in the actual system.
To function correctly in a real system, additional code is required for hardware connections, device control, and environment-specific configuration.
The included code focuses on the core processing logic and is not a complete standalone application.


---

## Directory structure

```
edge_computing/
├─ include/
│  ├─ capture.h          # Camera acquisition interfaces and data structures
│  ├─ encoder.h          # Encoder module API definitions
│  └─ imaging.h          # Image-processing function declarations
│
├─ src/
│  ├─ capture.cpp        # Implementation of image capture logic
│  ├─ capture_gpu.cu     # CUDA implementation of color gain processing
│  ├─ encoder.cpp        # Implementation of encoder pipeline
│  ├─ encoder_gpu.cu     # CUDA acceleration for encoder operations
│  ├─ imaging.cpp        # Image processing routines
│  ├─ imaging_gpu.cu     # CUDA-accelerated imaging functions
│  └─ CMakeLists.txt     # Build system configuration
│
└─ README.md             # Project documentation
```

--- 
## System Architecture

### Capture Module
The capture logic has been refactored to use synthetic input frames instead of real hardware input.
This allows users to understand and evaluate the core pipeline without requiring access to the original hardware.
The module operates using two main components:

1. **IPEXCAMImpl**: Manages memory buffers, software triggering, and image preprocessing such as gain adjustment and background compensation.
2. **CamBayerConsumer**: Generates synthetic 16-bit Bayer images and feeds them into the processing pipeline in place of real camera frames.

#### IPEXCAMImpl
- Allocates device and host memory for:
  - 16-bit Bayer image stacks (`bayer16bStack`)
  - Background correction buffers
- Stores control parameters:
  - Frame size
  - White-balance gain coefficients
  - Number of buffered frames
- Maintains processing state:
  - Current buffer index
  - Completion flags (`bg_done`)
  - Frame ordering information (`im_buf_idx`, `FPGA_FrN`)
- Provides a trigger mechanism
- Exposes APIs to retrieve processed image data

#### CamBayerConsumer
This class implements the frame-ingestion loop that produces dummy Bayer16 images in place of real camera input.
* `threadExecute()` repeatedly generates frames until the buffer cycle completes or capturing is stopped.
* For each frame:
  1. Optional delay simulates the frame interval.
  2. Dummy 16-bit RGGB Bayer data is generated.
  3. The image-processing core `AddGainTo16bit()` processes the data.
  4. A completion flag is set: `bg_done[current_idx] = true`.
  5. A frame counter is appended to `FPGA_FrN`.
  6. The internal buffer index is advanced.
  7. When the buffer is full:
     * Frame numbers are sorted via `indexed_sort()`
     * The sorting result is stored in `im_buf_idx`
     * Internal indices and lists are reset.

The core image-processing routine converts a raw 16-bit Bayer image into a gain-adjusted output using a CUDA kernel.
Each pixel is interpreted according to the RGGB Bayer pattern and color gains are applied. The result is stored in the output buffer.
This GPU pipeline enables real-time per-pixel gain adjustment across high-resolution sensor data.

### Imaging Module
This module implements the GPU-accelerated imaging pipeline used during multi-layer image acquisition.  
It receives a stack of Bayer-format images, converts them to 8-bit representations, performs per-pixel focus synthesis using layer-dependent Z-maps, and outputs BGR-formatted, focus-corrected images.
The processing pipeline is triggered spot-by-spot, and each spot includes several imaging layers (Z-layers).
The module coordinates asynchronous GPU tasks, waits for image stack readiness, and performs multi-stage processing before delivering the final output.

#### Main Control Loop (`final_focus`)
This loop provides synchronization, error handling, and progressive spot-based execution.
1. Waits for a complete image stack from the camera module.  
2. Ensures that a new capture is available before processing.  
3. Retrieves the raw 16-bit Bayer stack from the camera.
4. Calls the GPU processing routine `final_focus_task_gpu()` for each spot.
5. Releases the stack buffer and continues until the configured number of spots is processed.
6. Cleans up and resets state once imaging is complete.

#### GPU Processing (`final_focus_task_gpu`)
The GPU module performs two main tasks during image processing. 

1. **8-bit Conversion**  
The GPU first converts each 16-bit Bayer frame into an 8-bit image for faster processing. This is done in the `convert8BitKernel` CUDA kernel, where every pixel is scaled by dividing by 256 and written to GPU memory. By reducing bit depth early, the pipeline lowers memory usage and increases processing throughput, which is important because multiple depth layers must be processed for focus synthesis.

2. **Focus Layer Selection and Demosaicing**  
Next, the `BayerFocusInPlace2BGR` kernel selects the best-focus layer for each pixel using the per-pixel depth map (`best_z_map`) and the layer ordering table (`layer_idx`). After choosing the appropriate Bayer layer, the kernel performs bilinear interpolation on the RGGB pattern to reconstruct B, G, and R values. The output is a full-color BGR image generated directly on the GPU, enabling high-speed reconstruction from multi-layer Bayer data.

### Encoder Module
This module implements a hardware-accelerated image encoding pipeline optimized for NVIDIA Jetson platforms. Its primary purpose is to take GPU-processed image frames—generated by the imaging and focus system—and convert them into an encoded H.265 video stream using the Jetson hardware encoder. The overall design uses zero-copy GPU memory sharing, ensuring minimal latency while supporting continuous, multi-frame scientific imaging workflows.

#### Encoder Initialization and Configuration
The encoder is created and configured through the `Encoder` class, which sets pixel formats, rate-control parameters, bitrate, GOP structure, chroma format, and QP ranges based on system requirements. It uses NVIDIA’s Multimedia API to configure both the output plane (raw input images) and capture plane (encoded output stream). The initialization logic ensures that the encoder is correctly tuned for the target resolution, frame rate, and encoding profile, especially for HEVC Main or Main10 modes.

#### Runtime Parameter Adjustment
The module supports dynamic updates to encoding parameters such as bitrate, framerate, peak bitrate, and IDR forcing. A simple parameter script can be parsed and applied during operation, enabling immediate, frame-accurate adjustments. This is particularly useful for adaptive imaging applications where lighting, motion, or bandwidth conditions may change.

#### Frame Encoding Process
For each imaging frame, `encode_frame()` writes the YUV420 representation of the BGR input image, sets timestamps, and queues it to the encoder. The method supports blocking and non-blocking modes and handles EOS (end-of-stream) signaling when necessary.
This function acts as the bridge between the imaging GPU pipeline and the hardware encoder. It is optimized to handle sequences of frames coming from focus stacking, multi-layer scanning, or other scientific capture loops.

#### Integration with Imaging Pipeline
The encoding process is typically triggered from the acquisition pipeline, which feeds GPU-generated BGR frames into the encoder. It processes multi-layer focused images sequentially across multiple spots and encodes them frame by frame. Synchronization with GPU operations ensures that only completed, fully processed frames are passed into the encoding pipeline.
This integration enables the overall imaging system to generate high-quality encoded videos that represent focused and undistorted image data captured across multiple layers—making the module suitable for microscopy, scanning, or scientific imaging workflows.

#### GPU YUV Conversion Kernel
The module includes a CUDA kernel that converts BGR frames into YUV420 format directly on the GPU. Each thread computes one pixel of the Y plane and subsamples chroma values (U and V) for every 2×2 block, using a constant-memory coefficient matrix for efficient color–space transformation. The `RGBto3ChYUV420K` kernel writes Y, U, and V values into hardware-compatible memory layouts, enabling the encoder to consume GPU-resident YUV surfaces without CPU-side conversion.


--- 
## System Requirements

### Target Hardware
This software is designed and tested specifically on the NVIDIA Jetson Xavier NX (16GB model).  
The system relies on the Xavier NX platform for CUDA acceleration, GPU processing, and embedded execution.  

### Prerequisites
Before building and running this software, the following components must be installed on the system.  
These are the minimum requirements needed for CUDA-based image processing and OpenCV operations.

- NVIDIA JetPack (version 5.1, including CUDA drivers and toolchain)
- CUDA Toolkit (Jetson-compatible)
- Jetson Multimedia API (matching the installed JetPack version)
- OpenCV C++ Libraries (opencv_core, opencv_imgproc, opencv_imgcodecs)
- CMake (version 3.18 or newer)
- GCC/G++ Compiler with C++17 support

--- 

## Build Instructions
This software is built using CMake and requires the NVIDIA Jetson Xavier NX toolchain, CUDA, and the Jetson Multimedia API. After cloning the repository to your Jetson device, the typical build steps are:

```bash
mkdir build
cd build
cmake ..
make -j6
```

Set API_DIR in CMakeLists.txt to your Jetson Multimedia API root (e.g. /opt/nvidia/jetson_multimedia_api).
The use of `-j6` is recommended on the Jetson Xavier NX to improve compilation speed.

### Build Time
On a Jetson Xavier NX (16GB model), a full build typically completes in approximately 1-2 minutes, depending on whether CUDA kernels require recompilation. Subsequent incremental builds are usually faster since most object files remain cached.

### Runtime Characteristics
This project does not run as a single monolithic application. Instead, each component operates in real time as part of a continuous processing pipeline. 


---
## License

The `edge_computing` directory is part of the `cyboscan-paper` repository,
which is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
© 2025 K.K.CYBO

Some portions of the code disclosed here may be covered by one or more patents.
The existence, scope, and jurisdiction of any such patents may vary, and
nothing in this repository grants any license to practice patented technology.

For details, please refer to the `LICENSE` file at the root of the repository.