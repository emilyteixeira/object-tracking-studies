from collections import OrderedDict
import numpy as np


class CentroidTracker:
    """
    Rastreador de centróides baseado em distância euclidiana mínima.
    Extraído de speed_detection_test2.py — lógica inalterada.
    """

    def __init__(self, max_disappeared: int = 30):
        self.next_object_id = 0
        self.objects: OrderedDict = OrderedDict()      # id -> (cx, cy)
        self.disappeared: OrderedDict = OrderedDict()  # id -> frames desaparecido
        self.max_disappeared = max_disappeared

    def register(self, centroid: tuple) -> None:
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id: int) -> None:
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]

    def update(self, input_centroids: list) -> OrderedDict:
        input_centroids = [tuple(map(int, c)) for c in input_centroids]

        if len(input_centroids) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        if len(self.objects) == 0:
            for c in input_centroids:
                self.register(c)
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = np.array(list(self.objects.values()), dtype="int32")
        input_centroids_arr = np.array(input_centroids, dtype="int32")

        D = np.linalg.norm(
            np.expand_dims(object_centroids, axis=1) -
            np.expand_dims(input_centroids_arr, axis=0),
            axis=2
        )

        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows: set = set()
        used_cols: set = set()

        for (row, col) in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            object_id = object_ids[row]
            self.objects[object_id] = tuple(input_centroids[col])
            self.disappeared[object_id] = 0
            used_rows.add(row)
            used_cols.add(col)

        unused_rows = set(range(0, D.shape[0])).difference(used_rows)
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        unused_cols = set(range(0, len(input_centroids))).difference(used_cols)
        for col in unused_cols:
            self.register(input_centroids[col])

        return self.objects
