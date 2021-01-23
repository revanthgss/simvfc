from abc import ABC
import pandas as pd


class AbstractMobiltyModel(ABC):

    def get_position(self):
        """Generator function that returns the next position of the vehicle"""
        pass


class DynamicMobilityModel(AbstractMobiltyModel):

    def __init__(self, file_path, vehicle):
        """Takes a mobility dataset and generates vehicles positions"""
        df = pd.read_csv(file_path)
        self.trajectory = df[df["Vehicle_ID"]
                             == vehicle.id].sort_values(by="Frame_ID")

    def get_position(self):
        """
        Starts with first position in the data and yield position
        """
        cur_idx = 0
        while True:
            try:
                position = (
                    self.trajectory.iloc[cur_idx]["Global_X"], self.trajectory.iloc[cur_idx]["Global_Y"])
                cur_idx += 1
            except IndexError:
                # If the index is out of bounds stop the vehicle at the last known location and yield the same value
                position = (self.trajectory.iloc[cur_idx-1]["Global_X"],
                            self.trajectory.iloc[cur_idx-1]["Global_Y"])

            yield position
