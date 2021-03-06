from common.numpy_fast import interp
import numpy as np
from selfdrive.controls.lib.latcontrol_helpers import model_polyfit, compute_path_pinv
from selfdrive.op_params import opParams


op_params = opParams()
CAMERA_OFFSET = op_params.get('cameraOffset', 0.06)  # m from center car to camera

def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)

def calc_d_poly(l_poly, r_poly, p_poly, l_prob, r_prob, lane_width):
  # This will improve behaviour when lanes suddenly widen
  lane_width = min(4.0, lane_width)
  l_prob = l_prob * interp(abs(l_poly[3]), [2, 2.5], [1.0, 0.0])
  r_prob = r_prob * interp(abs(r_poly[3]), [2, 2.5], [1.0, 0.0])

  path_from_left_lane = l_poly.copy()
  path_from_left_lane[3] -= lane_width / 2.0
  path_from_right_lane = r_poly.copy()
  path_from_right_lane[3] += lane_width / 2.0

  lr_prob = l_prob + r_prob - l_prob * r_prob

  d_poly_lane = (l_prob * path_from_left_lane + r_prob * path_from_right_lane) / (l_prob + r_prob + 0.0001)
  return lr_prob * d_poly_lane + (1.0 - lr_prob) * p_poly


class LanePlanner(object):
  def __init__(self):
    self.l_poly = [0., 0., 0., 0.]
    self.r_poly = [0., 0., 0., 0.]
    self.p_poly = [0., 0., 0., 0.]
    self.d_poly = [0., 0., 0., 0.]

    self.lane_width = 3.0
    self.readings = []
    self.frame = 0

    self.l_prob = 0.
    self.r_prob = 0.
    self.lr_prob = 0.

    self._path_pinv = compute_path_pinv()
    self.x_points = np.arange(50)

  def parse_model(self, md):
    if len(md.leftLane.poly):
      self.l_poly = np.array(md.leftLane.poly)
      self.r_poly = np.array(md.rightLane.poly)
      self.p_poly = np.array(md.path.poly)
    else:
      self.l_poly = model_polyfit(md.leftLane.points, self._path_pinv)  # left line
      self.r_poly = model_polyfit(md.rightLane.points, self._path_pinv)  # right line
      self.p_poly = model_polyfit(md.path.points, self._path_pinv)  # predicted path
    self.l_prob = md.leftLane.prob  # left line prob
    self.r_prob = md.rightLane.prob  # right line prob

  def update_lane(self, v_ego):
    # only offset left and right lane lines; offsetting p_poly does not make sense
    self.l_poly[3] += CAMERA_OFFSET
    self.r_poly[3] += CAMERA_OFFSET

    self.lr_prob = self.l_prob + self.r_prob - self.l_prob * self.r_prob

    # Find current lanewidth
    if self.l_prob > 0.49 and self.r_prob > 0.49:
        self.frame += 1
        if self.frame % 20 == 0:
            self.frame = 0
            current_lane_width = sorted((2.8, abs(self.l_poly[3] - self.r_poly[3]), 3.6))[1]
            max_samples = 30
            self.readings.append(current_lane_width)
            avg = mean(self.readings)
            self.lane_width = avg
            if len(self.readings) == max_samples:
                self.readings.pop(0)

    # Don't exit dive
    if abs(self.l_poly[3] - self.r_poly[3]) > self.lane_width:
        self.r_prob = self.r_prob / interp(self.l_prob, [0, 1], [1, 3])

    self.d_poly = calc_d_poly(self.l_poly, self.r_poly, self.p_poly, self.l_prob, self.r_prob, self.lane_width)

  def update(self, v_ego, md):
    self.parse_model(md)
    self.update_lane(v_ego)
