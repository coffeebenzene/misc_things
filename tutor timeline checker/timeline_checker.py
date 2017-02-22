# Tutor time line checking helper.
# Should be compatiable with both python 2 and 3 at the same time.

import re
import datetime

try:
   input = raw_input # rebind raw_input. python2 input is evil.
except NameError:
   pass

class file_reader:
    def __init__(self, filename):
        self.filename = filename
    
    def __iter__(self):
        self._iterable = iter(self._f)
        return self
    
    def __next__(self):
        nextline = next(self._iterable).strip()
        while not nextline:
            nextline = next(self._iterable).strip()
        return nextline
    
    def next(self):
        return self.__next__()
    
    def __enter__(self):
        self._f = open(self.filename)
        return self
    
    def __exit__(self, type, value, traceback):
        self._f.close()



valid_params = ("timeline_filename", "timetable_filename",
                "problem_num", "duration",
                "lesson", "start",
                "monday_date", "association",
               )
one_min = datetime.timedelta(minutes=1) # for convenience.

def get_params(param_filename):
    params = {}
    
    with file_reader(param_filename) as f:
        for line in f:
            if line.startswith("#"):
                continue
            k, v = [x.strip() for x in line.split(":",1)]
            if k not in valid_params:
                raise Exception("ERROR: Invalid Parameter: {}".format(k))
            params[k] = v
    
    if params["start"] not in ("s","e"):
        raise Exception("ERROR: invalid value for parameter start: {}".format(params["start"]))
    
    params["duration"] = datetime.timedelta(minutes=int(params["duration"]))
    params["monday_date"] = datetime.datetime.strptime(params["monday_date"], "%Y-%m-%d")
    params["monday_date"] -= datetime.timedelta(days=params["monday_date"].weekday())
    assoc = {} # format {problem_index: cohorts} where problem_index="X", cohorts={1,2,..}
    for elem in params["association"].split(","):
        problem_index, cohort_num = elem.strip().split(":",1)
        assoc[problem_index] = {i.strip() for i in cohort_num.split("&")}
    params["association"] = assoc
    return params

def add_id_cohort_mapping(map, problem_id, cohort, data):
    if problem_id not in map:
        map[problem_id] = {}
    map[problem_id][cohort] = data

try:
    params = get_params("params.txt")
    
    # Timetable format: X is cohort number, Y is lesson number/name as string.
    # { "Cohort X": {Y: [day, starttime, endtime],
    #                ...}
    #  ...}
    timetable = {}
    with file_reader(params["timetable_filename"]) as f:
        cohort = None
        for line in f:
            if line.startswith("#"):
                continue
            header = re.match("^(?!\s)(.+):$", line)
            if header:
                cohort = header.group(1)
                timetable[cohort] = {}
                continue
            lesson, data = line.split(":",1)
            lesson = lesson.strip()
            data = [x.strip() for x in data.split(",")]
            data[0] = int(data[0])
            for i in (1,2):
                data[i] = datetime.datetime.strptime(data[i], "%H:%M").time()
            timetable[cohort][lesson] = data
    
    # Start processing time lines.
    with file_reader(params["timeline_filename"]) as f:
        timelines = list(f)
    
    # warning format: each element is (wrong, correction/explanation)
    warnings = []
    # id_cohort_map format:
    # { problem_id: {"Cohort X": (startdate, enddate)
    #               ...}
    # ...}
    id_cohort_all = {}
    id_cohort_proper = {}
    for i, line in enumerate(timelines):
        match = re.match(r"Wk\.(\d\.\d\.\d)"
                         r" Rel (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),"
                         r" Due (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
                         r" for \[(.*)\]",
                         line) # remember spaces are important in regex.
        if not match:
            raise Exception("Invalid time line found on line {}:{}".format(i, repr(line)))
        
        problem_id, startdate, enddate, cohort = match.groups()
        if problem_id.rsplit(".",1)[0] != params["problem_num"]:
            continue
        if cohort in id_cohort_all.get(problem_id,()): # id and cohort pair seen before.
            warnings.append((line, "Problem id and cohort repeated. Ignore."))
            continue
        
        startdate = datetime.datetime.strptime(startdate, "%Y-%m-%d %H:%M:%S")
        enddate = datetime.datetime.strptime(enddate, "%Y-%m-%d %H:%M:%S")
        
        # Add to mappings
        currentyear = params["monday_date"].year
        data = (startdate, enddate)
        add_id_cohort_mapping(id_cohort_all, problem_id, cohort, data)
        
        if currentyear != startdate.year: # Skip futher checks if not a proper timeline
            continue
        
        add_id_cohort_mapping(id_cohort_proper, problem_id, cohort, data)
        
        # Check that timing fits class timing.
        day, class_start, class_end = timetable[cohort][params["lesson"]]
        day = params["monday_date"] + datetime.timedelta(days=day-1)
        
        if params["start"] == "s":
            class_start = datetime.datetime.combine(day, class_start)
            expected_start = class_start - one_min
            expected_end = class_start + params["duration"] + one_min
        else:
            class_end = datetime.datetime.combine(day, class_end)
            expected_start = class_end -  params["duration"] - one_min
            expected_end = class_end + one_min
        
        if ( currentyear == startdate.year and
             (startdate != expected_start or enddate != expected_end) ):
            correct = "Wk.{} Rel {}, Due {} for [{}]".format(
                    problem_id,
                    expected_start.strftime("%Y-%m-%d %H:%M:%S"),
                    expected_end.strftime("%Y-%m-%d %H:%M:%S"),
                    cohort
            )
            warnings.append((line, correct))
    
    # Check that all problem ids are seen. (timeline list is complete)
    checked_index = {pid.rsplit(".",1)[1] for pid in id_cohort_all}
    expected_index = set(params["association"].keys())
    if checked_index != expected_index:
        checked_index = sorted(checked_index)
        expected_index = sorted(expected_index)
        warnings.append(("TIMELINE LIST INCOMPLETE: indexes incomplete",
                         "{} vs {}".format(checked_index, expected_index)
                        ))
    # Check each problem id has all the cohorts. (timeline list is complete)
    for problem_id, cohorts in id_cohort_all.items():
        if set(cohorts.keys()) != set(timetable.keys()):
            cohorts = sorted(set(cohorts.keys()))
            expected = sorted(set(timetable.keys()))
            warnings.append(("TIMELINE LIST INCOMPLETE: Problem id: {}".format(problem_id),
                             "calculated:{}\n  vs given:{}".format(cohorts, expected)
                            ))
    # Check each cohort appears in each problem id once.
    seen_cohorts = {}
    for problem_id, cohorts in id_cohort_proper.items():
        for cohort in cohorts.keys():
            seen_cohorts.setdefault(cohort,[]).append(problem_id)
    for cohort, problem_ids in seen_cohorts.items():
        if len(problem_ids) != 1:
            warnings.append(("{} not associated with only 1 problem id".format(cohort),
                             "problem ids: {}".format(problem_ids)
                            ))
    # Check each problem id opens at only 1 timing.
    for problem_id, cohorts in id_cohort_proper.items():
        if len(set(cohorts.values())) != 1:
            timings = []
            for time_range in set(cohorts.values()):
                timings.append(time_range[0].strftime("%H:%M %y-%m-%d %a"))
                timings.append(" to ")
                timings.append(time_range[1].strftime("%H:%M %y-%m-%d %a"))
                timings.append("\n")
            timings = "".join(timings)
            warnings.append(("{} has more than 1 release timing.".format(problem_id),
                             "timings:\n{}".format(timings)
                            ))
    # Check if associations match given associations
    for problem_id, cohorts in id_cohort_proper.items():
        problem_index = problem_id.rsplit(".",1)[1]
        cohorts = {c.rsplit(" ",1)[1] for c in cohorts}
        if cohorts != params["association"][problem_index]:
            cohorts = sorted(cohorts)
            expected = sorted(params["association"][problem_index])
            warnings.append(("{} cohorts to not match given association".format(problem_id),
                             "calculated:{}\n  vs given:{}".format(cohorts, expected)
                            ))
    
    if warnings:
        print("{} errors detected.".format(len(warnings)))
        for i, w in enumerate(warnings,1):
            print("Error {}:".format(i))
            print("{}\n{}\n".format(w[0], w[1]))
        with open("warnings.txt","w") as f:
            lines = []
            for i, w in enumerate(warnings,1):
                lines.append("Error {}:".format(i))
                lines.append(w[0])
                lines.append("Description/correction:")
                lines.append(w[1])
                lines.append("")
            f.write("\n".join(lines))
        print("Errors written into warnings.txt")
    else:
        print("No errors detected.")
    
    print("\nDetected timings:")
    lines = []
    for problem_id, cohorts in id_cohort_proper.items():
        lines.append("Wk{}".format(problem_id))
        for c, times in cohorts.items():
            starttime = times[0].strftime("%H:%M %y-%m-%d %a")
            endtime = times[1].strftime("%H:%M %y-%m-%d %a")
            lines.append("    {}: {} to {}".format(c, starttime, endtime))
        lines.append("")
    print("\n".join(lines))
    
    input("\nPress enter to exit.")
    
except Exception as e:
    import traceback
    traceback.print_exc()
    input()