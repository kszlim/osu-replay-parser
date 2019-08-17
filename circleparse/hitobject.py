import math
import copy
from . import mathhelper, curves

class SliderTick(object):
    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

class HitObject(object):
    def __init__(self, x, y, time, object_type, slider_type = None, curve_points = None, repeat = 1, pixel_length = 0, timing_point = None, difficulty = None, tick_distance = 1):
        """
        HitObject params for normal hitobject and sliders

        x -- x position
        y -- y position
        time -- timestamp
        object_type -- type of object (bitmask)

        [+] IF SLIDER
        slider_type -- type of slider (L, P, B, C)
        curve_points -- points in the curve path
        repeat -- amount of repeats for the slider (+1)
        pixel_length -- length of the slider
        timing_point -- ref of current timing point for the timestamp
        difficulty -- ref of beatmap difficulty
        tick_distance -- distance betwin each slidertick
        """
        self.x = x
        self.y = y
        self.time = time
        self.type = object_type

        #isSlider?
        if 2 & self.type:
            self.slider_type = slider_type
            self.curve_points = [mathhelper.Vec2(self.x, self.y)] + curve_points
            self.repeat = repeat
            self.pixel_length = pixel_length

            #For slider tick calculations
            self.timing_point = timing_point
            self.difficulty = difficulty
            self.tick_distance = tick_distance
            self.duration = (int(self.timing_point["raw_bpm"]) * (pixel_length / (self.difficulty["SliderMultiplier"] * self.timing_point["spm"])) / 100) * self.repeat

            self.ticks = []
            self.end_ticks = []

            self.calc_slider()
    
    def calc_slider(self, calc_path = False):
        #Fix broken objects
        if self.slider_type == "P" and len(self.curve_points) > 3:
            self.slider_type = "B"
        elif len(self.curve_points) == 2:
            self.slider_type = "L"

        #Make curve
        if self.slider_type == "P":     #Perfect
            try:
                curve = curves.Perfect(self.curve_points)
            except:
                curve = curves.Bezier(self.curve_points)
                self.slider_type = "B"
        elif self.slider_type == "B":   #Bezier
            curve = curves.Bezier(self.curve_points)
        elif self.slider_type == "C":   #Catmull
            curve = curves.Catmull(self.curve_points)

        #Quickest to skip this
        if calc_path: #Make path if requested (For drawing visual for testing)
            if self.slider_type == "L":     #Linear
                self.path = curves.Linear(self.curve_points).pos
            elif self.slider_type == "P":   #Perfect
                self.path = []
                l = 0
                step = 5
                while l <= self.pixel_length:
                    self.path.append(curve.point_at_distance(l))
                    l += step
            elif self.slider_type == "B":   #Bezier
                self.path = curve.pos
            elif self.slider_type == "C":   #Catmull
                self.path = curve.pos
            else:
                raise Exception("Slidertype not supported! ({})".format(self.slider_type))

        #Set slider ticks
        current_distance = self.tick_distance
        time_add = self.duration * (self.tick_distance / (self.pixel_length * self.repeat))

        while current_distance < self.pixel_length - self.tick_distance / 8:
            if self.slider_type == "L":     #Linear
                point = mathhelper.point_on_line(self.curve_points[0], self.curve_points[1], current_distance)
            else:   #Perfect, Bezier & Catmull uses the same function
                point = curve.point_at_distance(current_distance)

            self.ticks.append(SliderTick(point.x, point.y, self.time + time_add * (len(self.ticks) + 1)))
            current_distance += self.tick_distance

        #Adds slider_ends / repeat_points
        repeat_id = 1
        repeat_bonus_ticks = []
        while repeat_id < self.repeat:
            dist = (1 & repeat_id) * self.pixel_length
            time_offset = (self.duration / self.repeat) * repeat_id

            if self.slider_type == "L":     #Linear
                point = mathhelper.point_on_line(self.curve_points[0], self.curve_points[1], dist)
            else:   #Perfect, Bezier & Catmull uses the same function
                point = curve.point_at_distance(dist)

            self.end_ticks.append(SliderTick(point.x, point.y, self.time + time_offset))

            #Adds the ticks that already exists on the slider back (but reversed)
            repeat_ticks = copy.deepcopy(self.ticks)

            if 1 & repeat_id: #We have to reverse the timing normalizer
                repeat_ticks = list(reversed(repeat_ticks))
                normalize_time_value = self.time + (self.duration / self.repeat)
            else:
                normalize_time_value = self.time

            #Correct timing
            for tick in repeat_ticks:
                tick.time = self.time + time_offset + abs(tick.time - normalize_time_value)

            repeat_bonus_ticks += repeat_ticks

            repeat_id += 1

        self.ticks += repeat_bonus_ticks

        #Add endpoint for slider
        dist_end = (1 & self.repeat) * self.pixel_length
        if self.slider_type == "L":     #Linear
            point = mathhelper.point_on_line(self.curve_points[0], self.curve_points[1], dist_end)
        else:   #Perfect, Bezier & Catmull uses the same function
            point = curve.point_at_distance(dist_end)

        self.end_ticks.append(SliderTick(point.x, point.y, self.time + self.duration))

    def get_combo(self):
        """
        Returns the combo given by this object
        1 if normal hitobject, 2+ if slider (adds sliderticks)
        """
        if 2 & self.type:   #Slider
            val = 1                     #Start of the slider
            val += len(self.ticks)      #The amount of sliderticks
            val += self.repeat          #Reverse slider
        else:   #Normal
            val = 1                     #Itself...
        
        return val