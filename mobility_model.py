from abc import ABC
import pandas as pd
from vehicle import Vehicle
import numpy as np
import random


class MobiltyModel(ABC):

    def positions(self):
        """Generator function that returns the next position of the vehicle"""
        pass


# TODO: Create a factory class that takes config as param
# TODO: include file_path in config file

class DynamicMobilityModel(MobiltyModel):

    def __init__(self, file_path, config):
        """Takes a mobility dataset and generates vehicles positions"""
        self.df = pd.read_csv(file_path)
        self.trajectory = None
        self.config = config
        self.vehicles = {}

    def update_vehicles(self, env, frame_id):
        df = self.df[self.df["Frame_ID"] == frame_id]
        df = df[~df["Vehicle_ID"].isin(self.vehicles.keys())]["Vehicle_ID"]
        for _, idx in df.items():
            v = Vehicle(
                idx,
                env,
                self.config["desired_data_rate"],
            )
            v.set_mobility_model(self)
            self.vehicles[idx] = v

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
                v = self.vehicles.pop(vehicle.id)
                del v
                yield (-1, -1)
                break

            yield position


class StaticSimulatedMobilityModel(MobiltyModel):

    def __init__(self, config):
        """Takes a mobility dataset and generates vehicles positions"""
        self.config = config
        self.vehicles = {}
        self.pos = {}
        self.mxidx = 0

    def update_vehicles(self, env, frame_id):
        arr_vehicles = np.random.poisson(10)
        dep_vehicles = int(np.random.exponential(5))
        if len(self.vehicles) > dep_vehicles:
            for i in range(dep_vehicles):
                idx = random.choice(list(self.vehicles.keys()))
                v = self.vehicles.pop(idx)
                # self.pos.pop(idx)
                del v
        for i in range(arr_vehicles):
            v = Vehicle(
                self.mxidx,
                env,
                self.config["desired_data_rate"],
            )
            v.set_mobility_model(self)
            self.vehicles[self.mxidx] = v
            self.mxidx += 1

    def positions(self, vehicle):
        """
        Starts with first position in the data and yield position
        """

        na = self.config['network_area']
        origin = self.config['topology_origin']
        pos = (origin[0]+random.randint(
            0, na[0]), origin[1]+random.randint(0, na[1]))
        while True:
            try:
                position = pos
            except IndexError:
                yield (-1, -1)

            yield position
