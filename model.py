!pip install ultralytics --quiet

import os
import glob
import random
import shutil
from IPython.display import Image, display
from ultralytics import YOLO

!unzip -q /content/wildboar_dataset.zip -d /content/wildboar_dataset

dataset_path = "/content/wildboar_dataset"
output_path = "/content/dataset"

train_path = f"{output_path}/train"
val_path = f"{output_path}/val"
test_path = f"{output_path}/test"

for split in [train_path, val_path, test_path]:
    os.makedirs(f"{split}/images", exist_ok=True)
    os.makedirs(f"{split}/labels", exist_ok=True)

images = glob.glob(f"{dataset_path}/images/*.jpg")
data = [(img, img.replace("images", "labels").replace(".jpg", ".txt")) for img in images]
random.shuffle(data)

train_split = int(0.7 * len(data))
val_split = int(0.2 * len(data))
train_data = data[:train_split]
val_data = data[train_split:train_split + val_split]
test_data = data[train_split + val_split:]

def move_files(pairs, dest):
    for img, ann in pairs:
        shutil.copy(img, f"{dest}/images/")
        shutil.copy(ann, f"{dest}/labels/")

move_files(train_data, train_path)
move_files(val_data, val_path)
move_files(test_data, test_path)

yaml_content = f"""
train: {train_path}/images
val: {val_path}/images
test: {test_path}/images

nc: 1
names: ['wildboar']
"""

with open(f"{output_path}/data.yaml", "w") as f:
    f.write(yaml_content)

model = YOLO('yolov8n.pt')
model.train(
    data=f"{output_path}/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    name="wildboar_detector",
    device=0
)

metrics = model.val()
print(metrics)

test_image = glob.glob(f"{test_path}/images/*.jpg")[0]
results = model.predict(source=test_image, save=True, conf=0.5)
display(Image(filename=results[0].save_dir / os.path.basename(test_image)))

model.export(format="onnx")
print("Model exported successfully.")
