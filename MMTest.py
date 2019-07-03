import glob;
import os;
import json;
import struct;
import lz4.block;

def ComponentsDict():
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
    };
    return Components;


def QualitiesDict():
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
    };
    return Qualities;
    

def nearest_multiple(number, multiple):
    mult = (1/multiple);
    return round(number * mult) / mult;
    
    
def frange(start, stop, step):
    x = start;
    while x <= stop:
        yield x;
        x = round(x + step, 5);

        
def Iterate_Scan (Downforce,Handling,Speed,Rec_Best,ScanDepth,MaxDepth):
    print("Scan Depth: %d" % (ScanDepth));
    Components = ComponentsDict();
    Qualities = QualitiesDict();
    
    ScanDiv = 2 ** ScanDepth;
    ComponentValues = {};
    ComponentIndex = 0;
    BaselineList = [0,0,0,0,0,0];
    
    for ComponentName, ComponentDetails in Components.items():
        ComponentValues[ComponentName] = {};
        CompV = ComponentValues[ComponentName];
        
        # fetch the normal values
        Midp = ComponentDetails['Midpoint'];
        Rng = ComponentDetails['Range'];
        Grad = ComponentDetails['Gradations'];
        
        Cardinality = Rng / Grad;
        Start = Midp - Rng;
        End = Midp + Rng;
        
        # modify for the current function inputs
        Midp = Rec_Best[ComponentIndex];
        Grad_Try = round(Rng / ScanDepth,5);
        #Grad = Grad_Try + round(Grad_Try % Grad,5);
        #Grad = Grad_Try + round(5.0 % 0.1,5);
        if Grad_Try == Grad:
            BaselineList[ComponentIndex] = 1;
        Grad = nearest_multiple(Grad_Try,Grad);
        """
        if (Midp + Grad) >= End:
            Midp = End - Grad;
        if (Midp - Grad) <= Start:
            Midp = Start + Grad;
        Start = Midp - Grad;
        End = Midp + Grad;
        
        #Start = max(Start,Midp - Grad);
        #End = min(End,Midp + Grad);
        """
        
        for i in frange(Start,End,Grad):
            CompV[i] = {};
            CompV_Qualities = CompV[i];
            
            for QualityName, QualityComponent in Qualities.items():
                CompV_Qualities[QualityName] = (i-ComponentDetails['Midpoint']) * QualityComponent[ComponentName];
        
        ComponentIndex += 1;

    #print (json.dumps(ComponentValues, indent=4));
    
    for FW, List_FW in ComponentValues['Front Wing'].items():
        for RW, List_RW in ComponentValues['Rear Wing'].items():
            for P, List_P in ComponentValues['Pressure'].items():
                for C, List_C in ComponentValues['Camber'].items():
                    for G, List_G in ComponentValues['Gears'].items():
                        for S, List_S in ComponentValues['Suspension'].items():
                            #Elapsed += 1;
                            Rec = [FW,RW,P,C,G,S];
                            for Q in Qualities:
                                Rec.append(sum([
                                    #0.5,
                                    List_FW[Q],
                                    List_RW[Q],
                                    List_P[Q],
                                    List_C[Q],
                                    List_G[Q],
                                    List_S[Q]                                    
                                ]));
                            
                            Rec.append(sum([abs(Rec[6]-Downforce),abs(Rec[7]-Handling),abs(Rec[8]-Speed)]));

                            if Rec[9] < Rec_Best[9]:
                                Rec_Best = Rec;
    
    
    print(Rec_Best);
    #if sum(BaselineList) == 6 or Rec_Best[9] < 0.005 or ScanDepth >= MaxDepth:
    if sum(BaselineList) == 6 or ScanDepth >= MaxDepth:
        print("Done");
    else:
        Iterate_Scan(Downforce,Handling,Speed,Rec_Best,ScanDepth+1,MaxDepth);

        
def Optimum_Setup (MaxDepth):
    FileList = glob.glob(r"/home/ec2-user/python-practice/RaceSetups/*.sav");
    TargetFile = max(FileList, key=os.path.getctime);
    
#with open(r"scripts/CircuitTrackAArbeloa.sav","rb") as f:
    with open(TargetFile,"rb") as f:
        stepforward = struct.unpack("i",f.read(4))[0];
        dataLengthEncoded = struct.unpack("i",f.read(4))[0];
        dataLengthDecoded = struct.unpack("i",f.read(4))[0];

        dataDecompressed = lz4.block.decompress(f.read(),uncompressed_size = dataLengthDecoded);
        dataDecoded = json.loads(dataDecompressed.decode("utf-8","ignore"));
        mSetupStintData = dataDecoded["mSetupStintData"];
        mSetupOutput = mSetupStintData["mSetupOutput"];

        Downforce = mSetupStintData["mDeltaAerodynamics"] - mSetupOutput["aerodynamics"];
        Handling = mSetupStintData["mDeltaHandling"] - mSetupOutput["handling"];
        Speed = mSetupStintData["mDeltaSpeedBalance"] - mSetupOutput["speedBalance"];

        print("TARGET  Downforce: %f, Handling: %f, Speed: %f" % (Downforce,Handling,Speed));

        Components = ComponentsDict();
        Rec_Best = [0,0,0,0,0,0,0,0,0,3];
        ComponentIndex = 0;

        # populate Rec_Best with component midpoints
        for ComponentName, ComponentDetails in Components.items():
            Rec_Best[ComponentIndex] = ComponentDetails['Midpoint'];
            ComponentIndex += 1;

        Iterate_Scan(Downforce,Handling,Speed,Rec_Best,1,MaxDepth);
    
    #print (json.dumps(Results, indent=4));
                
    
                                
    """
    if Elapsed % 1000000 == 0:
    print(Rec_Best);

    print(Rec);
    print('%f, %f, %f' % (Rec[6], Rec[7], Rec[8]));
    print('%f, %f, %f' % (Rec[6]-D, Rec[7]-H, Rec[8]-S));
    print('%f, %f, %f' % (abs(Rec[6]-D), abs(Rec[7]-H), abs(Rec[8]-S)));
    print('');
    """
                                
        
        
        
    #print (json.dumps(Results, indent=4));
"""        
Downforce = round(random.random(),2);
Handling = round(random.random(),2);
Speed = round(random.random(),2);
print('Downforce: %f, Handling: %f, Speed: %f' % (Downforce,Handling,Speed));
"""
Optimum_Setup(10); 
#Optimum_Setup(0.5,0.5,0.5); 