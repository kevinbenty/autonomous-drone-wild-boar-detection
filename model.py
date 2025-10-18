from google.colab import files
uploaded = files.upload()

import os
dataset_zip = list(uploaded.keys())[0]
print(f"Uploaded dataset: {dataset_zip}")

from zipfile import ZipFile
extract_to = '/content/wild_boar_dataset'
with ZipFile(dataset_zip, 'r') as zip_ref:
    zip_ref.extractall(extract_to)

print("Dataset extracted to:", extract_to)
print("Contents:", os.listdir(extract_to))

!pip install ultralytics

from ultralytics import YOLO
import yaml
print("YOLOv8 imported successfully!")

data_config = {
    'path': extract_to,
    'train': f'{extract_to}/train',
    'val': f'{extract_to}/valid',
    'test': f'{extract_to}/test',
    'nc': 1,
    'names': ['wild_boar']
}

yaml_path = '/content/wild_boar.yaml'
with open(yaml_path, 'w') as file:
    yaml.dump(data_config, file)

print("Dataset YAML file created at:", yaml_path)

model = YOLO('yolov8s.pt')
results = model.train(data=yaml_path, epochs=50, imgsz=640, batch=16, name='wild_boar_yolov8')

metrics = model.val()
print("Evaluation complete!")

test_path = f"{extract_to}/test"
model.predict(source=test_path, conf=0.25, save=True)

import glob
from IPython.display import Image, display

output_dir = sorted(glob.glob('/content/runs/detect/*'))[-1]
output_images = glob.glob(f"{output_dir}/*.jpg")

if output_images:
    print(f"Showing result from: {output_images[0]}")
    display(Image(filename=output_images[0]))
else:
    print("No detection images found in:", output_dir)
