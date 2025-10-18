import cv2
import numpy as np
import time
try:
    import tflite_runtime.interpreter as tflite
except Exception:
    import tensorflow as tf
    tflite = tf.lite

class TFLiteDetector:
    def __init__(self, model_path, label_map=None, threshold=0.5, camera_index=0, width=320, height=320):
        self.model_path = model_path
        self.threshold = threshold
        self.label_map = label_map or {0: "object"}
        self.width = width
        self.height = height
        self.cam = cv2.VideoCapture(camera_index)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        print("[detector] model loaded:", model_path)

    def preprocess(self, frame):
        img = cv2.resize(frame, (self.width, self.height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        return np.expand_dims(img, axis=0)

    def detect_frame(self):
        ret, frame = self.cam.read()
        if not ret:
            return None, []
        input_data = self.preprocess(frame)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        out = {}
        for od in self.output_details:
            out[od['name']] = self.interpreter.get_tensor(od['index'])
        try:
            boxes = out.get('StatefulPartitionedCall:1', None) or out.get('detection_boxes', out.get(self.output_details[0]['name']))
            classes = out.get('StatefulPartitionedCall:3', None) or out.get('detection_classes', None)
            scores = out.get('StatefulPartitionedCall:2', None) or out.get('detection_scores', None)
        except Exception:
            vals = [self.interpreter.get_tensor(i['index']) for i in self.output_details]
            boxes, classes, scores = vals[0], vals[1], vals[2]

        boxes = np.squeeze(boxes)
        scores = np.squeeze(scores)
        classes = np.squeeze(classes).astype(np.int32) if classes is not None else np.zeros_like(scores, dtype=np.int32)
        detections = []
        h, w = frame.shape[:2]
        for i, score in enumerate(scores):
            if score >= self.threshold:
                box = boxes[i]
                y1, x1, y2, x2 = box
                x1_i, y1_i, x2_i, y2_i = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
                cls = classes[i] if classes is not None else 0
                label = self.label_map.get(cls, str(cls))
                detections.append({
                    "label": label,
                    "score": float(score),
                    "bbox": (x1_i, y1_i, x2_i, y2_i)
                })
        return frame, detections

    def close(self):
        self.cam.release()
