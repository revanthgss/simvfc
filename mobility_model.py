from abc import ABC
import pandas as pd
from .vehicle import Vehicle


class MobiltyModel(ABC):

    def positions(self):
        """Generator function that returns the next position of the vehicle"""
        pass


class DynamicMobilityModel(MobiltyModel):

    def __init__(self, file_path, config):
        """Takes a mobility dataset and generates vehicles positions"""
        self.df = pd.read_csv(file_path)
        self.trajectory = None
        self.config = config
        self.vehicles = {}

    def update_vehicles(self, frame_id):
        df = self.df[self.df["Frame_ID"] == frame_id]
        df = df[~df["Vehicle_ID"].isin(self.vehicles.keys())]["Vehicle_ID"]
        for _, idx in df.items():
            v = Vehicle(
                idx,
                self.env,
                self.service_store,
                self.config["desired_data_rate"],
            )
            v.set_mobility_model(self)
            self.vehicles[idx] = v
        pass

    def positions(self, vehicle):
        """
        Starts with first position in the data and yield position
        """
        self.trajectory = self.df[self.df["Vehicle_ID"]
                                  == vehicle.id].sort_values(by="Frame_ID")
        cur_idx = 0
        while True:
            try:
                position = (
                    self.trajectory.iloc[cur_idx]["Global_X"], self.trajectory.iloc[cur_idx]["Global_Y"])
                cur_idx += 1
            except IndexError:
                del self.vehicles[vehicle.id]
                _ = self.vehicles.pop(vehicle.id)
                yield (-1, -1)

            yield position
