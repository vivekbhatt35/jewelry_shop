import numpy as np
import cv2
import os

def hands_up_detect(poses):
    # Assume COCO: 5=Lshoulder, 6=Rshoulder, 9=Lwrist, 10=Rwrist
    alert_indices = []
    for idx, person in enumerate(poses):
        if len(person) < 51:
            continue
        lshoulder_y = person[1 + 5*3]
        rshoulder_y = person[1 + 6*3]
        lwrist_y = person[1 + 9*3]
        rwrist_y = person[1 + 10*3]
        if lwrist_y < lshoulder_y and rwrist_y < rshoulder_y:
            alert_indices.append(idx)
    return alert_indices  # List of indexes for persons with hands up

def get_person_bboxes(poses):
    bboxes = []
    for person in poses:
        xs = person[0::3]
        ys = person[1::3]
        if xs and ys:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            bboxes.append([int(min_x), int(min_y), int(max_x), int(max_y)])
        else:
            bboxes.append(None)
    return bboxes

def draw_bboxes(image, bboxes, indices, color=(0, 0, 255), thickness=3):
    for idx in indices:
        if bboxes[idx] is not None:
            x1, y1, x2, y2 = bboxes[idx]
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    return image

def draw_detection_boxes(image, detection_bboxes, color=(0, 0, 255), thickness=4):
    for bbox in detection_bboxes:
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    return image
