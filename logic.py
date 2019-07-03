import glob
import json
import os
import struct

from lz4 import block

Components = {
        'Front Wing': {
             'Midpoint': 15,
             'Range': 5,
             'Gradations': 0.1
        },
        'Rear Wing': {
             'Midpoint': 25,
             'Range': 5,
             'Gradations': 0.1
        },
        'Pressure': {
             'Midpoint': 21,
             'Range': 3,
             'Gradations': 0.6
        },
        'Camber': {
             'Midpoint': -2,
             'Range': 2,
             'Gradations': 0.4
        },
        'Suspension': {
             'Midpoint': 50,
             'Range': 50,
             'Gradations': 6.25
        },
        'Gears': {
             'Midpoint': 50,
             'Range': 50,
             'Gradations': 6.25
        }
    }

Qualities = {
        'Downforce': {
                'Front Wing': round(-6 / 50, 5),
                'Rear Wing': round(-4 / 50, 5),
                'Pressure': round(0 / 50, 5),
                'Camber': round(0 / 50, 5),
                'Gears': round(0 / 50, 5),
                'Suspension': round(0 / 50, 5)
        },
        'Handling': {
                'Front Wing': round(1 / 50, 5),
                'Rear Wing': round(1 / 50, 5),
                'Pressure': round((2.5 / 3) / 50, 5),
                'Camber': round(-3.75 / 50, 5),
                'Gears': round(-0.05 / 50, 5),
                'Suspension': round(-0.6 / 50, 5)
        },
        'Speed': {
                'Front Wing': round(-1.5 / 50, 5),
                'Rear Wing': round(-2.5 / 50, 5),
                'Pressure': round((-2.5 / 3) / 50, 5),
                'Camber': round(3.75 / 50, 5),
                'Gears': round(0.6 / 50, 5),
                'Suspension': round(0.1 / 50, 5)
        }
    }


def nearest_multiple(number, multiple):
    multiple = (1/multiple)
    return round(number * multiple) / multiple
    
    
def rounded_range(start, stop, step):
    x = start
    while x <= stop:
        yield x
        x = round(x + step, 5)

        
def iterate_scan(
        downforce,
        handling,
        speed,
        recorded_best,
        scan_depth,
        max_depth
):
    print("Scan Depth: %d" % scan_depth)
    # Components = ComponentsDict();
    # Qualities = QualitiesDict();
    
    # ScanDiv = 2 ** scan_depth
    component_values = {}
    component_index = 0
    baseline_list = [0, 0, 0, 0, 0, 0]
    
    for component_name, component_details in Components.items():
        component_values[component_name] = {}
        component_dict = component_values[component_name]
        
        # fetch the normal values
        midpoint = component_details['Midpoint']
        value_range = component_details['Range']
        gradations = component_details['Gradations']
        
        # Cardinality = value_range / gradations
        value_start = midpoint - value_range
        value_end = midpoint + value_range
        
        # modify for the current function inputs
        # midpoint = recorded_best[component_index]
        gradation_try = round(value_range / scan_depth, 5)
        # gradations = gradation_try + round(gradation_try % gradations,5);
        # gradations = gradation_try + round(5.0 % 0.1,5);
        if gradation_try == gradations:
            baseline_list[component_index] = 1
        gradations = nearest_multiple(gradation_try, gradations)

        # if (midpoint + gradations) >= value_end:
        #     midpoint = value_end - gradations
        # if (midpoint - gradations) <= value_start:
        #     midpoint = value_start + gradations
        # value_start = midpoint - gradations
        # value_end = midpoint + gradations
        #
        # # value_start = max(value_start,midpoint - gradations)
        # # value_end = min(value_end,midpoint + gradations)

        for i in rounded_range(value_start, value_end, gradations):
            component_dict[i] = {}
            qualities_dict = component_dict[i]
            
            for quality_name, quality_component in Qualities.items():
                qualities_dict[quality_name] =\
                    (i - component_details['Midpoint']) *\
                    quality_component[component_name]
        
        component_index += 1

    # print (json.dumps(component_values, indent=4));
    
    for FW, List_FW in component_values['Front Wing'].items():
        for RW, List_RW in component_values['Rear Wing'].items():
            for P, List_P in component_values['Pressure'].items():
                for C, List_C in component_values['Camber'].items():
                    for G, List_G in component_values['Gears'].items():
                        for S, List_S in\
                                component_values['Suspension'].items():
                            # Elapsed += 1;
                            setup_list = [FW, RW, P, C, G, S]
                            for Q in Qualities:
                                setup_list.append(sum([
                                    # 0.5,
                                    List_FW[Q],
                                    List_RW[Q],
                                    List_P[Q],
                                    List_C[Q],
                                    List_G[Q],
                                    List_S[Q]                                    
                                ]))
                            
                            setup_list.append(sum(
                                [abs(setup_list[6] - downforce),
                                 abs(setup_list[7] - handling),
                                 abs(setup_list[8] - speed)]
                            ))

                            if setup_list[9] < recorded_best[9]:
                                recorded_best = setup_list
    
    print(recorded_best)
    # if sum(baseline_list) == 6 or Rec_Best[9] < 0.005 or ScanDepth >=
    # MaxDepth:
    if sum(baseline_list) == 6 or scan_depth >= max_depth:
        print("Done")
    else:
        iterate_scan(
            downforce,
            handling,
            speed,
            recorded_best,
            scan_depth + 1,
            max_depth
        )

        
def optimum_setup(max_depth):
    file_list = glob.glob(r"/home/ec2-user/python-practice/RaceSetups/*.sav")
    target_file = max(file_list, key=os.path.getctime)
    
    # with open(r"scripts/CircuitTrackAArbeloa.sav","rb") as f:
    with open(target_file, "rb") as f:
        # stepforward = struct.unpack("i",f.read(4))[0];
        # dataLengthEncoded = struct.unpack("i",f.read(4))[0];
        data_length_decoded = struct.unpack("i", f.read(4))[0]

        data_decompressed = block.decompress(
            f.read(),
            uncompressed_size=data_length_decoded
        )
        data_decoded = json.loads(data_decompressed.decode("utf-8", "ignore"))
        setup_stint_data = data_decoded["mSetupStintData"]
        setup_output = setup_stint_data["mSetupOutput"]

        downforce = setup_stint_data["mDeltaAerodynamics"] -\
            setup_output["aerodynamics"]
        handling = setup_stint_data["mDeltaHandling"] -\
            setup_output["handling"]
        speed = setup_stint_data["mDeltaSpeedBalance"] -\
            setup_output["speedBalance"]

        print("TARGET  Downforce: %f, Handling: %f, Speed: %f" %
              (downforce, handling, speed))

        # Components = ComponentsDict();
        recorded_best = [0, 0, 0, 0, 0, 0, 0, 0, 0, 3]
        component_index = 0

        # populate Rec_Best with component midpoints
        for component_name, component_details in Components.items():
            recorded_best[component_index] = component_details['Midpoint']
            component_index += 1

        iterate_scan(downforce, handling, speed, recorded_best, 1, max_depth)
    
    # print (json.dumps(Results, indent=4));

    # if Elapsed % 1000000 == 0:
    # print(Rec_Best);
    #
    # print(Rec);
    # print('%f, %f, %f' % (Rec[6], Rec[7], Rec[8]));
    # print('%f, %f, %f' % (Rec[6]-D, Rec[7]-H, Rec[8]-S));
    # print('%f, %f, %f' % (abs(Rec[6]-D), abs(Rec[7]-H), abs(Rec[8]-S)));
    # print('');

    # print (json.dumps(Results, indent=4));

# Downforce = round(random.random(),2);
# Handling = round(random.random(),2);
# Speed = round(random.random(),2);
# print('Downforce: %f, Handling: %f, Speed: %f' % (Downforce,Handling,Speed));


optimum_setup(10)
# optimum_setup(0.5,0.5,0.5);
