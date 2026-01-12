import os
import itertools
import errno
import numpy as np
from typing import List

from datatorch.api.scripts.utils.simplify import simplify_points


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
    """Convert a binary mask to COCO polygon format [[x1,y1,x2,y2,...]]"""
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


def points_to_segmentation(points: List[List[List[float]]]) -> List[List[float]]:
    """
    Converts from points format to COCO segmentation format.
    
    Converts from:
        [[[x1,y1], [x2,y2], ...]]
    to:
        [[x1,y1,x2,y2...]]
    """
    return [np.array(polygon).flatten().tolist() for polygon in points]


def segmentation_to_points(segmentation: List[List[float]]) -> List[List[List[float]]]:
    """
    Converts from COCO segmentation format to points format.
    
    Converts from:
        [[x1,y1,x2,y2...]]
    to:
        [[[x1,y1], [x2,y2], ...]]
    """
    return [np.reshape(polygon, (-1, 2)).tolist() for polygon in segmentation]


def simplify_segmentation(segmentation: List[List[float]], tolerance: float = 1) -> List[List[float]]:
    """
    Simplifies an array of polygons in COCO polygon format [[x1,y1,x2,y2,...]].
    
    Args:
        segmentation: List of polygons in COCO format
        tolerance: Simplification tolerance (0 to disable)
        
    Returns:
        Simplified polygons in COCO format
    """
    if tolerance == 0:
        return segmentation

    points_format = segmentation_to_points(segmentation)
    simplified = [
        simplify_points(polygon, tolerance=tolerance, highestQuality=False)
        for polygon in points_format
    ]
    # Filter out polygons with less than 3 points (6 coordinates)
    simplified = [polygon for polygon in simplified if len(polygon) >= 3]
    return points_to_segmentation(simplified)
