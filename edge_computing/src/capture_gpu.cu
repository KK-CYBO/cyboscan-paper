#include <iostream>
#include <cuda_runtime.h>
#include "capture.h"

#define CHECK_CUDA_CALL(call)                                                                \
    do {                                                                                     \
        cudaError_t err = call;                                                              \
        if (err != cudaSuccess) {                                                            \
            std::cerr << "CUDA Error: " << cudaGetErrorString(err) << " at " << __FILE__     \
                      << ":" << __LINE__ << std::endl;                                       \
            exit(EXIT_FAILURE);                                                              \
        }                                                                                    \
    } while (0)

__device__ unsigned short clamp65535(int value) {
    return min(max(value, 0), 65535);
}


__global__ void AddGainTo16bitKernel(
    const uint16_t* inpImg,
    const int inp_h,
    const int inp_w,
    const int inp_p,
    unsigned short* outImg,
    const int out_h,
    const int out_w,
    const int out_p,
    const float gainR,
    const float gainG1,
    const float gainG2,
    const float gainB,
    const unsigned short trunc_th
)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x < inp_w && y < inp_h)
    {
        float the_gain;

        if ((y % 2 == 0) && (x % 2 == 0))
            the_gain = gainR;
        else if ((y % 2 == 0) && (x % 2 == 1))
            the_gain = gainG1;
        else if ((y % 2 == 1) && (x % 2 == 0))
            the_gain = gainG2;
        else
            the_gain = gainB;

        outImg[x + y * out_w] = static_cast<unsigned short>(
            clamp65535(the_gain * inpImg[x + y * inp_w])
        );
    }
}


bool IPEXCAMImpl::AddGainTo16bit(
    const uint16_t* input_d,
    const int h_,
    const int w_,
    const int p_,
    unsigned short* bayerTmp,
    const float col_gain_red,
    const float col_gain_gr1,
    const float col_gain_gr2,
    const float col_gain_blue,
    const bool apply_bg
)
{
    int out_p = cam_current_W * 2;

    dim3 blockSize(16, 16);
    dim3 gridSize(
        (w_ + blockSize.x - 1) / blockSize.x,
        (h_ + blockSize.y - 1) / blockSize.y
    );

    unsigned short trunc_th = 65535;

    AddGainTo16bitKernel<<<gridSize, blockSize>>>(
        input_d,
        h_, w_, p_,
        bayerTmp,
        cam_current_H, cam_current_W, out_p,
        col_gain_red, col_gain_gr1, col_gain_gr2, col_gain_blue,
        trunc_th
    );

    cudaDeviceSynchronize();

    cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess)
    {
        printf("CUDA AddGainTo16bit ---> current_img_idx = %i\n", current_img_idx);
        printf("CUDA AddGainTo16bit ---> Kernel error ---> %s\n", cudaGetErrorString(error));
        return false;
    }

    return true;
}
