# Dataset Preparation Guidelines for Security Object Detection Model Training
# This file provides instructions for setting up your training dataset

## Dataset Structure

Your dataset should follow this directory structure:

```
/path/to/dataset/
├── images/
│   ├── train/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   │   └── ...
│   └── val/
│       ├── img101.jpg
│       ├── img102.jpg
│       └── ...
├── labels/
│   ├── train/
│   │   ├── img001.txt
│   │   ├── img002.txt
│   │   └── ...
│   └── val/
│       ├── img101.txt
│       ├── img102.txt
│       └── ...
```

## Class Structure

The model will be trained with these 5 classes:

0. person - Any human figure
1. weapon - Guns, knives, or other weapons
2. helmet - Any type of helmet/head covering
3. mask - Face masks or coverings
4. suspicious - Suspicious behavior/posture

## Label Format

YOLO format labels are text files with one line per object:
`<class_id> <x_center> <y_center> <width> <height>`

Where:
- `class_id`: Integer class identifier (0-4 as defined above)
- `x_center`, `y_center`: Center coordinates normalized to [0-1]
- `width`, `height`: Object dimensions normalized to [0-1]

Example label file content:
```
0 0.5 0.5 0.3 0.6    # person in center
1 0.7 0.6 0.1 0.2    # weapon on right side
```

## Data Collection Guidelines

1. **Image Variety**:
   - Include different lighting conditions
   - Capture various angles and distances
   - Include both indoor and outdoor scenes
   - Ensure diversity of weapon types

2. **Balanced Classes**:
   - Aim for at least 500 images per class (more is better)
   - Include many examples of weapons in different contexts
   - Ensure good representation of each class

3. **Data Augmentation**:
   - The training script includes automatic augmentation
   - For best results, still provide variety in your source images

## Data Sources

1. **Custom Data Collection**:
   - Take photos in your environment
   - Stage scenarios with props (fake weapons)
   - Capture real surveillance camera footage

2. **Public Datasets**:
   - Consider these open datasets for weapons detection:
     - RWF (Real-World Firearms Dataset)
     - WDDB (Weapon Detection Dataset Benchmark)
     - Open Images (has weapon categories)

3. **Synthetic Data**:
   - Consider generating synthetic data for weapons
   - Use image generation tools for rare scenarios

## Notes

- Update the path in `security_dataset.yaml` to point to your dataset location
- Ensure proper annotation of all objects in each image
- Split your dataset approximately 80% training, 20% validation
