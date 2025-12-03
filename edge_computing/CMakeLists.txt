cmake_minimum_required(VERSION 3.16)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "-D__STDC_CONSTANT_MACROS")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -w")
set(CMAKE_BUILD_TYPE Release)
set(PROJECT_NAME edge_computing)

set(TEGRA_DIR "/usr/lib/aarch64-linux-gnu/tegra")
set(TEGRA_ARMABI "/usr/lib/aarch64-linux-gnu")

set(API_DIR "/opt/nvidia/jetson_multimedia_api"
    CACHE PATH "Path to the Jetson Multimedia API root directory")
set(API_INCLUDE_DIR ${API_DIR}/include)
set(API_CLASS_DIR ${API_DIR}/samples/common/classes)
set(API_ALGO_CUDA_DIR ${API_DIR}/samples/common/algorithm/cuda)
set(API_ALGO_TRT_DIR ${API_DIR}/samples/common/algorithm/trt)
set(API_JPEG_DIR ${API_INCLUDE_DIR}/libjpeg-8b)

set(V4L2_INCLUDE_DIRS /usr/include/)

set(IMAGING_PATH ${CMAKE_CURRENT_SOURCE_DIR})
project(${PROJECT_NAME})

find_package(PkgConfig REQUIRED)
find_package(OpenCV REQUIRED)
find_package(CUDA REQUIRED)

set(CUDA_INCLUDE_DIRS ${CUDA_TOOLKIT_ROOT_DIR}/include)
set(CUDA_NVCC_FLAGS ${CUDA_NVCC_FLAGS};--generate-code arch=compute_72,code=sm_72)
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} --std=c++17")

set(NVIDIA_MMAPI_SOURCES
    ${API_CLASS_DIR}/NvBufSurface.cpp
    ${API_CLASS_DIR}/NvElement.cpp
    ${API_CLASS_DIR}/NvVideoEncoder.cpp
    ${API_CLASS_DIR}/NvV4l2ElementPlane.cpp
    ${API_CLASS_DIR}/NvV4l2Element.cpp
    ${API_CLASS_DIR}/NvElementProfiler.cpp
    ${API_CLASS_DIR}/NvBuffer.cpp
    ${API_CLASS_DIR}/NvLogging.cpp
    ${API_CLASS_DIR}/NvUtils.cpp
)

add_library(NvidiaMMApiLib
    ${NVIDIA_MMAPI_SOURCES}
)

target_include_directories(NvidiaMMApiLib
    PUBLIC
    ${CMAKE_CURRENT_BINARY_DIR}
    ${API_INCLUDE_DIR}
    ${API_CLASS_DIR}    
    ${API_ALGO_CUDA_DIR}
    ${API_ALGO_TRT_DIR}
    ${V4L2_INCLUDE_DIRS}
    ${API_JPEG_DIR}
    ${NVINCLUDE_DIR}
    ${TEGRA_ARMABI}
    ${TEGRA_ARMABI}/tegra
)

target_link_libraries(NvidiaMMApiLib
    PUBLIC
    Threads::Threads
    pthread
    cuda
    v4l2
    X11
    drm
    EGL
    GLESv2
    vulkan
    ${TEGRA_DIR}/libnvbufsurface.so
    ${TEGRA_DIR}/libnvbufsurftransform.so
    ${TEGRA_DIR}/libnvosd.so
    ${TEGRA_DIR}/libnvjpeg.so
)

set(CUDA_SOURCE_FILES
    src/capture_gpu.cu
    src/imaging_gpu.cu
    src/encoder_gpu.cu
)

cuda_add_library(ImagingCudaLib
    ${CUDA_SOURCE_FILES}
)

target_include_directories(ImagingCudaLib
    PUBLIC
    ${API_INCLUDE_DIR}
    ${IMAGING_PATH}/include
    ${OpenCV_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
    ${CUDA_DIR}/targets/aarch64-linux
    ${CUDA_DIR}/lib64
)

target_link_libraries(ImagingCudaLib
    ${CUDA_LIBRARIES}
    ${CUDA_TOOLKIT_ROOT_DIR}/lib64/libcudart.so
)

set(SOURCE_FILES
    ${IMAGING_PATH}/src/capture.cpp
    ${IMAGING_PATH}/src/imaging.cpp
    ${IMAGING_PATH}/src/encoder.cpp
)

add_library(${PROJECT_NAME}
    ${SOURCE_FILES}
)

target_include_directories(${PROJECT_NAME} 
    PUBLIC
    ${IMAGING_PATH}
    ${API_INCLUDE_DIR}
    ${CUDA_INCLUDE_DIRS}
    ${OpenCV_INCLUDE_DIRS}
    ${EGL_INCLUDE_DIR}
    ${OPENGLES_INCLUDE_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CUDA_DIR}/targets/aarch64-linux
    ${CUDA_DIR}/lib64
    ${CAMERA_INC_DIR}
    ${ZSTAGE_DIR}
    ${GST_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME}
    ${OpenCV_LIBS}
    pthread
    cuda
    NvidiaMMApiLib
    ImagingCudaLib
)

