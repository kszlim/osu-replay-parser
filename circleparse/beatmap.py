from . import mathhelper
from .hitobject import HitObject

class Beatmap(object):
    """
    Beatmap object for beatmap parsing and handling
    """

    def __init__(self, file_name):
        """
        file_name -- Directory for beatmap file (.osu)
        """
        self.file_name = file_name
        self.version = -1   #Unknown by default
        self.header = -1
        self.difficulty = {}
        self.timing_points = {
            "raw_bpm": {},  #Raw bpm modifier code
            "raw_spm": {}, #Raw speed modifier code
            "bpm": {},  #Beats pr minute
            "spm": {}   #Speed modifier
        }
        self.slider_point_distance = 1  #Changes after [Difficulty] is fully parsed
        self.hitobjects = []
        self.max_combo = 0
        self.parse_beatmap()

        if "ApproachRate" not in self.difficulty.keys():    #Fix old osu version
            self.difficulty["ApproachRate"] = self.difficulty["OverallDifficulty"]

        #print("Beatmap parsed!")
    
    def parse_beatmap(self):
        """
        Parses beatmap file line by line by passing each line into parse_line.
        """
        with open(self.file_name, encoding="utf8") as file_stream:
            ver_line = ""
            while len(ver_line) < 2: #Find the line where beatmap version is spesified (normaly first line)
                ver_line = file_stream.readline()
            self.version = int(''.join(list(filter(str.isdigit, ver_line))))  #Set version
            for line in file_stream:
                self.parse_line(line.replace("\n", ""))

    def parse_line(self, line):
        """
        Parse a beatmapfile line.

        Handles lines that are required for our use case (Difficulty, TimingPoints & hitobjects), 
        everything else is skipped.
        """
        if len(line) < 1:
            return

        if line.startswith("["):
            if line == "[Difficulty]":
                self.header = 0
            elif line == "[TimingPoints]":
                self.header = 1
            elif line == "[HitObjects]":
                self.header = 2
                self.slider_point_distance = (100 * self.difficulty["SliderMultiplier"]) / self.difficulty["SliderTickRate"]
            else:
                self.header = -1
            return

        if self.header == -1: #We return if we are reading under a header we dont care about
            return

        if self.header == 0:
            self.handle_difficulty_propperty(line)
        elif self.header == 1:
            self.handle_timing_point(line)
        elif self.header == 2:
            self.handle_hitobject(line)
    
    def handle_difficulty_propperty(self, propperty):
        """
        Puts the [Difficulty] propperty into the difficulty dict.
        """
        prop = propperty.split(":")
        self.difficulty[prop[0]] = float(prop[1])

    def handle_timing_point(self, timing_point):
        """
        Formats timing points used for slider velocity changes,
        and store them into self.timing_points dict.
        """
        timing_point_split = timing_point.split(",")
        timing_point_time = int(float(timing_point_split[0])) #Fixes some special mappers special needs to use floats
        timing_point_focus = timing_point_split[1]
        
        timing_point_type = 1
        if len(timing_point_split) >= 7: #Fix for old beatmaps that only stores bpm change and timestamp (only BPM change) [v3?]
            timing_point_type = int(timing_point_split[6])

        if timing_point_type == 0 and not timing_point_focus.startswith("-"):
            timing_point_focus = "-100"

        if timing_point_focus.startswith("-"):  #If not then its not a slider velocity modifier
            self.timing_points["spm"][timing_point_time] = -100 / float(timing_point_focus) #Convert to normalized value and store
            self.timing_points["raw_spm"][timing_point_time] = float(timing_point_focus)
        else:
            if len(self.timing_points["bpm"]) == 0: #Fixes if hitobjects shows up before bpm is set
                timing_point_time = 0

            self.timing_points["bpm"][timing_point_time] = 60000 / float(timing_point_focus)#^
            self.timing_points["raw_bpm"][timing_point_time] = float(timing_point_focus)
            #This trash of a game resets the spm when bpm change >.>
            self.timing_points["spm"][timing_point_time] = 1
            self.timing_points["raw_spm"][timing_point_time] = -100


    def handle_hitobject(self, line):
        """
        Puts every hitobject into the hitobjects array.

        Creates hitobjects, hitobject_sliders or skip depending on the given data.
        We skip everything that is not important for us for our use case (Spinners)
        """
        split_object = line.split(",")
        time = int(split_object[2])
        object_type = int(split_object[3])

        if not (1 & object_type > 0 or 2 & object_type > 0):  #We only want sliders and circles as spinners are random bannanas etc.
            return

        if 2 & object_type:  #Slider
            repeat = int(split_object[6])
            pixel_length = float(split_object[7])

            time_point = self.get_timing_point_all(time)

            tick_distance = (100 * self.difficulty["SliderMultiplier"]) / self.difficulty["SliderTickRate"]
            if self.version >= 8:
                #tick_distance /= time_point["spm"]
                tick_distance /= (mathhelper.clamp(-time_point["raw_spm"], 10, 1000) / 100)
            
            #tick_distance /= time_point["spm"]

            curve_split = split_object[5].split("|")
            curve_points = []
            for i in range(1, len(curve_split)):
                vector_split = curve_split[i].split(":")
                vector = mathhelper.Vec2(int(vector_split[0]), int(vector_split[1]))
                curve_points.append(vector)

            slider_type = curve_split[0]
            if self.version <= 6 and len(curve_points) >= 2:
                if slider_type == "L":
                    slider_type = "B"
                
                if len(curve_points) == 2:
                    if (int(split_object[0]) == curve_points[0].x and int(split_object[1]) == curve_points[0].y) or (curve_points[0].x == curve_points[1].x and curve_points[0].y == curve_points[1].y):
                        del curve_points[0]
                        slider_type = "L"

            if len(curve_points) == 0: #Incase of ExGon meme (Sliders that acts like hitcircles)
                hitobject = HitObject(int(split_object[0]), int(split_object[1]), time, 1)
            else:
                hitobject = HitObject(int(split_object[0]), int(split_object[1]), time, object_type, slider_type, curve_points, repeat, pixel_length, time_point, self.difficulty, tick_distance)
        else:
            hitobject = HitObject(int(split_object[0]), int(split_object[1]), time, object_type)

        self.hitobjects.append(hitobject)
        self.max_combo += hitobject.get_combo()

    def get_timing_point_all(self, time):
        """
        Returns a object of all current timing types

        time -- timestamp
        return -- {"raw_bpm": Float, "raw_spm": Float, "bpm": Float, "spm": Float}
        """
        types = {
            "raw_bpm": 600,
            "raw_spm": -100,
            "bpm": 100,
            "spm": 1
        }   #Will return the default value if timing point were not found
        for t in types.keys():
            r = self.get_timing_point(time, t)
            if r != None:
                types[t] = r
            #else:
                #print("{} were not found for timestamp {}, using {} instead.".format(t, time, types[t]))

        return types

    def get_timing_point(self, time, timing_type):
        """
        Returns latest timing point by timestamp (Current)

        time -- timestamp
        timing_type -- mpb, bmp or spm
        return -- self.timing_points object
        """
        r = None
        try:
            for key in sorted(self.timing_points[timing_type].keys(), key=lambda k: k):
                if key <= time:
                    r = self.timing_points[timing_type][key]
                else:
                    break
        except Exception as e:
            print(e)
        return r

    def get_object_count(self):
        """
        Get the total hitobject count for the parsed beatmap (Normal hitobjects, sliders & sliderticks)

        return -- total hitobjects for parsed beatmap
        """
        count = 0
        for hitobject in self.hitobjects:
            count += hitobject.get_points()
        return count
