#include "capture.h"
#include <iostream>
#include <thread>
#include <algorithm>
#include <numeric>

using namespace std;


static void indexed_sort(const std::vector<unsigned int>& key,
                         std::vector<unsigned int>& idx)
{
    const size_t n = key.size();
    idx.resize(n);
    std::iota(idx.begin(), idx.end(), 0);

    std::sort(idx.begin(), idx.end(),
              [&](unsigned int a, unsigned int b) {
                  return key[a] < key[b];
              });
}

CamBayerConsumer::CamBayerConsumer(
    IPEXCAMImpl* ipex_cam_impl_,
    int W,
    int H)
    : ipex_cam_impl(ipex_cam_impl_), imgW(W), imgH(H)
{
    std::cout << "CamBayerConsumer (Dummy Mode) Construction Done\n";
}

CamBayerConsumer::~CamBayerConsumer()
{
    stopFlag = true;
    threadShutdown();
}

bool CamBayerConsumer::threadInitialize()
{
    std::cout << "CamBayerConsumer threadInitialize (No Argus)\n";
    return true;
}

static void generateDummy16bitBayer(
    uint16_t* buf,
    int H,
    int W)
{
    for (int y = 0; y < H; y++)
    {
        for (int x = 0; x < W; x++)
        {
            buf[y * W + x] = ((x / 16 + y / 16) % 2) ? 800 : 1600;
        }
    }
}

bool CamBayerConsumer::threadExecute()
{
    std::cout << "[Dummy Consumer] Start threadExecute\n";

    ipex_cam_impl->consumer_ready = true;

    int H = ipex_cam_impl->cam_current_H;
    int W = ipex_cam_impl->cam_current_W;
    unsigned long img_size = (unsigned long)H * (unsigned long)W;

    std::vector<uint16_t> dummyBayer(img_size);

    for (int frame = 0; frame < (int)ipex_cam_impl->num_of_buffer; frame++)
    {
        if (ipex_cam_impl->finish_capturing) break;
        if (stopFlag) break;

        std::this_thread::sleep_for(std::chrono::milliseconds(20));

        generateDummy16bitBayer(dummyBayer.data(), H, W);

        unsigned long pt_16b = (unsigned long)ipex_cam_impl->current_img_idx * img_size;

        ipex_cam_impl->AddGainTo16bit(
            dummyBayer.data(),
            H,
            W,
            W * sizeof(uint16_t),
            ipex_cam_impl->bayer16bStack + pt_16b,
            ipex_cam_impl->col_gain_red,
            ipex_cam_impl->col_gain_gr1,
            ipex_cam_impl->col_gain_gr2,
            ipex_cam_impl->col_gain_blue,
            true
        );

        ipex_cam_impl->bg_done[ipex_cam_impl->current_img_idx] = true;
        ipex_cam_impl->FPGA_FrN.push_back((unsigned int)ipex_cam_impl->IpexFrN);
        ipex_cam_impl->IpexFrN++;

        if (ipex_cam_impl->current_img_idx ==
            (int)ipex_cam_impl->num_of_buffer - 1)
        {
            indexed_sort(ipex_cam_impl->FPGA_FrN, ipex_cam_impl->im_buf_idx);
            ipex_cam_impl->FPGA_FrN.clear();
            ipex_cam_impl->current_img_idx = 0;
            ipex_cam_impl->img_stk_stat = 2;
        }
        else
        {
            ipex_cam_impl->current_img_idx++;
        }
    }

    std::cout << "[Dummy Consumer] Finished threadExecute\n";
    ipex_cam_impl->ipex_consumer_finished = true;
    return true;
}

bool CamBayerConsumer::threadShutdown()
{
    std::cout << "[Dummy Consumer] Shutdown\n";
    ipex_cam_impl->ipex_consumer_finished = true;
    return true;
}
