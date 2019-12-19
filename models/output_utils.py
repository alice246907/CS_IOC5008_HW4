import torch
import torch.nn.functional as F
import numpy as np
import cv2

from config import cfg, mask_type, MEANS, STD, activation_func
from box_utils import crop, sanitize_coordinates


import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "../data"))
sys.path.append(os.path.join(BASE_DIR, "../utils"))


def postprocess(
    det_output,
    w,
    h,
    batch_idx=0,
    interpolation_mode="bilinear",
    visualize_lincomb=False,
    crop_masks=True,
    score_threshold=0,
):
    """
    Postprocesses the output of Yolact
    on testing mode into a format that makes sense,
    accounting for all the possible configuration settings.

    Args:
        - det_output: The lost of dicts that Detect outputs.
        - w: The real with of the image.
        - h: The real height of the image.
        - batch_idx: If you have multiple images
            for this batch, the image's index in the batch.
        - interpolation_mode: Can be 'nearest' | 'area' | 'bilinear'
        (see torch.nn.functional.interpolate)

    Returns 4 torch Tensors (in the following order):
        - classes [num_det]: The class idx for each detection.
        - scores  [num_det]: The confidence score for each detection.
        - boxes   [num_det, 4]:
                The bounding box for each detection in absolute point form.
        - masks   [num_det, h, w]: Full image masks for each detection.
    """

    dets = det_output[batch_idx]
    # dets = det_output

    if dets is None:
        return [torch.Tensor()] * 4
    if score_threshold > 0:
        keep = dets["score"] > score_threshold

        for k in dets:
            if k != "proto":
                dets[k] = dets[k][keep]

        if dets["score"].size(0) == 0:
            return [torch.Tensor()] * 4

    classes = dets["class"]
    boxes = dets["box"]
    scores = dets["score"]
    masks = dets["mask"]

    if cfg.mask_type == mask_type.lincomb and cfg.eval_mask_branch:
        proto_data = dets["proto"]

        if visualize_lincomb:
            display_lincomb(proto_data, masks)

        masks = proto_data @ masks.t()
        masks = cfg.mask_proto_mask_activation(masks)

        if crop_masks:
            masks = crop(masks, boxes)

        masks = masks.permute(2, 0, 1).contiguous()

        masks = F.interpolate(
            masks.unsqueeze(0),
            (h, w),
            mode=interpolation_mode,
            align_corners=False,
        ).squeeze(0)

        # Binarize the masks
        masks.gt_(0.5)

    boxes[:, 0], boxes[:, 2] = sanitize_coordinates(
        boxes[:, 0], boxes[:, 2], w, cast=False
    )
    boxes[:, 1], boxes[:, 3] = sanitize_coordinates(
        boxes[:, 1], boxes[:, 3], h, cast=False
    )
    boxes = boxes.long()

    if cfg.mask_type == mask_type.direct and cfg.eval_mask_branch:
        # Upscale masks
        full_masks = torch.zeros(masks.size(0), h, w)

        for jdx in range(masks.size(0)):
            x1, y1, x2, y2 = boxes[jdx, :]

            mask_w = x2 - x1
            mask_h = y2 - y1

            # Just in case
            if mask_w * mask_h <= 0 or mask_w < 0:
                continue

            mask = masks[jdx, :].view(1, 1, cfg.mask_size, cfg.mask_size)
            mask = F.interpolate(
                mask,
                (mask_h, mask_w),
                mode=interpolation_mode,
                align_corners=False,
            )
            mask = mask.gt(0.5).float()
            full_masks[jdx, y1:y2, x1:x2] = mask

        masks = full_masks

    return classes, scores, boxes, masks


def undo_image_transformation(img, w, h):
    """
    Takes a transformed image tensor and
    returns a numpy ndarray that is untransformed.
    Arguments w and h are the original height and width of the image.
    """
    img_numpy = img.permute(1, 2, 0).cpu().numpy()
    img_numpy = img_numpy[:, :, (2, 1, 0)]  # To BRG

    if cfg.backbone.transform.normalize:
        img_numpy = (img_numpy * np.array(STD) + np.array(MEANS)) / 255.0
    elif cfg.backbone.transform.subtract_means:
        img_numpy = (img_numpy / 255.0 + np.array(MEANS) / 255.0).astype(
            np.float32
        )

    img_numpy = img_numpy[:, :, (2, 1, 0)]  # To RGB
    img_numpy = np.clip(img_numpy, 0, 1)

    return cv2.resize(img_numpy, (w, h))


def display_lincomb(proto_data, masks):
    out_masks = torch.matmul(proto_data, masks.t())

    for kdx in range(1):
        jdx = kdx + 0
        import matplotlib.pyplot as plt

        coeffs = masks[jdx, :].cpu().numpy()
        idx = np.argsort(-np.abs(coeffs))

        coeffs_sort = coeffs[idx]
        arr_h, arr_w = (4, 8)
        proto_h, proto_w, _ = proto_data.size()
        arr_img = np.zeros([proto_h * arr_h, proto_w * arr_w])
        arr_run = np.zeros([proto_h * arr_h, proto_w * arr_w])

        for y in range(arr_h):
            for x in range(arr_w):
                i = arr_w * y + x

                if i == 0:
                    running_total = (
                        proto_data[:, :, idx[i]].cpu().numpy() * coeffs_sort[i]
                    )
                else:
                    running_total += (
                        proto_data[:, :, idx[i]].cpu().numpy() * coeffs_sort[i]
                    )

                running_total_nonlin = running_total
                if cfg.mask_proto_mask_activation == activation_func.sigmoid:
                    running_total_nonlin = 1 / (
                        1 + np.exp(-running_total_nonlin)
                    )

                arr_img[
                    y * proto_h: (y + 1) * proto_h,
                    x * proto_w: (x + 1) * proto_w,
                ] = (
                    (
                        proto_data[:, :, idx[i]]
                        / torch.max(proto_data[:, :, idx[i]])
                    )
                    .cpu()
                    .numpy()
                    * coeffs_sort[i]
                )
                arr_run[
                    y * proto_h: (y + 1) * proto_h,
                    x * proto_w: (x + 1) * proto_w,
                ] = (running_total_nonlin > 0.5).astype(np.float)
        plt.imshow(arr_img)
        plt.show()
        plt.imshow(out_masks[:, :, jdx].cpu().numpy())
        plt.show()
