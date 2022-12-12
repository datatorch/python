import os
import itertools
import errno


def binmask2cocorle(binary_mask):
    """Takes in a binary mask and converts to COCO RLE"""
    rle = {"counts": [], "size": list(binary_mask.shape)}
    counts = rle.get("counts")

    last_elem = 0
    running_length = 0

    for i, elem in enumerate(binary_mask.ravel(order="F")):
        if elem == last_elem:
            pass
        else:
            counts.append(running_length)
            running_length = 0
            last_elem = elem
        running_length += 1

    counts.append(running_length)

    return rle


def binmask2cocopoly(binary_mask):
    try:
        from cv2 import findContours, RETR_TREE, CHAIN_APPROX_SIMPLE
    except:
        print("Error. Please install and import opencv-python to use this function:")
        print("\t pip3 install opencv-python")
        print("\t import cv2")

    contours, _ = findContours(binary_mask, RETR_TREE, CHAIN_APPROX_SIMPLE)
    segmentation = []
    valid_poly = 0
    for contour in contours:
        if contour.size >= 6:
            segmentation.append(contour.astype(float).flatten().tolist())
            valid_poly += 1
    if valid_poly == 0:
        raise ValueError
    return segmentation
