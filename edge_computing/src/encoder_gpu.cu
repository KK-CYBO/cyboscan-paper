#include "encoder.h"


__constant__ float bgr_to_yuv_C_[12] = {
    0.257 , 0.504,   0.098, 17.28,
    -0.148, -0.291,  0.439, 128.0,
    0.439 , -0.368, -0.071, 128.0
};

__device__ unsigned char custom_clamp255(int value) {
    return min(max(value, 0), 255);
}

__global__ void
    RGBto3ChYUV420K(
        const unsigned char * rgb,
        size_t rgbStep,
        unsigned char * y_plane, 
        unsigned char * u_plane,
        unsigned char * v_plane,
        size_t yStep,
        size_t uvStep,
        int width,
        int height
        )
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x < width && y < height)
    {
        int idx = (y * rgbStep + x) * 3;
        unsigned char redd = rgb[idx + 2];
        unsigned char greenn = rgb[idx + 1];
        unsigned char bluee = rgb[idx + 0];

        const float Y = bgr_to_yuv_C_[0] * redd + bgr_to_yuv_C_[1] * greenn + bgr_to_yuv_C_[2] * bluee + bgr_to_yuv_C_[3];
        const float U = bgr_to_yuv_C_[4] * redd + bgr_to_yuv_C_[5] * greenn + bgr_to_yuv_C_[6] * bluee + bgr_to_yuv_C_[7];
        const float V = bgr_to_yuv_C_[8] * redd + bgr_to_yuv_C_[9] * greenn + bgr_to_yuv_C_[10]* bluee + bgr_to_yuv_C_[11];

        *((unsigned char*)((char*)y_plane + y * yStep) + x) = static_cast<unsigned char>(custom_clamp255(Y));

        if (y % 2 == 0 && x % 2 == 0)
        {
            unsigned char uPixel = static_cast<unsigned char>(custom_clamp255(U));
            unsigned char vPixel = static_cast<unsigned char>(custom_clamp255(V));
            *((unsigned char*)((char*)u_plane + (y /2) * uvStep) + x/2) = uPixel;
            *((unsigned char*)((char*)v_plane + (y /2) * uvStep) + x/2) = vPixel;
        }
    }
}

void Encoder::RGBto3ChYUV420(
    const unsigned char * d_frame_rgb,
    unsigned char * d_frame_y,
    unsigned char * d_frame_u,
    unsigned char * d_frame_v,
    int H,
    int W,
    int step,
    int ystep,
    int uvstep
    )
{
    dim3 blockSize(32, 32);
    dim3 gridSize((W + blockSize.x - 1) / blockSize.x, (H + blockSize.y - 1) / blockSize.y);
    size_t rgb_step = step;
    size_t y_step = ystep;
    size_t uv_step = uvstep;
    RGBto3ChYUV420K<<<gridSize, blockSize>>>(d_frame_rgb, rgb_step, d_frame_y, d_frame_u, d_frame_v, y_step, uv_step, W, H);
    cudaDeviceSynchronize();
}
