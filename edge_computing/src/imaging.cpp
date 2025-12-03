#include <filesystem>
#include "imaging.h"
#include "capture.h"

using namespace cv;
using namespace std;
std::mutex gmtx;

std::vector<std::string> fol_names;

void Focus::final_focus()
{
    int i_s = 1;

    while (true)
    {
        imaging_is_free = true;
        frame_miss = false;
        unsigned short stk_stat = ipex_cam->img_stack_status();
        if (abort_all) break;
        if (stk_stat < 1)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        if (!new_capture)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            ipex_cam->release_img_buff(0);
            continue;
        }

        if (stk_stat)
        {
            focus_finished = false;
            imaging_is_free = false;
            new_capture = false;
            unsigned short* theStack = ipex_cam->get_16b_bayer_stack();
            bool res = final_focus_task_gpu(i_s, theStack);
            if (abort_all) return;          
            if (res)
            {
                ipex_cam->release_img_buff(0);
                i_s++;
                spot_count_done++;
            }
            if (i_s > desired_num_of_spots) break;
        }
    }
    cudaDeviceSynchronize();
    fol_names.clear();
    std::cout << "IMAGING ENDS" << std::endl;
}


bool Focus::final_focus_task_gpu(int spotIdx, unsigned short* stack_bayer_16bit)
{
    int ij = 0;

    for (ushort l = 0; l < n_layers; l++)
    {
        while (!ipex_cam->is_bg_done(l))
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
            if (abort_all) return false;
            if (frame_miss) return false;
        }
        if (frame_miss) return false;
        
        long int stpt = l * orig_H * orig_W;
        unsigned short* srcPtr = stack_bayer_16bit + stpt;
        unsigned char * dstPtr = fgpu->dra_bayer_stack_8b + stpt;
        
        fgpu->convertTo8bit(srcPtr, dstPtr, orig_W, orig_H);
    }
    cudaDeviceSynchronize();

    ij = 0;
    while (true)
    {
        unsigned short stk_stat = ipex_cam->img_stack_status();
        if (stk_stat == 2) break;        
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
        if (abort_all) return false;
        if (frame_miss) return false;
    }

    ipex_cam->get_layers_indexes(fgpu->layer_idx);
    if (frame_miss) return false;
    
    unsigned int j = 0;
    float all_debayer_t = 0;
    float all_wait_enc_t = 0;
    float all_lens_adj_t = 0;

    for (ushort l = starting_layer; l < n_f_layers_g + starting_layer; l++)
    {
        auto tmp0 = std::chrono::high_resolution_clock::now();    

        while(enc_state[j])
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            if (abort_all) return false;
        }
        
        enc_state[j] = 1;

        long int stpt = l * 1 * orig_H * orig_W;
        unsigned char* srctPtr = fgpu->dra_bayer_stack_8b + stpt;

        fgpu->bayer_focus_inplace_toBGR(
            fgpu->dra_bayer_stack_8b,
            fgpu->one_bgr_img,
            fgpu->best_z_map_g,
            fgpu->layer_idx,
            orig_H,
            orig_W,
            z_map_minVal,
            z_map_maxVal,
            n_layers,
            l
        );

        long int col_adj_pt = j * 3 * orig_H * orig_W * sizeof(unsigned char);
        unsigned char* colDstPtr = fgpu->bgr_focused_undistorted + col_adj_pt;
        // Apply additional image adjustment here if needed

        j++;        
    }
    cudaDeviceSynchronize();

    std::cout << "final imaging task gpu for Spot" << spotIdx << " the_focus...\n";
    vid_stat = 1;  
    unsigned int sp = (spotIdx - 1) * 10;

    return true;
}
