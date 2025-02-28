import os
import argparse
import shutil
import sys
import warnings
from subprocess import call

def run_cmd(command):
    try:
        call(command, shell=True)
    except KeyboardInterrupt:
        print("Process interrupted")
        sys.exit(1)

def stage_1_overall_restoration(opts):
    print("Running Stage 1: Overall restoration")
    os.chdir("./Global")
    stage_1_input_dir = opts.input_folder
    stage_1_output_dir = os.path.join(opts.output_folder, "stage_1_restore_output")
    if not os.path.exists(stage_1_output_dir):
        os.makedirs(stage_1_output_dir)

    if not opts.with_scratch:
        stage_1_command = (
            "python test.py --test_mode Full --Quality_restore --test_input "
            + stage_1_input_dir
            + " --outputs_dir "
            + stage_1_output_dir
            + " --gpu_ids "
            + opts.GPU
        )
        run_cmd(stage_1_command)
    else:
        mask_dir = os.path.join(stage_1_output_dir, "masks")
        new_input = os.path.join(mask_dir, "input")
        new_mask = os.path.join(mask_dir, "mask")
        stage_1_command_1 = (
            "python detection.py --test_path "
            + stage_1_input_dir
            + " --output_dir "
            + mask_dir
            + " --input_size full_size"
            + " --GPU "
            + opts.GPU
        )

        if opts.HR:
            HR_suffix=" --HR"
        else:
            HR_suffix=""

        stage_1_command_2 = (
            "python test.py --Scratch_and_Quality_restore --test_input "
            + new_input
            + " --test_mask "
            + new_mask
            + " --outputs_dir "
            + stage_1_output_dir
            + " --gpu_ids "
            + opts.GPU + HR_suffix
        )

        run_cmd(stage_1_command_1)
        run_cmd(stage_1_command_2)

    stage_1_results = os.path.join(stage_1_output_dir, "restored_image")
    stage_4_output_dir = os.path.join(opts.output_folder, "final_output")
    if not os.path.exists(stage_4_output_dir):
        os.makedirs(stage_4_output_dir)
    for x in os.listdir(stage_1_results):
        img_dir = os.path.join(stage_1_results, x)
        shutil.copy(img_dir, stage_4_output_dir)

    print("Finish Stage 1 ...")
    print("\n")

def stage_2_face_detection(opts, stage_1_output_dir):
    print("Running Stage 2: Face Detection")
    os.chdir(".././Face_Detection")
    stage_2_input_dir = os.path.join(stage_1_output_dir, "restored_image")
    stage_2_output_dir = os.path.join(opts.output_folder, "stage_2_detection_output")
    if not os.path.exists(stage_2_output_dir):
        os.makedirs(stage_2_output_dir)
    if opts.HR:
        stage_2_command = (
            "python detect_all_dlib_HR.py --url " + stage_2_input_dir + " --save_url " + stage_2_output_dir
        )
    else:
        stage_2_command = (
            "python detect_all_dlib.py --url " + stage_2_input_dir + " --save_url " + stage_2_output_dir
        )
    run_cmd(stage_2_command)
    print("Finish Stage 2 ...")
    print("\n")

def stage_3_face_enhancement(opts, stage_2_output_dir):
    print("Running Stage 3: Face Enhancement")
    os.chdir(".././Face_Enhancement")
    stage_3_input_mask = "./"
    stage_3_input_face = stage_2_output_dir
    stage_3_output_dir = os.path.join(opts.output_folder, "stage_3_face_output")
    if not os.path.exists(stage_3_output_dir):
        os.makedirs(stage_3_output_dir)
    
    if opts.HR:
        opts.checkpoint_name='FaceSR_512'
        stage_3_command = (
            "python test_face.py --old_face_folder "
            + stage_3_input_face
            + " --old_face_label_folder "
            + stage_3_input_mask
            + " --tensorboard_log --name "
            + opts.checkpoint_name
            + " --gpu_ids "
            + opts.GPU
            + " --load_size 512 --label_nc 18 --no_instance --preprocess_mode resize --batchSize 1 --results_dir "
            + stage_3_output_dir
            + " --no_parsing_map"
        ) 
    else:
        stage_3_command = (
            "python test_face.py --old_face_folder "
            + stage_3_input_face
            + " --old_face_label_folder "
            + stage_3_input_mask
            + " --tensorboard_log --name "
            + opts.checkpoint_name
            + " --gpu_ids "
            + opts.GPU
            + " --load_size 256 --label_nc 18 --no_instance --preprocess_mode resize --batchSize 4 --results_dir "
            + stage_3_output_dir
            + " --no_parsing_map"
        )
    run_cmd(stage_3_command)
    print("Finish Stage 3 ...")
    print("\n")

def stage_4_blending(opts, stage_1_output_dir, stage_3_output_dir):
    print("Running Stage 4: Blending")
    os.chdir(".././Face_Detection")
    stage_4_input_image_dir = os.path.join(stage_1_output_dir, "restored_image")
    stage_4_input_face_dir = os.path.join(stage_3_output_dir, "each_img")
    stage_4_output_dir = os.path.join(opts.output_folder, "after_blending")
    if not os.path.exists(stage_4_output_dir):
        os.makedirs(stage_4_output_dir)
    if opts.HR:
        stage_4_command = (
            "python align_warp_back_multiple_dlib_HR.py --origin_url "
            + stage_4_input_image_dir
            + " --replace_url "
            + stage_4_input_face_dir
            + " --save_url "
            + stage_4_output_dir
        )
    else:
        stage_4_command = (
            "python align_warp_back_multiple_dlib.py --origin_url "
            + stage_4_input_image_dir
            + " --replace_url "
            + stage_4_input_face_dir
            + " --save_url "
            + stage_4_output_dir
        )
    run_cmd(stage_4_command)
    print("Finish Stage 4 ...")
    print("\n")

def stage_5(opts):
    print("Running Stage 5: image super resolution")
    real_esrgan_dir = ".././Real-ESRGAN"
    input_dir = os.path.join(opts.output_folder, "after_blending")
    output_dir = os.path.join(opts.output_folder, "final_output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    os.chdir(real_esrgan_dir)
    command = (
        f"python inference_realesrgan.py -n RealESRGAN_x4plus -i {input_dir} -o {output_dir} --face_enhance"
    )
    run_cmd(command)
    print("Finish Stage 5: Real-ESRGAN")
    print("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_folder", type=str, default="./test_images/old", help="Test images")
    parser.add_argument(
        "--output_folder",
        type=str,
        default="./output",
        help="Restored images, please use the absolute path",
    )
    parser.add_argument("--GPU", type=str, default="6,7", help="0,1,2")
    parser.add_argument(
        "--checkpoint_name", type=str, default="Setting_9_epoch_100", help="choose which checkpoint"
    )
    parser.add_argument("--with_scratch", action="store_true")
    parser.add_argument("--HR", action='store_true')
    opts = parser.parse_args()

    # resolve relative paths before changing directory
    opts.input_folder = os.path.abspath(opts.input_folder)
    opts.output_folder = os.path.abspath(opts.output_folder)
    if not os.path.exists(opts.output_folder):
        os.makedirs(opts.output_folder)

    main_environment = os.getcwd()

    stage_1_overall_restoration(opts)

    stage_1_output_dir = os.path.join(opts.output_folder, "stage_1_restore_output")
    stage_2_face_detection(opts, stage_1_output_dir)

    stage_2_output_dir = os.path.join(opts.output_folder, "stage_2_detection_output")
    stage_3_face_enhancement(opts, stage_2_output_dir)

    stage_3_output_dir = os.path.join(opts.output_folder, "stage_3_face_output")
    stage_4_blending(opts, stage_1_output_dir, stage_3_output_dir)
    warnings.filterwarnings("ignore", category=UserWarning)
    stage_5(opts)

    print("All the processing is done. Please check the results.")
