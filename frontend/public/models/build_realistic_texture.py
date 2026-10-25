import os
import math
import numpy as np
from PIL import Image, ImageFilter

def build_realistic_texture():
    base_path = 'frontend/public/models/orig_base_color.webp'
    output_path = 'frontend/public/models/companion_avatar_realistic.jpg'
    teal_path = 'frontend/public/models/companion_avatar_teal.jpg'

    orig = Image.open(base_path).convert('RGB')
    arr_orig = np.array(orig, dtype=np.float32)
    arr = arr_orig.copy()
    h, w, _ = arr.shape
    y_grid, x_grid = np.indices((h, w))

    # 1. Warm Glowing Complexion (Soft peachy-golden warmth across facial skin)
    face_mask = (y_grid >= 240) & (y_grid <= 950) & (x_grid >= 260) & (x_grid <= 1020)
    
    # Gentle smoothing of harsh pores/freckles on face for the stylized realistic look
    orig_face = orig.crop((260, 240, 1020, 950))
    smooth_face = orig_face.filter(ImageFilter.GaussianBlur(radius=1.8))
    arr_smooth_face = np.array(smooth_face, dtype=np.float32)
    
    # Blend 45% smooth face with 55% original to keep detail while softening complexion
    arr[240:950, 260:1020] = arr[240:950, 260:1020] * 0.55 + arr_smooth_face * 0.45

    # Apply warm golden-peach color grade to face
    arr[face_mask, 0] = np.clip(arr[face_mask, 0] * 1.05 + 6, 0, 255)
    arr[face_mask, 1] = np.clip(arr[face_mask, 1] * 1.02 + 2, 0, 255)
    arr[face_mask, 2] = np.clip(arr[face_mask, 2] * 0.98, 0, 255)

    # 2. Rosy Cheek & Nose Tip Blush
    # Left cheek: center (y=610, x=430)
    dist_l_cheek = np.sqrt((x_grid - 430)**2 + (y_grid - 610)**2)
    blush_l_mask = np.clip(1.0 - (dist_l_cheek / 120.0), 0.0, 1.0)**2.0
    
    # Right cheek: center (y=610, x=830)
    dist_r_cheek = np.sqrt((x_grid - 830)**2 + (y_grid - 610)**2)
    blush_r_mask = np.clip(1.0 - (dist_r_cheek / 120.0), 0.0, 1.0)**2.0

    # Nose tip blush: center (y=640, x=630)
    dist_nose = np.sqrt((x_grid - 630)**2 + (y_grid - 640)**2)
    blush_nose_mask = np.clip(1.0 - (dist_nose / 65.0), 0.0, 1.0)**2.2

    blush_total = np.clip(blush_l_mask * 0.42 + blush_r_mask * 0.42 + blush_nose_mask * 0.35, 0.0, 0.70)
    blush_color = np.array([225.0, 115.0, 110.0], dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1.0 - blush_total) + blush_color[c] * blush_total

    # 3. Warm Rosy Lips with Soft Luster
    dist_mouth = np.sqrt(((x_grid - 630) / 110.0)**2 + ((y_grid - 720) / 45.0)**2)
    lip_blend = np.clip(1.0 - dist_mouth, 0.0, 1.0)**1.5 * 0.45
    lip_color = np.array([215.0, 105.0, 105.0], dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1.0 - lip_blend) + lip_color[c] * lip_blend

    # Lip gloss highlight
    dist_gloss = np.sqrt(((x_grid - 630) / 25.0)**2 + ((y_grid - 740) / 8.0)**2)
    gloss_blend = np.clip(1.0 - dist_gloss, 0.0, 1.0)**2.0 * 0.28
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1.0 - gloss_blend) + 255.0 * gloss_blend

    # 4. Defined Arched Eyebrows & Upper Eyelash/Eyeliner
    brow_color = np.array([55.0, 32.0, 22.0], dtype=np.float32)

    t_l = (x_grid - 430.0) / 140.0
    y_arch_l = 390.0 - 25.0 * np.sin(t_l * np.pi)
    dist_brow_l = np.sqrt(((x_grid - 500) / 70.0)**2 + ((y_grid - y_arch_l) / 14.0)**2)
    brow_l_mask = np.clip(1.0 - dist_brow_l, 0.0, 1.0)**2.0 * 0.65
    brow_l_mask = brow_l_mask * ((x_grid >= 430) & (x_grid <= 570) & (y_grid >= 340) & (y_grid <= 415))

    t_r = (x_grid - 690.0) / 140.0
    y_arch_r = 390.0 - 25.0 * np.sin(t_r * np.pi)
    dist_brow_r = np.sqrt(((x_grid - 760) / 70.0)**2 + ((y_grid - y_arch_r) / 14.0)**2)
    brow_r_mask = np.clip(1.0 - dist_brow_r, 0.0, 1.0)**2.0 * 0.65
    brow_r_mask = brow_r_mask * ((x_grid >= 690) & (x_grid <= 830) & (y_grid >= 340) & (y_grid <= 415))

    brow_total = np.clip(brow_l_mask + brow_r_mask, 0.0, 0.75)
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1.0 - brow_total) + brow_color[c] * brow_total

    # Eyeliner / upper lash line
    dist_lash_l = np.sqrt(((x_grid - 495) / 50.0)**2 + ((y_grid - 455) / 7.0)**2)
    lash_l_mask = np.clip(1.0 - dist_lash_l, 0.0, 1.0)**2.0 * 0.55 * ((x_grid >= 445) & (x_grid <= 545))

    dist_lash_r = np.sqrt(((x_grid - 765) / 50.0)**2 + ((y_grid - 455) / 7.0)**2)
    lash_r_mask = np.clip(1.0 - dist_lash_r, 0.0, 1.0)**2.0 * 0.55 * ((x_grid >= 715) & (x_grid <= 815))

    lash_total = np.clip(lash_l_mask + lash_r_mask, 0.0, 0.70)
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1.0 - lash_total) + 30.0 * lash_total

    # 5. Luminous Warm Hazel-Brown Eyes (Eye 1: (285, 118), Eye 2: (1038, 88))
    def paint_realistic_eye(center_x, center_y):
        eyeball_r = 115.0
        iris_r = 44.0
        pupil_r = 15.0

        dist = np.sqrt((x_grid - center_x)**2 + (y_grid - center_y)**2)
        eyeball_mask = dist <= eyeball_r

        sclera_depth = np.clip(dist / eyeball_r, 0.0, 1.0)
        sclera_r = 252.0 - sclera_depth * 15.0
        sclera_g = 250.0 - sclera_depth * 18.0
        sclera_b = 248.0 - sclera_depth * 20.0

        arr[eyeball_mask, 0] = sclera_r[eyeball_mask]
        arr[eyeball_mask, 1] = sclera_g[eyeball_mask]
        arr[eyeball_mask, 2] = sclera_b[eyeball_mask]

        iris_mask = dist <= iris_r
        t_iris = np.clip(dist / iris_r, 0.0, 1.0)
        limbal_factor = np.clip((t_iris - 0.75) / 0.25, 0.0, 1.0)**2.0
        
        angle = np.arctan2(y_grid - center_y, x_grid - center_x)
        fibers = 0.5 + 0.5 * np.sin(angle * 24.0) * 0.15 + np.cos(angle * 12.0) * 0.10

        iris_base_r = 150.0 * (1.0 - t_iris * 0.45) * (0.9 + fibers * 0.2)
        iris_base_g = 88.0 * (1.0 - t_iris * 0.50) * (0.9 + fibers * 0.2)
        iris_base_b = 42.0 * (1.0 - t_iris * 0.55) * (0.9 + fibers * 0.2)

        iris_r_col = iris_base_r * (1.0 - limbal_factor * 0.75) + 35.0 * (limbal_factor * 0.75)
        iris_g_col = iris_base_g * (1.0 - limbal_factor * 0.75) + 20.0 * (limbal_factor * 0.75)
        iris_b_col = iris_base_b * (1.0 - limbal_factor * 0.75) + 14.0 * (limbal_factor * 0.75)

        arr[iris_mask, 0] = iris_r_col[iris_mask]
        arr[iris_mask, 1] = iris_g_col[iris_mask]
        arr[iris_mask, 2] = iris_b_col[iris_mask]

        pupil_blend = np.clip((pupil_r - dist) / 3.0, 0.0, 1.0)
        pupil_mask = pupil_blend > 0.0
        for c in range(3):
            arr[pupil_mask, c] = arr[pupil_mask, c] * (1.0 - pupil_blend[pupil_mask]) + 8.0 * pupil_blend[pupil_mask]

        dist_hl = np.sqrt((x_grid - (center_x + 9))**2 + (y_grid - (center_y - 9))**2)
        hl_blend = np.clip(1.0 - (dist_hl / 7.0), 0.0, 1.0)**2.0 * 0.95
        hl_mask = hl_blend > 0.0
        for c in range(3):
            arr[hl_mask, c] = arr[hl_mask, c] * (1.0 - hl_blend[hl_mask]) + 255.0 * hl_blend[hl_mask]

        dist_hl2 = np.sqrt((x_grid - (center_x - 7))**2 + (y_grid - (center_y + 8))**2)
        hl2_blend = np.clip(1.0 - (dist_hl2 / 4.5), 0.0, 1.0)**2.0 * 0.45
        hl2_mask = hl2_blend > 0.0
        for c in range(3):
            arr[hl2_mask, c] = arr[hl2_mask, c] * (1.0 - hl2_blend[hl2_mask]) + 245.0 * hl2_blend[hl2_mask]

    paint_realistic_eye(285, 118)
    paint_realistic_eye(1038, 88)

    # 6. Pearly White Bright Clean Teeth
    teeth_mask_upper = (y_grid >= 1880) & (y_grid <= 2040) & (x_grid >= 480) & (x_grid <= 1050)
    teeth_mask_lower = (y_grid >= 780) & (y_grid <= 920) & (x_grid >= 1250) & (x_grid <= 1680)

    for tmask in [teeth_mask_upper, teeth_mask_lower]:
        lum = arr[:, :, :].mean(axis=2)
        valid_tooth = tmask & (lum > 70) & (arr[:, :, 0] > 70)
        is_gum = valid_tooth & (arr[:, :, 0] > arr[:, :, 1] * 1.35)
        is_enamel = valid_tooth & (~is_gum)

        enamel_target = np.array([252.0, 248.0, 242.0], dtype=np.float32)
        arr[is_enamel, 0] = np.clip(arr[is_enamel, 0] * 0.35 + enamel_target[0] * 0.65 + 20, 0, 255)
        arr[is_enamel, 1] = np.clip(arr[is_enamel, 1] * 0.35 + enamel_target[1] * 0.65 + 20, 0, 255)
        arr[is_enamel, 2] = np.clip(arr[is_enamel, 2] * 0.35 + enamel_target[2] * 0.65 + 25, 0, 255)

        gum_target = np.array([225.0, 115.0, 128.0], dtype=np.float32)
        arr[is_gum, 0] = np.clip(arr[is_gum, 0] * 0.4 + gum_target[0] * 0.6, 0, 255)
        arr[is_gum, 1] = np.clip(arr[is_gum, 1] * 0.4 + gum_target[1] * 0.6, 0, 255)
        arr[is_gum, 2] = np.clip(arr[is_gum, 2] * 0.4 + gum_target[2] * 0.6, 0, 255)

    # 7. Soft Heather Lavender-Grey Crewneck T-Shirt (matching reference image)
    # The shirt polygon in UV space occupies:
    # 1. Main Torso / Shoulders in bottom-right quadrant: y: 920..2048, x: 950..2048
    # 2. Torso sides / front under chest: y: 1080..2048, x: 100..1050 (where not hand/teeth)
    # 3. Ribbed Crewneck Collar Band: y: 950..1120, x: 230..1100
    
    # Heather fabric fine grain texture
    np.random.seed(42)
    heather_noise = (np.random.rand(h, w) - 0.5) * 6.0

    # Clean target color for soft heather lavender t-shirt: RGB(186, 175, 192)
    base_shirt_r = 186.0 + heather_noise
    base_shirt_g = 175.0 + heather_noise
    base_shirt_b = 192.0 + heather_noise

    # In bottom right quadrant (y: 920..2048, x: 950..2048), find shirt geometry:
    # Everything in this quadrant except hands/sneakers (which are in top-right y < 850)
    # Exclude armpit/inner mouth cutouts (which have dark edges)
    br_shirt_mask = (y_grid >= 930) & (x_grid >= 960) & (y_grid <= 2040)
    # Exclude the mouth cavity cutout (around y: 1650, x: 1900)
    mouth_cutout = (y_grid >= 1600) & (y_grid <= 1800) & (x_grid >= 1800) & (x_grid <= 2048)
    br_shirt_mask = br_shirt_mask & (~mouth_cutout)

    # Use subtle shading from original light side to create natural fabric folds
    # In orig, the light half was x: 1450..2048. Let's find fold modulation
    fold_sample = arr_orig[950:2000, 1450:2000].mean(axis=2)
    fold_factor = (fold_sample - fold_sample.mean()) / (fold_sample.std() + 1e-5) * 8.0
    # Create smooth fold texture across both sides
    fold_texture = np.zeros((h, w), dtype=np.float32)
    fold_texture[950:2000, 1450:2000] = fold_factor
    fold_texture[950:2000, 950:1450] = np.fliplr(fold_factor[:, :500])

    # Apply soft heather lavender to entire shirt body
    arr[br_shirt_mask, 0] = np.clip(base_shirt_r[br_shirt_mask] + fold_texture[br_shirt_mask], 0, 255)
    arr[br_shirt_mask, 1] = np.clip(base_shirt_g[br_shirt_mask] + fold_texture[br_shirt_mask], 0, 255)
    arr[br_shirt_mask, 2] = np.clip(base_shirt_b[br_shirt_mask] + fold_texture[br_shirt_mask], 0, 255)

    # Crewneck collar band: y: 950..1120, x: 230..1100
    # In orig, the collar band was the blue strip (y: 950..1120, x: 230..1100) where blue is prominent
    collar_mask = (y_grid >= 950) & (y_grid <= 1120) & (x_grid >= 230) & (x_grid <= 1100) & (arr_orig[:, :, 2] > arr_orig[:, :, 0] * 1.05)
    # Collar color: slightly deeper heather purple-grey (#9D91A3)
    arr[collar_mask, 0] = np.clip(160.0 + heather_noise[collar_mask], 0, 255)
    arr[collar_mask, 1] = np.clip(148.0 + heather_noise[collar_mask], 0, 255)
    arr[collar_mask, 2] = np.clip(166.0 + heather_noise[collar_mask], 0, 255)

    # Save finalized realistic texture map
    final_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    final_img.save(output_path, quality=95)
    # Also save to teal_path so both paths serve this texture
    final_img.save(teal_path, quality=95)
    print(f'Successfully generated {output_path} and updated {teal_path}!')

if __name__ == '__main__':
    build_realistic_texture()
