#include <iostream>
#include <cuda_runtime.h>
#include <chrono>
#include <cstdio>

#include "imaging.h"


#define gpuErrchk(ans) { gpuAssert((ans), __FILE__, __LINE__); }
inline void gpuAssert(cudaError_t code, const char *file, int line, bool abort=true)
{
   if (code != cudaSuccess) 
   {
      fprintf(stderr,"GPUassert::: %s %s %d\n", cudaGetErrorString(code), file, line);
      if (abort) exit(code);
   }
}


__global__ void BayerFocusInPlace2BGR(
    unsigned char* inp_arr_8b,
    unsigned char* out_arr_8b,
    unsigned char * best_z_map,
    unsigned int * layer_idx,
    int img_H,
    int img_W,
    int minV,
    int maxV,
    int n_layers,
    int current_l
)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    
    if (x >= img_W || y >= img_H) return;

    int z_c = (maxV + minV) / 2;
    int zshift = z_c - (int)best_z_map[y * img_W + x];
    int src_z = current_l - zshift;
    if (src_z < 0 || src_z > n_layers - 1) return;
    
    int real_z_idx = -1;;
    for (int z = 0; z < n_layers; z++) {
        if (layer_idx[z] == src_z) { real_z_idx = z; break; }
    }
    if (real_z_idx == -1) return;

    unsigned long int img_size = img_H * img_W;
    unsigned long int src_pt = real_z_idx * img_size;
    unsigned char* input = inp_arr_8b + src_pt;

    int Bidx = y * img_W + x;
    int Cidx = Bidx * 3;
    unsigned char B = 0, G = 0, R = 0;
    int width = img_W;

    if ((y % 2 == 0) && (x % 2 == 0))
    {
        R = input[Bidx];
        G = (input[Bidx - 1] + input[Bidx + 1] + input[Bidx - width] + input[Bidx + width]) / 4;
        B = (input[Bidx - width - 1] + input[Bidx - width + 1] + input[Bidx + width - 1] + input[Bidx + width + 1]) / 4;
    }
    else if ((y % 2 == 0) && (x % 2 == 1))
    {
        G = input[Bidx];
        R = (input[Bidx - 1] + input[Bidx + 1]) / 2;
        B = (input[Bidx - width] + input[Bidx + width]) / 2;
    }
    else if ((y % 2 == 1) && (x % 2 == 0))
    {
        G = input[Bidx];
        R = (input[Bidx - width] + input[Bidx + width]) / 2;
        B = (input[Bidx - 1] + input[Bidx + 1]) / 2;
    }
    else
    {
        B = input[Bidx];
        G = (input[Bidx - 1] + input[Bidx + 1] + input[Bidx - width] + input[Bidx + width]) / 4;
        R = (input[Bidx - width - 1] + input[Bidx - width + 1] + input[Bidx + width - 1] + input[Bidx + width + 1]) / 4;
    }

    out_arr_8b[Cidx] = B;
    out_arr_8b[Cidx + 1] = G;
    out_arr_8b[Cidx + 2] = R;
    return;
}


void FocusGPU::bayer_focus_inplace_toBGR(
    unsigned char* input_8b,
    unsigned char* output_8b,
    unsigned char * best_z_map,
    unsigned int * layer_idx_,
    int img_H,
    int img_W,
    int minV,
    int maxV, 
    int n_layers,
    int current_l
)
{   
    dim3 numBlocks((img_W + threadsPerBlock.x - 1) / threadsPerBlock.x,
                   (img_H + threadsPerBlock.y - 1) / threadsPerBlock.y);

    BayerFocusInPlace2BGR<<<numBlocks, threadsPerBlock>>>(
        input_8b,
        output_8b,
        best_z_map,
        layer_idx_,
        img_H,
        img_W,
        minV,
        maxV,
        n_layers,
        current_l
    );

    cudaDeviceSynchronize();

    cudaError_t error = cudaGetLastError();
    if(error != cudaSuccess)
    {
      printf("CUDA bayer-focus-inplace-toBGR error::: %s\n", cudaGetErrorString(error));
      printf("CUDA error, block_size: %i grid_size: %i\n", threadsPerBlock, numBlocks);
      exit(-1);
    }
}


__global__ void convert8BitKernel(
    const unsigned short *d_inBayer,
    unsigned char *d_outBayer,
    int width,
    int height)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    
    if (x >= width || y >= height) return;
    
    int idxPixel = y * width + x;
    d_outBayer[idxPixel] = static_cast<unsigned char>(d_inBayer[idxPixel]/256.0);
}


void FocusGPU::convertTo8bit(const unsigned short *d_inBayer, unsigned char  *d_outBayer, int width, int height)
{
    dim3 block(16, 16);
    dim3 grid((width + block.x - 1) / block.x, (height + block.y - 1) / block.y);
    dim3 grid0((width/4 + block.x - 1) / block.x, (height/4 + block.y - 1) / block.y);

    cudaError_t err;

    convert8BitKernel<<<grid, threadsPerBlock>>>(d_inBayer, d_outBayer, width, height);
    
    err = cudaGetLastError(); if (err != cudaSuccess)  std::cerr << "Error: convet8bitKernel --> " << cudaGetErrorString(err) << "\n";
    err = cudaDeviceSynchronize();
    err = cudaGetLastError();
    if (err != cudaSuccess)  std::cerr << "Error: convertTo8bit --> " << cudaGetErrorString(err) << "\n";
}

