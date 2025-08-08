#!/bin/bash
# Setup script for preparing the model training environment

# Create a new Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r training_requirements.txt

# Check CUDA availability for PyTorch
echo "Checking CUDA availability..."
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device Count:', torch.cuda.device_count() if torch.cuda.is_available() else 0)"

# Create directories for dataset if they don't exist
echo "Setting up dataset directories..."
mkdir -p dataset/images/train
mkdir -p dataset/images/val
mkdir -p dataset/labels/train
mkdir -p dataset/labels/val

# Update dataset path in YAML file
echo "Updating dataset path in YAML configuration..."
sed -i '' "s|path: /path/to/dataset|path: $(pwd)/dataset|g" security_dataset.yaml

echo ""
echo "Setup complete! Follow these steps to begin:"
echo "1. Place your training images in dataset/images/train and dataset/images/val"
echo "2. Place your label files in dataset/labels/train and dataset/labels/val"
echo "3. Verify security_dataset.yaml has the correct path"
echo "4. Run the training with: python train_security_model.py"
echo ""
echo "For detailed instructions on dataset preparation, see dataset_preparation_guide.md"
